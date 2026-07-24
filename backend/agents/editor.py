import os
import json
import logging
import anthropic
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Find directory paths
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
dotenv_path = os.path.join(backend_dir, ".env")
load_dotenv(dotenv_path)

# Initialize Gemini Client
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def editor(resume, job_description_chunks, min_chars=50, max_chars=300):
    """
    Wrapper function that aligns the selected resume bullet points with the
    job description chunks using the editor.txt prompt.

    :param resume: dict (experience_id -> list of bullets) or list of bullets
    :param job_description_chunks: dict or list of job description sections
    :param min_chars: minimum length constraint for the edited bullet text
    :param max_chars: maximum length constraint for the edited bullet text
    :return: The modified resume object in its original structure
    """
    logger.info("Entering editor")
    # 1. Flatten the resume input to a list of bullet dicts if it is a dictionary
    flat_resume = []
    if isinstance(resume, dict):
        for bullets_list in resume.values():
            flat_resume.extend(bullets_list)
    else:
        flat_resume = resume

    trimmed_resume = [{'bullet_id': bullet['bullet_id'], 'text': bullet['text']} for bullet in flat_resume if isinstance(bullet, dict) and 'bullet_id' in bullet]

    # 2. Read the prompt template
    prompt_template_path = os.path.join(current_dir, "prompts", "editor.txt")
    if not os.path.exists(prompt_template_path):
        # Fallback default prompt if file doesn't exist
        prompt_text = (
            "System: You are an expert resume editor. Align the user's resume bullet points to the provided job description chunks.\n"
            "Inputs:\n- <resume_json>\n- <job_chunks>\n- <max_chars>\n- <min_chars>\n"
            "Rules:\n1. Edit ONLY if Necessary.\n2. Modify ONLY \"text\".\n3. Do Not Fabricate.\n"
            "4. WHO Formula.\n5. Strict Constraints.\n\nOutput Format:\nReturn ONLY the modified JSON array."
        )
    else:
        with open(prompt_template_path, "r", encoding="utf-8") as f:
            prompt_text = f.read()

    # 3. Interpolate variables into the prompt template
    prompt = prompt_text
    prompt = prompt.replace("<resume_json>", json.dumps(trimmed_resume, indent=2))
    prompt = prompt.replace("<job_chunks>", json.dumps(job_description_chunks, indent=2))
    prompt = prompt.replace("<max_chars>", str(max_chars))
    prompt = prompt.replace("<min_chars>", str(min_chars))

    modified_bullets = None

    # 4. Call LLM
    try:
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=200000,
            messages=[
                {"role": "user", "content": prompt},
            ]
        )
        
        raw_response = response.content[0].text.strip()
        
        # Strip markdown fences if present
        if raw_response.startswith("```"):
            lines = raw_response.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_response = "\n".join(lines).strip()

        # Parse output JSON
        modified_bullets = json.loads(raw_response)

    except Exception as e:
        logger.error(f"Error during resume editing process: {e}", exc_info=True)
        # Fallback to original bullets on failure
        modified_bullets = trimmed_resume

    # Merge modifications back into original bullets to preserve all metadata keys (e.g. sub_section_id)
    modified_map = {}
    if isinstance(modified_bullets, list):
        for b in modified_bullets:
            if isinstance(b, dict) and 'bullet_id' in b:
                modified_map[b['bullet_id']] = b

    final_bullets = []
    for orig_b in flat_resume:
        if not isinstance(orig_b, dict):
            final_bullets.append(orig_b)
            continue
        b_id = orig_b.get('bullet_id')
        if b_id in modified_map:
            merged_b = dict(orig_b)
            merged_b['text'] = modified_map[b_id].get('text', orig_b.get('text'))
            if 'bold_words' in modified_map[b_id]:
                merged_b['bold_words'] = modified_map[b_id]['bold_words']
            merged_b['edited'] = merged_b['text'] != orig_b.get('text')
            final_bullets.append(merged_b)
        else:
            final_bullets.append(dict(orig_b))

    logger.info("Exiting editor")
    if isinstance(resume, dict):
        final_dict = {}
        for b in final_bullets:
            if not isinstance(b, dict) or 'bullet_id' not in b:
                continue
            for k, v in resume.items():
                if any(isinstance(orig_b, dict) and orig_b.get('bullet_id') == b['bullet_id'] for orig_b in v):
                    if k not in final_dict:
                        final_dict[k] = []
                    final_dict[k].append(b)
                    break
        return final_dict
    else:
        return final_bullets