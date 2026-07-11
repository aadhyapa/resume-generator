from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import copy
import os

from agents.validator import validate_resume
from agents.job_description_chunker import job_description_chunker
from agents.embedder import embed
from agents.editor import editor

from algorithms.matchmaker import matchmaker
from algorithms.selector import selector
from algorithms.formatter import formater

app = FastAPI()

# This makes sure that the cors won't cause issues with the extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/generate_resume")
async def generate_resume(job_description: str = Body(..., embed=True)):
    try:
        job_description.strip()
        if not job_description:
            raise HTTPException(status_code=400, detail="Job description cannot be empty")

        # Processing Job Description
        sectioned_chunks = job_description_chunker(job_description)
        
        requirement_embeddings = embed(sectioned_chunks['requirement'])
        responsibility_embeddings = embed(sectioned_chunks['responsibility'])
        bonus_embeddings = embed(sectioned_chunks['bonus'])
        soft_skills_embedding = embed(sectioned_chunks['soft-skills'])

        # Load resume bullets from the generated test data resume JSON
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(current_dir)
        resume_path = os.path.join(backend_dir, "agents", "test_data", "resume.json")

        if os.path.exists(resume_path):
            try:
                with open(resume_path, "r", encoding="utf-8") as f:
                    # Use a deep copy to avoid modifying the original database reference in-place across request
                    resume = copy.deepcopy(json.load(f))
                    resume_bullets = resume["bullets"]

            except Exception as e:
                print(f"Error loading test resume: {e}")
                resume_bullets = []
        else:
            resume_bullets = []

        # Finding best bullet matches
        scored_resume_bullets = matchmaker(requirement_embeddings, responsibility_embeddings, bonus_embeddings, soft_skills_embedding, resume_bullets)
        selected_bullets = selector(scored_resume_bullets, 20, 4)

        # Keep a clean deep copy of original bullets for comparison and fallback
        original_bullets = copy.deepcopy(selected_bullets)


        edited_resume = selected_bullets
        max_attempts = 2
        failed_ids = set()

        for attempt in range(1, max_attempts + 1):
            if attempt == 1:
                # 1st Attempt: Run editor on the entire set
                edited_resume = editor(selected_bullets, sectioned_chunks)
            else:
                # 2nd Attempt: Only re-edit bullets that failed validation
                orig_map = {b["bullet_id"]: b for b in original_bullets if "bullet_id" in b}
                
                # Construct subset of only failed bullets, reset to original text
                failed_subset = []
                for b in edited_resume:
                    b_id = b.get("bullet_id")
                    if b_id in failed_ids and b_id in orig_map:
                        reset_bullet = copy.deepcopy(orig_map[b_id])
                        reset_bullet.pop("bold_words", None)
                        failed_subset.append(reset_bullet)

                # Run editor on the subset and capture the returned edited list
                edited_subset = editor(failed_subset, sectioned_chunks)
                edited_subset_map = {b["bullet_id"]: b for b in edited_subset if "bullet_id" in b}

                # Construct new list with edited subset merged back in
                new_edited_resume = []
                for b in edited_resume:
                    b_id = b.get("bullet_id")
                    if b_id in edited_subset_map:
                        new_edited_resume.append(edited_subset_map[b_id])
                    else:
                        new_edited_resume.append(b)
                edited_resume = new_edited_resume

            # Validate current state
            validation_report = validate_resume(original_bullets, edited_resume)

            if validation_report["is_valid"]:
                break
            else:
                # Gather IDs of failed bullets
                failed_ids = set()
                for failure in validation_report["character_limit_failures"]:
                    failed_ids.add(failure["bullet_id"])
                for failure in validation_report["fabrication_failures"]:
                    failed_ids.add(failure["id"])

                # If this was the final attempt, restore original bullets for all failures
                if attempt == max_attempts:
                    orig_map = {b["bullet_id"]: b for b in original_bullets if "bullet_id" in b}
                    new_edited_resume = []
                    for b in edited_resume:
                        b_id = b.get("bullet_id")
                        if b_id in failed_ids and b_id in orig_map:
                            restored_bullet = copy.deepcopy(orig_map[b_id])
                            restored_bullet["edited"] = False
                            new_edited_resume.append(restored_bullet)
                        else:
                            new_edited_resume.append(b)
                    edited_resume = new_edited_resume

                assembled_resume = formater(edited_resume)
        
        return {"message": "Resume generated successfully", "resume": assembled_resume}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/store-resume")
def store_resume(resume):
    # In the future, create a db entry
    resume['bullets' ] = embed(resume['bullets'])

    with open("test_data/resume1.json", "w") as file:
        file.write(json.dumps(resume))

    




if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
