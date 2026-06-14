from google import genai
from dotenv import load_dotenv
import os
import json

# Get current file directory and backend directory to locate files
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
dotenv_path = os.path.join(backend_dir, ".env")

load_dotenv(dotenv_path)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def extract_keywords(job_description):
    '''
    This function extracts keywords from a job description using the Gemini API.
    :param: job_description (str): The job description to extract keywords from.
    :return: dict: A dictionary containing the extracted keywords, or None if the extraction fails.
    '''
    prompt_path = os.path.join(current_dir, "prompts", "keyword_extraction.txt")
    json_path = os.path.join(current_dir, "formats", "keyword_extraction.json")

    with open(prompt_path, "r", encoding="utf-8") as f:
        keyword_extraction_prompt = f.read()

    with open(json_path, "r", encoding="utf-8") as f:
        json_schema = f.read()

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=f"{keyword_extraction_prompt} \n {json_schema} \n {job_description}",
        config={"temperature": 0.1}
    )

    # Parse and validate JSON
    raw_text = response.text.strip()

    try:
        json_output = json.loads(raw_text)
        return json_output
    except json.JSONDecodeError as e:
        return None