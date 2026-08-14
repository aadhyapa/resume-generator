import json
from pathlib import Path

from config import get_settings
from llm.client import LLMClient, ProviderLLMClient
from llm.json_utils import parse_json_object
from models.jd import StructuredJobDescription

PROMPT_PATH = Path(__file__).with_name("prompts") / "jd_preprocessor.txt"


def preprocess_job_description(raw_job_description: str, llm_client: LLMClient | None = None, model: str | None = None) -> StructuredJobDescription:
    settings = get_settings()
    schema = StructuredJobDescription.model_json_schema()
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = prompt.replace("<schema_json>", json.dumps(schema, indent=2))
    prompt = prompt.replace("<raw_job_description>", raw_job_description)
    client = llm_client or ProviderLLMClient()
    response = client.generate_json(model=model or settings.jd_preprocessor_model, prompt=prompt, temperature=0.1, max_tokens=4000)
    return StructuredJobDescription.model_validate(parse_json_object(response.text, source="v2 jd_preprocessor"))
