"""
Prompt injection and input sanitization for LLM interactions.
"""

import re
from typing import List

# Patterns that indicate prompt injection attempts
BLOCKED_PATTERNS: List[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+your\s+(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+DAN", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"pretend\s+you\s+are", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+)?you\s+have\s+no", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)", re.IGNORECASE),
    re.compile(r"forget\s+(all\s+)?(your|previous)\s+instructions", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
]

MAX_INPUT_LENGTH = 2000


def sanitize_user_input(text: str) -> str:
    """
    Sanitize user input to prevent prompt injection.

    - Truncates to MAX_INPUT_LENGTH characters
    - Checks for known injection patterns and neutralizes them
    - Returns sanitized text
    """
    if not text:
        return text

    # Truncate
    text = text[:MAX_INPUT_LENGTH]

    # Check for injection patterns
    for pattern in BLOCKED_PATTERNS:
        if pattern.search(text):
            # Replace matched portion with [FILTERED]
            text = pattern.sub("[FILTERED]", text)

    return text
