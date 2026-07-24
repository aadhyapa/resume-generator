
from dotenv import load_dotenv
import voyageai
import os

load_dotenv()
client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))

def generate_embedding(text: str) -> list:
    """
    Generate embeddings for a given text using the Voyage AI API.
    :param text: The text to generate embeddings for.
    :return: A list of floats representing the embedding.
    """
    result = client.embed([text], model="voyage-code-3")
    if result.embeddings:
        return result.embeddings[0]
    return []

def embed(chunks):
    if not chunks:
        return []
    embedded_chunks = []
    for chunk in chunks:
        if isinstance(chunk, str):
            embedded_chunks.append({
                'text': chunk,
                'embedding': generate_embedding(chunk)
            })
        elif isinstance(chunk, dict):
            chunk['embedding'] = generate_embedding(chunk.get('text', ''))
            embedded_chunks.append(chunk)
        else:
            embedded_chunks.append(chunk)
    return embedded_chunks