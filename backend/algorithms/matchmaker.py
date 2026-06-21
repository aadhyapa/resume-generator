import numpy as np

'''
bullet_embedding structure:[
        {
        "bullet_id": "uuid",
        "embedding": [0.123, -0.442, ...]
        }
]

job_desc_embedding structure: [0.123, -0.442, ...]
'''

def calculate_cosine_similarity(job_desc_embedding: list, resume_bullet_embeddings: list) -> float:
    """
    Calculates the cosine similarity between the job description embedding and the resume bullet embeddings.
    
    :param job_desc_embedding: The embedding of the job description.
    :param resume_bullet_embeddings: A dictionary of bullet ids and their embeddings.
    :return: dictionary with the scores and the corresponding bullets.
    """
    job_desc_coords = np.array(job_desc_embedding)
    for bullet_embedding in resume_bullet_embeddings:
        coords = np.array(bullet_embedding['embedding'])
        score = np.dot(job_desc_coords, coords) / (np.linalg.norm(job_desc_coords) * np.linalg.norm(coords))
        bullet_embedding["score"] = score  

    return resume_bullet_embeddings
    