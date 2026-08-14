import json
from json import JSONDecodeError


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


def _line_excerpt(text: str, line_number: int, *, radius: int = 2) -> str:
    lines = text.splitlines() or [""]
    start = max(line_number - radius, 1)
    end = min(line_number + radius, len(lines))
    return "\n".join(f"{line_no}: {lines[line_no - 1]}" for line_no in range(start, end + 1))


def parse_json_object(raw_text: str, *, source: str = "LLM response"):
    cleaned = strip_json_fences(raw_text)
    try:
        return json.loads(cleaned, strict=False)
    except JSONDecodeError as exc:
        excerpt = _line_excerpt(cleaned, exc.lineno)
        raise LLMJSONParseError(
            f"Invalid JSON from {source}: {exc.msg} at line {exc.lineno} "
            f"column {exc.colno} (char {exc.pos}). Nearby response lines:\n{excerpt}"
        ) from exc
