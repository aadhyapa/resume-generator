from __future__ import annotations

import os
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol
import logging

import anthropic
from dotenv import load_dotenv
from google import genai

from llm.retry import call_with_transient_retry

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

logger = logging.getLogger(__name__)

# Non-streaming Anthropic requests need to stay comfortably under the SDK's HTTP
# timeout, so this is a generous default rather than the model's real ceiling
# (128K, which requires streaming). Callers that need more should switch to a
# streaming call rather than raising this indefinitely.
DEFAULT_MAX_TOKENS = 16000


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    latency_ms: int
    token_usage: dict | None = None


@dataclass(frozen=True)
class StructuredLLMResponse:
    data: dict[str, Any]
    model: str
    latency_ms: int
    token_usage: dict | None = None


class LLMClient(Protocol):
    def generate_json(self, *, model: str, prompt: str, temperature: float = 0.1, max_tokens: int = DEFAULT_MAX_TOKENS) -> LLMResponse:
        ...

    def generate_structured(
        self,
        *,
        model: str,
        prompt: str,
        tool_name: str,
        tool_description: str,
        schema: dict[str, Any],
        temperature: float = 0.1,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> StructuredLLMResponse:
        ...


class ProviderLLMClient:
    def __init__(self):
        self._anthropic = None
        self._gemini = None

    def generate_json(self, *, model: str, prompt: str, temperature: float = 0.1, max_tokens: int = DEFAULT_MAX_TOKENS) -> LLMResponse:
        started = perf_counter()
        def _execute():
            if model.startswith("claude"):
                return self._generate_anthropic(model, prompt, temperature, max_tokens)
            else:
                return self._generate_gemini(model, prompt, temperature)
        text, usage = call_with_transient_retry(_execute, label=f"generate_json ({model})")
        return LLMResponse(text=text, model=model, latency_ms=int((perf_counter() - started) * 1000), token_usage=usage)

    def generate_structured(
        self,
        *,
        model: str,
        prompt: str,
        tool_name: str,
        tool_description: str,
        schema: dict[str, Any],
        temperature: float = 0.1,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> StructuredLLMResponse:
        """Force a schema-conformant response via strict tool use.

        Unlike `generate_json` (free-text JSON the caller must parse and hope is
        well-formed), this constrains the model's output directly: Claude can only
        respond by calling `tool_name` with arguments matching `schema`, and the
        SDK hands back an already-parsed dict. There's no free-text JSON to
        truncate, fence, or drop a delimiter in.

        Only implemented against Anthropic today. Non-Claude models fall back to
        `generate_json` + best-effort parsing, since they're not routed through
        strict tool use here.
        """
        started = perf_counter()
        if not model.startswith("claude"):
            from llm.json_utils import parse_json_object

            response = self.generate_json(model=model, prompt=prompt, temperature=temperature, max_tokens=max_tokens)
            data = parse_json_object(response.text, source=f"{model} (json mode)", repair=True)
            return StructuredLLMResponse(data=data, model=model, latency_ms=response.latency_ms, token_usage=response.token_usage)

        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        def _execute():
            return self._anthropic.messages.create(
                model=model,
                max_tokens=max_tokens,
                tools=[
                    {
                        "name": tool_name,
                        "description": tool_description,
                        "input_schema": schema,
                        "strict": True,
                    }
                ],
                tool_choice={"type": "tool", "name": tool_name},
                messages=[{"role": "user", "content": prompt}],
            )

        try:
            response = call_with_transient_retry(_execute, label=f"generate_structured ({model})")
        except anthropic.BadRequestError as e:
            logger.error("Anthropic BadRequestError (structured): %s", e)
            logger.error("Anthropic response body: %s", getattr(e, "response", None))
            raise
        except Exception as e:
            logger.error("Anthropic exception (structured): %s", e)
            raise

        tool_use = next(
            (block for block in response.content if getattr(block, "type", None) == "tool_use" and block.name == tool_name),
            None,
        )
        if tool_use is None:
            raise ValueError(
                f"Model did not call the '{tool_name}' tool (stop_reason={response.stop_reason}). "
                "This means the request itself is malformed (e.g. schema too large/invalid), "
                "not a formatting slip in the model's output."
            )

        usage = getattr(response, "usage", None)
        return StructuredLLMResponse(
            data=tool_use.input,
            model=model,
            latency_ms=int((perf_counter() - started) * 1000),
            token_usage=usage.model_dump() if hasattr(usage, "model_dump") else None,
        )

    def _generate_anthropic(self, model: str, prompt: str, temperature: float, max_tokens: int) -> tuple[str, dict | None]:
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        try:
            response = self._anthropic.messages.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
        except anthropic.BadRequestError as e:
            logger.error("Anthropic BadRequestError: %s", e)
            logger.error("Anthropic response body: %s", getattr(e, "response", None))
            raise
        except Exception as e:
            logger.error("Anthropic exception: %s", e)
            raise
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
        response = self._gemini.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "temperature": temperature,
                "response_mime_type": "application/json",
            }
        )
        return (response.text or "").strip(), None
