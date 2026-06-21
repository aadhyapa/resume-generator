from IPython.core import latex_symbols
import numpy as np

# Weight by category
CATEGORY_WEIGHTS = {
    "requirement": 1,
    "responsibility": 0.8,
    "bonus": 0.6,
    "soft-skills": 0.3,
}


def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return np.dot(a, b) / denom


def scorer(job_desc_chunks, resume_bullet_embeddings, chunk_type):
    """
    Ranks resume bullets by their best-matching alignment to job description
    chunks, rather than a single whole-JD embedding. Each bullet's score is
    the weighted average of its top-k most similar JD chunks.

    :param job_desc_chunks: list of dicts with 'text', 'category', 'embedding'
    :param resume_bullet_embeddings: list of dicts with 'bullet_id', 'embedding'
    :param chunk_type: name of the job description chunk
    :return: resume_bullet_embeddings with the chunk score added
    """
    for bullet in resume_bullet_embeddings:
        bullet_vec = bullet["embedding"]
        if 'score' not in bullet:
            bullet['score'] = 0

        for chunk in job_desc_chunks: 
            chunk_vec = chunk['embedding']
            bullet['score'] += cosine_similarity(chunk_vec, bullet_vec) * CATEGORY_WEIGHTS[chunk_type]


def matchmaker(requirement_embeddings, responsibility_embeddings, bonus_embeddings, soft_skills_embedding):
    # TEMP
    resume_bullets = []

    scorer(requirement_embeddings, resume_bullets, 'requirement')
    scorer(requirement_embeddings, resume_bullets, 'requirement')
    scorer(requirement_embeddings, resume_bullets, 'requirement')
    scorer(requirement_embeddings, resume_bullets, 'requirement')

    resume_bullets.sort(key=lambda bullet: bullet.get('score', 0), reverse=True)
    
    return resume_bullets
