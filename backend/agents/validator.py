import os
import json
import logging
from google import genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Find directory paths
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
dotenv_path = os.path.join(backend_dir, ".env")
load_dotenv(dotenv_path)

# Initialize Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def _extract_bullets(resume) -> dict:
    """
    Helper to extract bullet dicts keyed by bullet_id from a resume structure.
    Handles both dict (experience_id -> list of bullets) and flat list formats.
    """
    bullets = {}
    if isinstance(resume, dict):
        for exp_id, items in resume.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and "bullet_id" in item:
                        bullets[item["bullet_id"]] = item
    elif isinstance(resume, list):
        for item in resume:
            if isinstance(item, dict) and "bullet_id" in item:
                bullets[item["bullet_id"]] = item
    return bullets

def validate_resume(original_resume, edited_resume, min_chars=50, max_chars=300) -> dict:
    """
    Validates that:
    1. None of the edited bullet points are fabricated (uses Gemini check).
    2. All edited bullet points are within the character limits.

    :param original_resume: Original resume structure (dict or list)
    :param edited_resume: Edited resume structure (dict or list)
    :param min_chars: Minimum character limit
    :param max_chars: Maximum character limit
    :return: dict containing:
             - "is_valid": bool
             - "character_limit_failures": list of failures
             - "fabrication_failures": list of failures
     """
    orig_map = _extract_bullets(original_resume)
    edit_map = _extract_bullets(edited_resume)

    char_failures = []
    comparisons = []

    # 1. Run Programmatic Character Limit Validation
    for bullet_id, edit_bullet in edit_map.items():
        text = edit_bullet.get("text", "")
        text_len = len(text)
        if text_len < min_chars or text_len > max_chars:
            char_failures.append({
                "bullet_id": bullet_id,
                "text": text,
                "length": text_len,
                "reason": f"Character length {text_len} is out of bounds [{min_chars}, {max_chars}]"
            })

        # Gather comparisons for edited bullets
        orig_bullet = orig_map.get(bullet_id)
        if orig_bullet:
            orig_text = orig_bullet.get("text", "")
            is_edited = orig_text != text
            edit_bullet["edited"] = is_edited
            # Only check for fabrication if the text actually changed
            if is_edited:
                comparisons.append({
                    "id": bullet_id,
                    "original": orig_text,
                    "edited": text
                })
        else:
            edit_bullet["edited"] = False

    # 2. Run LLM-based Fabrication Check (only if there are modifications)
    fab_failures = []
    if comparisons:
        prompt_path = os.path.join(current_dir, "prompts", "validator.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_text = f.read()
        else:
            prompt_text = "System: Identify fabrication in the following pairs of original and edited text. Return JSON list of failures."

        contents = f"{prompt_text}\n\nInput JSON:\n{json.dumps(comparisons, indent=2)}"

        try:
            logger.info(f"Sending {len(comparisons)} bullet comparisons to Gemini fabrication validator...")
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=contents,
                config={"temperature": 0.1}
            )

            raw_response = response.text.strip()
            
            # Clean markdown code fences
            if raw_response.startswith("```"):
                lines = raw_response.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_response = "\n".join(lines).strip()

            if raw_response:
                fab_failures = json.loads(raw_response)
        except Exception as e:
            # If the validation API call fails, log the failure details but do not crash
            logger.error(f"Error during fabrication check API call: {e}", exc_info=True)
            fab_failures = [{
                "id": "API_ERROR",
                "reason": f"Fabrication check failed to execute: {str(e)}"
            }]

    return {
        "is_valid": len(char_failures) == 0 and len(fab_failures) == 0,
        "character_limit_failures": char_failures,
        "fabrication_failures": fab_failures
    }
