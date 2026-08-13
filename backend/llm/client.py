import os
from dataclasses import dataclass
from time import perf_counter
from typing import Protocol

import anthropic
from dotenv import load_dotenv
from google import genai

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    latency_ms: int
    token_usage: dict | None = None


class LLMClient(Protocol):
    def generate_json(self, *, model: str, prompt: str, temperature: float = 0.1, max_tokens: int = 4000) -> LLMResponse:
        ...


class ProviderLLMClient:
    def __init__(self):
        self._anthropic = None
        self._gemini = None

    def generate_json(self, *, model: str, prompt: str, temperature: float = 0.1, max_tokens: int = 4000) -> LLMResponse:
        started = perf_counter()
        if model.startswith("claude"):
            text, usage = self._generate_anthropic(model, prompt, temperature, max_tokens)
        else:
            text, usage = self._generate_gemini(model, prompt, temperature)
        return LLMResponse(text=text, model=model, latency_ms=int((perf_counter() - started) * 1000), token_usage=usage)

    def _generate_anthropic(self, model: str, prompt: str, temperature: float, max_tokens: int) -> tuple[str, dict | None]:
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = self._anthropic.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        text = ""
        for block in response.content:
            if getattr(block, "type", None) == "text":
                text += block.text
            elif hasattr(block, "text") and getattr(block, "type", None) != "thinking":
                text += block.text
        usage = getattr(response, "usage", None)
        return text.strip(), usage.model_dump() if hasattr(usage, "model_dump") else None

    def _generate_gemini(self, model: str, prompt: str, temperature: float) -> tuple[str, dict | None]:
        if self._gemini is None:
            self._gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = self._gemini.models.generate_content(model=model, contents=prompt, config={"temperature": temperature})
        return (response.text or "").strip(), None
