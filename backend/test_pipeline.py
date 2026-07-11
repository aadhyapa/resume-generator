import os
import json
import asyncio
import sys

# Add backend dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import generate_resume

async def main():
    print("Starting test pipeline execution...")
    
    # Path to the job description file
    jd_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents", "test_data", "simmons_internship.txt")
    
    if not os.path.exists(jd_path):
        print(f"Error: Job description file not found at {jd_path}")
        return
        
    with open(jd_path, "r", encoding="utf-8") as f:
        job_description = f.read()

    print("Running generate_resume API endpoint logic...")
    try:
        # Call the async endpoint function directly
        result = await generate_resume(job_description)
        
        print("\n=== SUCCESS ===")
        print(result["message"])
        print("\nGenerated resume structure (first 3 experience groups or bullets shown):")
        
        resume = result["edited_resume"]
        if isinstance(resume, dict):
            for exp_id, bullets in list(resume.items())[:3]:
                print(f"\nExperience ID: {exp_id} ({len(bullets)} bullets)")
                for b in bullets:
                    print(f"  - [{b.get('bullet_id')}] {b.get('text')}")
                    if "bold_words" in b:
                        print(f"    (Bold words: {b['bold_words']})")
        else:
            for b in list(resume)[:5]:
                print(f"  - [{b.get('bullet_id')}] (Experience: {b.get('experience_id')}) (Edited: {b.get('edited')}) {b.get('text')}")
                if "bold_words" in b:
                    print(f"    (Bold words: {b['bold_words']})")
                    
    except Exception as e:
        print("\n=== ERROR ===")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
