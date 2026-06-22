from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()

def generate_embedding(text: str) -> list:
    """
    Generate embeddings for a given text using the Gemini API.
    :param text: The text to generate embeddings for.
    :return: A list of floats representing the embedding.
    """
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )
    if result.embeddings:
        return result.embeddings[0].values
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

