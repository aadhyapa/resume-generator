from __future__ import annotations

import logging
from pathlib import Path

from config import get_settings
from llm.client import LLMClient, ProviderLLMClient
from llm.retry import call_with_validation_retry
from llm.schema_utils import constrain_id_array_items, constrain_id_field, to_strict_schema
from models.jd import StructuredJobDescription
from models.ranking import ResumeRanking
from models.resume import MasterResume
from serializers.resume_compact import serialize_master_resume_for_ranking

PROMPT_PATH = Path(__file__).with_name("prompts") / "resume_ranker.txt"

TOOL_NAME = "submit_resume_ranking"
TOOL_DESCRIPTION = (
    "Submit the completed ranking of every section, subsection, and bullet in the "
    "master resume against the structured job description."
)

logger = logging.getLogger(__name__)


def _ranking_schema(master_resume: MasterResume) -> dict:
    """Strict schema for this request, with every ID field bound to the exact IDs
    that exist in this master resume. A ranking naming any other ID is rejected
    by Anthropic's schema validation before it ever reaches `tool_use.input` -
    this is what stops `bullet_id: "cert1"` for a resume with no cert1 bullet.
    """
    schema = to_strict_schema(ResumeRanking.model_json_schema())
    section_ids = [s.section_id for s in master_resume.sections]
    subsection_ids = [s.sub_section_id for s in master_resume.sub_sections]
    bullet_ids = [b.bullet_id for b in master_resume.bullets]

    constrain_id_field(schema, "SectionRanking", "section_id", section_ids)
    constrain_id_field(schema, "SubsectionRanking", "section_id", section_ids)
    constrain_id_field(schema, "SubsectionRanking", "sub_section_id", subsection_ids)
    constrain_id_field(schema, "BulletRanking", "bullet_id", bullet_ids)
    constrain_id_array_items(schema, "BulletRanking", "redundant_with", bullet_ids)
    return schema


def rank_resume_content(structured_jd: StructuredJobDescription, master_resume: MasterResume, llm_client: LLMClient | None = None, model: str | None = None) -> ResumeRanking:
    settings = get_settings()
    model_name = model or settings.resume_ranker_model
    logger.info("Starting rank_resume_content with model %s.", model_name)
    logger.info("rank_resume_content Input Structured JD: %s", structured_jd)
    logger.info("rank_resume_content Input Master Resume summary: %d sections, %d bullets", len(master_resume.sections), len(master_resume.bullets))
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = prompt.replace("<structured_jd_json>", structured_jd.model_dump_json(indent=2))
    prompt = prompt.replace("<master_resume>", serialize_master_resume_for_ranking(master_resume))

    client = llm_client or ProviderLLMClient()
    schema = _ranking_schema(master_resume)

    def attempt() -> ResumeRanking:
        response = client.generate_structured(
            model=model_name,
            prompt=prompt,
            tool_name=TOOL_NAME,
            tool_description=TOOL_DESCRIPTION,
            schema=schema,
            temperature=0.1,
        )
        logger.debug("rank_resume_content raw tool input: %s", response.data)
        return ResumeRanking.model_validate(response.data).validate_against_master_resume(master_resume)

    result = call_with_validation_retry(attempt, label="rank_resume_content")
    logger.info("Completed rank_resume_content. Ranked sections: %d, subsections: %d", len(result.section_rankings), len(result.subsection_rankings))
    logger.info("ResumeRanking Output: %s", result)
    return result
