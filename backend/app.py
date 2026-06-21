from fastapi import FastAPI, HTTPException
from agents.validator import validate_resume
from agents.job_description_chunker import job_description_chunker
from agents.embedder import generate_embedding
from algorithms.matchmaker import matchmaker

app = FastAPI()

@app.post("/generate_resume")
async def generate_resume(job_description: str):
    try:
        job_description.strip()
        if not job_description:
            raise HTTPException(status_code=400, detail="Job description cannot be empty")

        sectioned_chunks = job_description_chunker(job_description)
    
        requirement_embeddings = generate_embedding(sectioned_chunks['requirement'])
        responsibility_embeddings = generate_embedding(sectioned_chunks['responsibility'])
        bonus_embeddings = generate_embedding(sectioned_chunks['bonus'])
        soft_skills_embedding = generate_embedding(job_description['soft-skills'])
        
        return {"message": "Resume generated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
