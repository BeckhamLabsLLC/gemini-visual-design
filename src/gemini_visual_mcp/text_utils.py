"""Helpers for parsing model text output."""

import json
import re
from typing import Any

# A fenced block anywhere in the response, not only at the very start. The
# previous implementation only stripped a fence when the response *began*
# with one, so any preamble ("Here's your analysis:") defeated it.
_FENCE = re.compile(r"```[a-zA-Z0-9_+-]*\s*\n(.*?)(?:\n\s*```|\Z)", re.DOTALL)


def strip_code_fences(text: str) -> str:
    """Return the contents of the first fenced block, or the stripped input."""
    if not text:
        return ""
    match = _FENCE.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def parse_json_response(text: str) -> tuple[Any | None, str | None]:
    """Parse model output as JSON, tolerating code fences.

    Returns (value, error). Never raises.
    """
    candidate = strip_code_fences(text)
    try:
        return json.loads(candidate), None
    except json.JSONDecodeError as e:
        return None, str(e)
