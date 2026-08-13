import json
from pathlib import Path

from config import get_settings
from llm.client import LLMClient, ProviderLLMClient
from llm.json_utils import parse_json_object
from models.jd import StructuredJobDescription
from models.ranking import ResumeRanking
from models.resume import MasterResume
from serializers.resume_compact import serialize_master_resume_for_ranking

PROMPT_PATH = Path(__file__).with_name("prompts") / "resume_ranker.txt"


def rank_resume_content(structured_jd: StructuredJobDescription, master_resume: MasterResume, llm_client: LLMClient | None = None, model: str | None = None) -> ResumeRanking:
    settings = get_settings()
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = prompt.replace("<schema_json>", json.dumps(ResumeRanking.model_json_schema(), indent=2))
    prompt = prompt.replace("<structured_jd_json>", structured_jd.model_dump_json(indent=2))
    prompt = prompt.replace("<master_resume>", serialize_master_resume_for_ranking(master_resume))
    client = llm_client or ProviderLLMClient()
    response = client.generate_json(model=model or settings.resume_ranker_model, prompt=prompt, temperature=0.1, max_tokens=8000)
    return ResumeRanking.model_validate(parse_json_object(response.text)).validate_against_master_resume(master_resume)
