from __future__ import annotations

import json
import logging
from pathlib import Path

from config import get_settings
from llm.client import LLMClient, ProviderLLMClient
from llm.json_utils import parse_json_object
from models.jd import StructuredJobDescription

PROMPT_PATH = Path(__file__).with_name("prompts") / "jd_preprocessor.txt"

logger = logging.getLogger(__name__)


def preprocess_job_description(raw_job_description: str, llm_client: LLMClient | None = None, model: str | None = None) -> StructuredJobDescription:
    settings = get_settings()
    model_name = model or settings.jd_preprocessor_model
    logger.info("Starting preprocess_job_description with model %s. Input JD length: %d", model_name, len(raw_job_description))
    logger.debug("Raw Job Description Input: %s", raw_job_description)
    schema = StructuredJobDescription.model_json_schema()
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = prompt.replace("<schema_json>", json.dumps(schema, indent=2))
    prompt = prompt.replace("<raw_job_description>", raw_job_description)
    client = llm_client or ProviderLLMClient()
    response = client.generate_json(model=model_name, prompt=prompt, temperature=0.1, max_tokens=4000)
    result = StructuredJobDescription.model_validate(parse_json_object(response.text, source="v2 jd_preprocessor", repair=True))
    logger.info("Completed preprocess_job_description. Output role: %s, company: %s, requirements count: %d", result.role, result.company, len(result.requirements))
    logger.debug("StructuredJobDescription Output: %s", result)
    return result
