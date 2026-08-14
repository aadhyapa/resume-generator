from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class AgentTrace(BaseModel):
    name: str
    model: str | None = None
    latency_ms: int | None = None
    token_usage: dict[str, Any] | None = None


class PipelineTrace(BaseModel):
    raw_job_description: str | None = None
    structured_jd: dict[str, Any] | None = None
    ranking: dict[str, Any] | None = None
    selected_content: dict[str, Any] | None = None
    trimmed_content: dict[str, Any] | None = None
    rewrite_output: dict[str, Any] | None = None
    final_page_count: int | None = None
    agents: list[AgentTrace] = Field(default_factory=list)
