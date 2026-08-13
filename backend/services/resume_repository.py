import copy
import json
from pathlib import Path
from typing import Any

from models.resume import MasterResume

DEFAULT_RESUME_PATH = Path(__file__).resolve().parents[1] / "test_data" / "resume_data_embedded.json"


def load_master_resume(path: str | Path = DEFAULT_RESUME_PATH) -> MasterResume:
    with Path(path).open("r", encoding="utf-8") as file:
        return MasterResume.model_validate(json.load(file))


def selected_content_to_resume(master_resume: MasterResume, selected_bullets: list[dict[str, Any]]) -> dict[str, Any]:
    from algorithms.formatter import formater
    return formater(copy.deepcopy(selected_bullets), master_resume.to_raw_dict())
