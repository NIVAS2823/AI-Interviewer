import json
import re
import logging

logger = logging.getLogger(__name__)

def extract_single_json(text: str):
    """
    Extract a valid JSON object from LLM output by scanning for the first {...}.
    """
    if not text:
        return None

    raw = text.strip()

    # 1. Remove code fences
    raw = re.sub(r"```json", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"```", "", raw)

    # 2. Find first { ... } block
    match = re.search(r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}", raw)
    if not match:
        return None

    json_str = match.group(0)

    try:
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"JSON decode failed: {e}. Raw JSON: {json_str}")
        return None