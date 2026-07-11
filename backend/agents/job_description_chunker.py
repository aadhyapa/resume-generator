import os
import json
import logging
from google import genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Get current file directory and backend directory to locate files
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
dotenv_path = os.path.join(backend_dir, ".env")

load_dotenv(dotenv_path)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def job_description_chunker(job_description):
    '''
    This function extracts keywords from a job description using the Gemini API.
    :param: job_description (str): The job description to extract keywords from.
    :return: dict: A dictionary containing the extracted chunks of the job description.
    '''
    logger.info("job_description_chunker: Chunking job description...")
    prompt_path = os.path.join(current_dir, "prompts", "job_description_chunker.txt")
    json_path = os.path.join(current_dir, "formats", "job_description_chunker.json")

    with open(prompt_path, "r", encoding="utf-8") as f:
        keyword_extraction_prompt = f.read()

    with open(json_path, "r", encoding="utf-8") as f:
        json_schema = f.read()

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=f"{keyword_extraction_prompt} \n JSON Schema:\n{json_schema} \n Job Description:\n{job_description}",
            config={"temperature": 0.1}
        )

        # Parse and validate JSON
        raw_text = response.text.strip()
        logger.debug(f"job_description_chunker: Raw response from Gemini: {raw_text}")

        # Clean markdown code fences if present
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_text = "\n".join(lines).strip()

        json_output = json.loads(raw_text)
        logger.info("job_description_chunker: Job description chunked successfully.")
        return json_output
    except json.JSONDecodeError as e:
        logger.error(f"job_description_chunker: JSON decode error: {e}. Raw response: {raw_text}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"job_description_chunker: Unexpected error: {e}", exc_info=True)
        return None