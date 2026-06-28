from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from agents.validator import validate_resume
from agents.job_description_chunker import job_description_chunker
from agents.embedder import embed
from agents.editor import editor

from algorithms.matchmaker import matchmaker
from algorithms.selector import selector

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

        sectioned_chunks = job_description_chunker(job_description)
    
        requirement_embeddings = embed(sectioned_chunks['requirement'])
        responsibility_embeddings = embed(sectioned_chunks['responsibility'])
        bonus_embeddings = embed(sectioned_chunks['bonus'])
        soft_skills_embedding = embed(sectioned_chunks['soft-skills'])

        resume_bullets = matchmaker(requirement_embeddings, responsibility_embeddings, bonus_embeddings, soft_skills_embedding)

        selected_bullets = selector(resume_bullets, 20, 4)

        import copy
        # Keep a clean deep copy of original bullets for comparison and fallback
        original_bullets = copy.deepcopy(selected_bullets)

        def get_flat_bullets(res):
            if isinstance(res, dict):
                return [b for items in res.values() for b in items]
            elif isinstance(res, list):
                return res
            return list(res)

        edited_resume = selected_bullets
        max_attempts = 2
        failed_ids = set()

        for attempt in range(1, max_attempts + 1):
            if attempt == 1:
                # 1st Attempt: Run editor on the entire set
                edited_resume = editor(selected_bullets, sectioned_chunks)
            else:
                # 2nd Attempt: Only re-edit bullets that failed validation
                orig_flat = get_flat_bullets(original_bullets)
                edit_flat = get_flat_bullets(edited_resume)
                orig_map = {b["bullet_id"]: b for b in orig_flat if "bullet_id" in b}
                
                # Reset failed bullets to their original text before retrying
                for b in edit_flat:
                    b_id = b.get("bullet_id")
                    if b_id in failed_ids and b_id in orig_map:
                        b["text"] = orig_map[b_id]["text"]
                        b.pop("bold_words", None)

                # Construct subset of only failed bullets to feed to editor
                if isinstance(edited_resume, dict):
                    failed_subset = {}
                    for exp_id, items in edited_resume.items():
                        failed_in_exp = [b for b in items if b.get("bullet_id") in failed_ids]
                        if failed_in_exp:
                            failed_subset[exp_id] = failed_in_exp
                else:
                    failed_subset = [b for b in edited_resume if b.get("bullet_id") in failed_ids]

                # Run editor on the subset (modifies references in edited_resume)
                editor(failed_subset, sectioned_chunks)

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
                    orig_flat = get_flat_bullets(original_bullets)
                    edit_flat = get_flat_bullets(edited_resume)
                    orig_map = {b["bullet_id"]: b for b in orig_flat if "bullet_id" in b}

                    for b in edit_flat:
                        b_id = b.get("bullet_id")
                        if b_id in failed_ids and b_id in orig_map:
                            b["text"] = orig_map[b_id]["text"]
                            if "bold_words" in orig_map[b_id]:
                                b["bold_words"] = orig_map[b_id]["bold_words"]
                            else:
                                b.pop("bold_words", None)
        
        return {"message": "Resume generated successfully", "resume": edited_resume}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
