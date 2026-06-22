import os
import json
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
    # Load resume bullets from the generated test data resume JSON
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(current_dir)
    resume_path = os.path.join(backend_dir, "agents", "test_data", "resume.json")

    if os.path.exists(resume_path):
        try:
            with open(resume_path, "r", encoding="utf-8") as f:
                # Use a deep copy to avoid modifying the original database reference in-place across requests
                import copy
                resume_bullets = copy.deepcopy(json.load(f))
        except Exception as e:
            print(f"Error loading test resume: {e}")
            resume_bullets = []
    else:
        resume_bullets = []

    scorer(requirement_embeddings, resume_bullets, 'requirement')
    scorer(responsibility_embeddings, resume_bullets, 'responsibility')
    scorer(bonus_embeddings, resume_bullets, 'bonus')
    scorer(soft_skills_embedding, resume_bullets, 'soft-skills')

    resume_bullets.sort(key=lambda bullet: bullet.get('score', 0), reverse=True)
    
    return resume_bullets
