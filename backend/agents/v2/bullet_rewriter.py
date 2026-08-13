import json
from pathlib import Path

from config import get_settings
from llm.client import LLMClient, ProviderLLMClient
from llm.json_utils import parse_json_object
from models.jd import StructuredJobDescription
from models.resume import MasterResume
from models.rewriting import BulletRewriteResponse
from models.selection import SelectedResumeContent
from serializers.resume_compact import serialize_selected_content_for_rewriter

PROMPT_PATH = Path(__file__).with_name("prompts") / "bullet_rewriter.txt"


def rewrite_selected_bullets(structured_jd: StructuredJobDescription, master_resume: MasterResume, selected: SelectedResumeContent, llm_client: LLMClient | None = None, model: str | None = None, compression: bool = False) -> BulletRewriteResponse:
    settings = get_settings()
    selected_ids = selected.selected_bullet_ids()
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    compression_instruction = "The rewritten resume exceeds one page. Compress wording while preserving every factual claim, metric, technology, and accomplishment." if compression else "Not active."
    prompt = prompt.replace("<compression_instruction>", compression_instruction)
    prompt = prompt.replace("<schema_json>", json.dumps(BulletRewriteResponse.model_json_schema(), indent=2))
    prompt = prompt.replace("<structured_jd_json>", structured_jd.model_dump_json(indent=2))
    prompt = prompt.replace("<selected_resume>", serialize_selected_content_for_rewriter(master_resume, selected))
    client = llm_client or ProviderLLMClient()
    response = client.generate_json(model=model or settings.bullet_rewriter_model, prompt=prompt, temperature=0.1, max_tokens=5000)
    return BulletRewriteResponse.model_validate(parse_json_object(response.text)).validate_against_selection(master_resume, selected_ids)
