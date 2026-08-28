from __future__ import annotations

import logging
from pathlib import Path

from config import get_settings
from llm.client import LLMClient, ProviderLLMClient
from llm.retry import call_with_validation_retry
from llm.schema_utils import constrain_id_field, to_strict_schema
from models.jd import StructuredJobDescription
from models.resume import MasterResume
from models.rewriting import BulletRewriteResponse
from models.selection import SelectedResumeContent
from serializers.resume_compact import selected_bullet_ids_in_master_order, serialize_selected_content_for_rewriter

PROMPT_PATH = Path(__file__).with_name("prompts") / "bullet_rewriter.txt"

TOOL_NAME = "submit_bullet_rewrites"
TOOL_DESCRIPTION = "Submit the rewritten text for every selected bullet, in the same order and IDs as provided."

logger = logging.getLogger(__name__)


def _rewrite_schema(selected_ids: list[str]) -> dict:
    """Strict schema for this request, with `bullet_id` bound to exactly the
    selected bullet IDs - a rewrite naming any other ID is rejected before it
    reaches `tool_use.input`, the same guard as the ranker's ID enums."""
    schema = to_strict_schema(BulletRewriteResponse.model_json_schema())
    constrain_id_field(schema, "RewrittenBullet", "bullet_id", selected_ids)
    return schema


def rewrite_selected_bullets(structured_jd: StructuredJobDescription, master_resume: MasterResume, selected: SelectedResumeContent, llm_client: LLMClient | None = None, model: str | None = None, compression: bool = False) -> BulletRewriteResponse:
    settings = get_settings()
    model_name = model or settings.bullet_rewriter_model
    selected_ids = selected_bullet_ids_in_master_order(master_resume, selected)
    logger.info("Starting rewrite_selected_bullets with model %s. Compression active: %s. Selected bullets count: %d", model_name, compression, len(selected_ids))
    logger.debug("rewrite_selected_bullets Input Structured JD: %s", structured_jd)
    logger.debug("rewrite_selected_bullets Input Selected IDs: %s", selected_ids)
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    compression_instruction = "The rewritten resume exceeds one page. Compress wording while preserving every factual claim, metric, technology, and accomplishment." if compression else "Not active."
    prompt = prompt.replace("<compression_instruction>", compression_instruction)
    prompt = prompt.replace("<structured_jd_json>", structured_jd.model_dump_json(indent=2))
    prompt = prompt.replace("<selected_resume>", serialize_selected_content_for_rewriter(master_resume, selected))

    client = llm_client or ProviderLLMClient()
    schema = _rewrite_schema(selected_ids)

    def attempt() -> BulletRewriteResponse:
        response = client.generate_structured(
            model=model_name,
            prompt=prompt,
            tool_name=TOOL_NAME,
            tool_description=TOOL_DESCRIPTION,
            schema=schema,
            temperature=0.1,
        )
        return BulletRewriteResponse.model_validate(response.data).validate_against_selection(master_resume, selected_ids)

    result = call_with_validation_retry(attempt, label="rewrite_selected_bullets")
    logger.info("Completed rewrite_selected_bullets. Rewritten bullets count: %d", len(result.rewritten_bullets))
    logger.debug("BulletRewriteResponse Output: %s", result)
    return result
