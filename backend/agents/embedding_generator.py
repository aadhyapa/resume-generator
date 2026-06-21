from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()

def generate_embedding(text: str, task_type: str) -> list:
    """
    Generate embeddings for a given text using the Gemini API.
    :param text: The text to generate embeddings for.
    :param task_type: The type of task, which determines the embedding model to use.
    :return: A list of embeddings.
    """
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )
    return result.embeddings
