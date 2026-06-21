from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()

def generate_embedding(text: str) -> list:
    """
    Generate embeddings for a given text using the Gemini API.
    :param text: The text to generate embeddings for.
    :return: A list of embeddings.
    """
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )
    return result.embeddings
