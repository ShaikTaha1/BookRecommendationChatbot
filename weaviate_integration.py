import weaviate
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

client = weaviate.Client(
    url=os.getenv("WEAVIATE_URL"),
    auth_client_secret=None,  # Add authentication if required
    timeout_config=(5, 15)
)

def setup_weaviate_schema():
    schema = {
        "classes": [
            {
                "class": "UserInteraction",
                "properties": [
                    {"name": "user_input", "dataType": ["text"]},
                    {"name": "emotion", "dataType": ["text"]},
                    {"name": "book_title", "dataType": ["text"]},
                    {"name": "embedding", "dataType": ["number[]"]}
                ]
            }
        ]
    }
    try:
        client.schema.create(schema)
        logger.info("Weaviate schema created successfully.")
    except weaviate.exceptions.UnexpectedStatusCodeError:
        logger.info("Class UserInteraction already exists. Skipping creation.")

def store_user_interaction(user_input, emotion, book_title, embedding):
    data_object = {
        "user_input": user_input,
        "emotion": emotion,
        "book_title": book_title,
        "embedding": embedding
    }
    try:
        client.data_object.create(data_object, class_name="UserInteraction")
        logger.info(f"Stored interaction: text='{user_input}', emotion='{emotion}', book_title='{book_title}'")
    except Exception as e:
        logger.error(f"Error storing interaction: {str(e)}")

def search_books_based_on_combined_embeddings(combined_embedding, exclude_books=None):
    try:
        response = (
            client.query
            .get("UserInteraction", ["book_title", "book_description"])
            .with_near_vector({"vector": combined_embedding})
            .do()
        )
        data = response['data']['Get']['UserInteraction']

        # Ensure we exclude any books that have already been recommended
        if exclude_books:
            data = [d for d in data if d['book_title'].lower() not in [book.lower() for book in exclude_books]]

        return data
    except Exception as e:
        logger.error(f"Error occurred while searching books: {str(e)}")
        return []

