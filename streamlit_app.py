import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.title("Book Recommendation Chatbot")

st.write("Ask for a book recommendation based on your current mood or situation.")

user_input = st.text_input("Enter your query here:")
if st.button("Get Recommendation"):
    if user_input:
        response = requests.post(f"{API_URL}/recommend", json={"user_input": user_input})
        if response.status_code == 200:
            result = response.json()
            st.write(f"**Detected Emotion:** {result['emotion']} with confidence {result['confidence']:.2f}")
            st.write(f"**Recommended Book:** {result['recommended_book']['title']}")
            st.write(f"**Book Details:** {result['recommended_book']['title']} by {', '.join(result['recommended_book']['authors'])}")
            st.write(f"**Description:** {result['recommended_book']['description']}")
            st.write(f"[More Info]({result['recommended_book']['info_link']})")
            st.write(f"**Chatbot:** {result['response']}")

            st.session_state['last_recommendation'] = result['recommended_book']['title']
            st.session_state['user_input'] = user_input
            st.session_state['recommendation_history'] = st.session_state.get('recommendation_history', []) + [result['recommended_book']['title']]
        else:
            st.error("Sorry, something went wrong. Please try again.")
    else:
        st.warning("Please enter a query to get a recommendation.")

# Feedback section
if 'last_recommendation' in st.session_state:
    st.write("### Feedback")
    st.write("If you're not satisfied with the recommendation, you can ask for an alternative.")

    feedback_option = st.selectbox("What would you like to do?", [
        "",
        "I don't like this book, suggest an alternative",
        "I already read this book, suggest an alternative",
        "This book is not relevant to my query",
        "I want a more specific recommendation"
    ])

    if feedback_option:
        feedback_input = {
            "user_input": st.session_state['user_input'],
            "feedback": feedback_option,
            "last_recommended_book": st.session_state['last_recommendation'],
            "recommendation_history": st.session_state['recommendation_history']
        }
        feedback_response = requests.post(f"{API_URL}/feedback", json=feedback_input)
        if feedback_response.status_code == 200:
            feedback_result = feedback_response.json()
            st.write(f"**Alternative Book:** {feedback_result['recommended_book']['title']}")
            st.write(f"**Book Details:** {feedback_result['recommended_book']['title']} by {', '.join(feedback_result['recommended_book']['authors'])}")
            st.write(f"**Description:** {feedback_result['recommended_book']['description']}")
            st.write(f"[More Info]({feedback_result['recommended_book']['info_link']})")
            st.write(f"**Chatbot:** {feedback_result['response']}")

            # Update recommendation history with the new recommendation
            st.session_state['last_recommendation'] = feedback_result['recommended_book']['title']
            st.session_state['recommendation_history'].append(feedback_result['recommended_book']['title'])
        else:
            st.error("Sorry, something went wrong with your feedback. Please try again.")
