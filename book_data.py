import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")

def fetch_book_details_from_api(query):
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&key={API_KEY}"
    response = requests.get(url)
    data = response.json()
    if "items" in data:
        book = data["items"][0]["volumeInfo"]
        return {
            "title": book.get("title", "Unknown Title"),
            "authors": book.get("authors", ["Unknown"]),
            "description": book.get("description", "No description available."),
            "info_link": book.get("infoLink", "#")
        }
    return {
        "title": "Unknown Title",
        "authors": ["Unknown"],
        "description": "No description available.",
        "info_link": "#"
    }
