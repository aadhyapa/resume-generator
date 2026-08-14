import json
import re

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

def parse_json_object(raw_text: str):
    cleaned = strip_json_fences(raw_text)
    
    # Try parsing directly first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find the JSON boundaries: look for the first '{' or '[' and the last '}' or ']'
    start_brace = cleaned.find('{')
    start_bracket = cleaned.find('[')
    
    start_idx = -1
    end_char = ''
    if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
        start_idx = start_brace
        end_char = '}'
    elif start_bracket != -1:
        start_idx = start_bracket
        end_char = ']'
        
    if start_idx != -1:
        end_idx = cleaned.rfind(end_char)
        if end_idx != -1 and end_idx > start_idx:
            cleaned = cleaned[start_idx:end_idx + 1]

    # Replace common issues like trailing commas: ,} or ,]
    cleaned = re.sub(r',\s*([\]}])', r'\1', cleaned)
    
    # Replace single quotes wrapping keys/values with double quotes if possible,
    # but be careful. A simpler regex-based fix for trailing commas, control characters is usually safer.
    # Strip illegal control characters within JSON strings (except newlines/tabs)
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', lambda m: '\\u{:04x}'.format(ord(m.group(0))) if m.group(0) not in ('\n', '\r', '\t') else m.group(0), cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as first_err:
        # Fallback: strict control character escaping (strict=False permits control characters in strings)
        try:
            return json.loads(cleaned, strict=False)
        except json.JSONDecodeError:
            raise first_err

