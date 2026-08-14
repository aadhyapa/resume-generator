import json
import re
from json import JSONDecodeError
from typing import Any


class LLMJSONParseError(ValueError):
    """Raised when an LLM response cannot be parsed as JSON."""


def strip_json_fences(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _truncate_line(line: str, max_line_length: int) -> str:
    if len(line) <= max_line_length:
        return line
    return f"{line[:max_line_length]}..."


def _line_excerpt(text: str, line_number: int, *, radius: int = 2, max_line_length: int = 200) -> str:
    lines = text.splitlines() or [""]
    start = max(line_number - radius, 1)
    end = min(line_number + radius, len(lines))
    return "\n".join(
        f"{line_no}: {_truncate_line(lines[line_no - 1], max_line_length)}"
        for line_no in range(start, end + 1)
    )


def _extract_json_payload(text: str) -> str:
    """Return the likely JSON object/array from an LLM response."""
    start_brace = text.find("{")
    start_bracket = text.find("[")
    if start_brace == -1 and start_bracket == -1:
        return text

    if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
        start_idx = start_brace
        end_char = "}"
    else:
        start_idx = start_bracket
        end_char = "]"

    end_idx = text.rfind(end_char)
    if end_idx == -1 or end_idx <= start_idx:
        return text
    return text[start_idx : end_idx + 1]


def _sanitize_common_json_issues(text: str) -> str:
    """Fix safe, structure-preserving JSON issues often emitted by LLMs."""
    # Drop trailing commas before an object/array close.
    text = re.sub(r",\s*([\]}])", r"\1", text)
    return text


def _repair_missing_separators(text: str) -> str:
    """Conservatively add commas at line boundaries between JSON values.

    This targets common LLM omissions such as adjacent objects in arrays or an
    object/array/string/number/bool/null value followed by the next object key.
    It intentionally operates only across newlines to avoid mutating string
    contents in the middle of a line.
    """
    value_end = r'(?:[}\]"0-9]|true|false|null)'
    next_value_start = r'(?=[\[{"-]|true|false|null|\d)'
    next_key_start = r'(?="[^"\\]*(?:\\.[^"\\]*)*"\s*:)'
    text = re.sub(rf"({value_end})(\s*\n\s*)({next_value_start})", r"\1,\2", text)
    text = re.sub(rf"({value_end})(\s*\n\s*)({next_key_start})", r"\1,\2", text)
    return text


def _raise_parse_error(source: str, text: str, exc: JSONDecodeError) -> None:
    excerpt = _line_excerpt(text, exc.lineno)
    raise LLMJSONParseError(
        f"Invalid JSON from {source}: {exc.msg} at line {exc.lineno} "
        f"column {exc.colno} (char {exc.pos}). Nearby response lines:\n{excerpt}"
    ) from exc


def parse_json_object(raw_text: str, *, source: str = "LLM response", repair: bool = False) -> Any:
    """Parse an LLM response as JSON with useful diagnostics.

    Args:
        raw_text: Raw provider response text.
        source: Human-readable producer name for error messages.
        repair: If true, retry with conservative separator repair after strict
            parsing fails. Use this for production LLM calls, not unit tests that
            verify malformed JSON is rejected.
    """
    cleaned = _sanitize_common_json_issues(_extract_json_payload(strip_json_fences(raw_text)))
    try:
        return json.loads(cleaned)
    except JSONDecodeError as first_err:
        if repair:
            repaired = _repair_missing_separators(cleaned)
            if repaired != cleaned:
                try:
                    return json.loads(repaired)
                except JSONDecodeError:
                    pass
        _raise_parse_error(source, cleaned, first_err)
