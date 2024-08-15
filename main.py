from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from weaviate_integration import store_user_interaction, search_books_based_on_combined_embeddings, setup_weaviate_schema
from transformers import GPT2LMHeadModel, GPT2Tokenizer, pipeline
from book_data import fetch_book_details_from_api
import os
from dotenv import load_dotenv
import numpy as np

load_dotenv()

app = FastAPI()

# Load models and tokenizer
model_name = os.getenv("MODEL_NAME", "distilbert-base-nli-stsb-mean-tokens")
model = SentenceTransformer(model_name)

emotion_classifier = pipeline('text-classification', model='j-hartmann/emotion-english-distilroberta-base', top_k=None)
tokenizer = GPT2Tokenizer.from_pretrained("./fine_tuned_model")
fine_tuned_model = GPT2LMHeadModel.from_pretrained("./fine_tuned_model")
text_generator = pipeline('text-generation', model=fine_tuned_model, tokenizer=tokenizer, max_length=150)

# Setup Weaviate schema
setup_weaviate_schema()

class UserInput(BaseModel):
    user_input: str

class FeedbackInput(BaseModel):
    user_input: str
    feedback: str
    last_recommended_book: str
    recommendation_history: list

def detect_emotion(text):
    emotion_result = emotion_classifier(text)
    emotion = max(emotion_result[0], key=lambda x: x['score'])['label']
    confidence = max(emotion_result[0], key=lambda x: x['score'])['score']
    return emotion, confidence

def generate_personalized_response(emotion, title, description):
    prompt = f"Based on the emotion {emotion}, explain why the book '{title}' would be a good recommendation. The book description is: {description}."
    response = text_generator(prompt, max_new_tokens=50)[0]['generated_text']
    return response

def generate_combined_embedding(emotion_embedding, context_embedding):
    combined_embedding = np.average([emotion_embedding, context_embedding], axis=0, weights=[0.3, 0.7])
    return combined_embedding

@app.post("/recommend")
def recommend_book(input_data: UserInput):
    try:
        user_input = input_data.user_input
        emotion, confidence = detect_emotion(user_input)

        # Generate embeddings
        emotion_embedding = model.encode(emotion).tolist()
        context_embedding = model.encode(user_input).tolist()

        # Combine embeddings
        combined_embedding = generate_combined_embedding(emotion_embedding, context_embedding)

        # Search Weaviate
        similar_books = search_books_based_on_combined_embeddings(combined_embedding)

        book_details = None
        if similar_books:
            recommended_book = similar_books[0]['book_title']
            book_details = fetch_book_details_from_api(recommended_book)

        if not book_details:
            book_details = fetch_book_details_from_api(user_input)

        personalized_response = generate_personalized_response(emotion, book_details['title'], book_details['description'])

        embedding = model.encode(user_input).tolist()
        store_user_interaction(user_input, emotion, book_details['title'], embedding)

        return {
            "emotion": emotion,
            "confidence": confidence,
            "recommended_book": {
                "title": book_details['title'],
                "authors": book_details.get('authors', ['Unknown']),
                "description": book_details.get('description', 'No description available.'),
                "info_link": book_details.get('info_link', '#')
            },
            "response": personalized_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
def handle_feedback(feedback_input: FeedbackInput):
    try:
        user_input = feedback_input.user_input
        feedback = feedback_input.feedback
        recommendation_history = feedback_input.recommendation_history

        emotion, confidence = detect_emotion(user_input)

        # Generate embeddings
        emotion_embedding = model.encode(emotion).tolist()
        context_embedding = model.encode(user_input).tolist()

        # Combine embeddings
        combined_embedding = generate_combined_embedding(emotion_embedding, context_embedding)

        # Search Weaviate, excluding books already recommended
        similar_books = search_books_based_on_combined_embeddings(combined_embedding, exclude_books=recommendation_history)

        # Ensure we do not recommend a book that has already been suggested
        if similar_books:
            alternative_book = similar_books[0]['book_title']
            book_details = fetch_book_details_from_api(alternative_book)
        else:
            # Fallback: If no new books are found in Weaviate, generate from LLM
            book_details = fetch_book_details_from_api(user_input)

        personalized_response = generate_personalized_response(emotion, book_details['title'], book_details['description'])

        # Store the new interaction in Weaviate
        embedding = model.encode(user_input).tolist()
        store_user_interaction(user_input, emotion, book_details['title'], embedding)

        # Update the recommendation history
        recommendation_history.append(book_details['title'])

        return {
            "recommended_book": {
                "title": book_details['title'],
                "authors": book_details.get('authors', ['Unknown']),
                "description": book_details.get('description', 'No description available.'),
                "info_link": book_details.get('info_link', '#')
            },
            "response": personalized_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
