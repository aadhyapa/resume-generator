from __future__ import annotations

import json
import logging
from pathlib import Path

from config import get_settings
from llm.client import LLMClient, ProviderLLMClient
from llm.json_utils import parse_json_object
from models.jd import StructuredJobDescription
from models.ranking import ResumeRanking
from models.resume import MasterResume
from serializers.resume_compact import serialize_master_resume_for_ranking

PROMPT_PATH = Path(__file__).with_name("prompts") / "resume_ranker.txt"

logger = logging.getLogger(__name__)


def rank_resume_content(structured_jd: StructuredJobDescription, master_resume: MasterResume, llm_client: LLMClient | None = None, model: str | None = None) -> ResumeRanking:
    print("AADHYA")
    settings = get_settings()
    model_name = model or settings.resume_ranker_model
    logger.info("Starting rank_resume_content with model %s.", model_name)
    print("AADHYA1")
    logger.info("rank_resume_content Input Structured JD: %s", structured_jd)
    logger.info("rank_resume_content Input Master Resume summary: %d sections, %d bullets", len(master_resume.sections), len(master_resume.bullets))
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    print("AADHYA2")
    prompt = prompt.replace("<schema_json>", json.dumps(ResumeRanking.model_json_schema(), indent=2))
    print("AADHYA3")
    prompt = prompt.replace("<structured_jd_json>", structured_jd.model_dump_json(indent=2))
    print("AADHYA4")
    prompt = prompt.replace("<master_resume>", serialize_master_resume_for_ranking(master_resume))
    client = llm_client or ProviderLLMClient()
    response = client.generate_json(model=model_name, prompt=prompt, temperature=0.1, max_tokens=8000)
    result = ResumeRanking.model_validate(parse_json_object(response.text)).validate_against_master_resume(master_resume)
    logger.info("Completed rank_resume_content. Ranked sections: %d, subsections: %d", len(result.section_rankings), len(result.subsection_rankings))
    logger.info("ResumeRanking Output: %s", result)
    return result
