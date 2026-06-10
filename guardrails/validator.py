"""
guardrails/validator.py
------------------------
Input validation and prompt injection protection.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional

INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|prior)\s+instructions?",
    r"forget\s+(everything|all|prior|previous)",
    r"(system\s*prompt|base\s*prompt)",
    r"(delete|clear|reset)\s+(agent|memory|context|history)",
    r"(jailbreak|dan\s+mode|act\s+as\s+(an?\s+)?(ai|llm|gpt))",
    r"(sudo|root|admin)\s+(mode|access|override)",
    r"(reveal|show|print|display)\s+(your\s+)?(instructions|prompt|system)",
    r"</?(system|instruction|prompt)>",
    r"\bexecute\s+(code|shell|command|script)\b",
    r"(bomb|weapon|explosive|poison|drug\s+synthesis)",
]


@dataclass
class ValidationResult:
    valid: bool
    error_message: Optional[str] = None
    sanitized_query: Optional[str] = None


def _has_injection(text: str) -> bool:
    lower = text.lower()
    return any(re.search(p, lower) for p in INJECTION_PATTERNS)


def validate_inputs(
    destination: str,
    budget: float,
    days: int,
    travelers: int,
    preferences: list,
    raw_query: str = "",
) -> ValidationResult:
    destination = destination.strip()

    if len(destination) < 2:
        return ValidationResult(valid=False, error_message="Please enter a valid destination.")

    if _has_injection(destination) or (raw_query and _has_injection(raw_query)):
        return ValidationResult(valid=False, error_message="Your query contains restricted content. Please enter a genuine travel request.")

    if budget < 1000:
        return ValidationResult(valid=False, error_message="Budget must be at least Rs 1,000.")
    if budget > 100_000_000:
        return ValidationResult(valid=False, error_message="Budget cannot exceed Rs 10 Crore.")
    if days < 1:
        return ValidationResult(valid=False, error_message="Trip must be at least 1 day.")
    if days > 30:
        return ValidationResult(valid=False, error_message="Trip cannot exceed 30 days.")
    if travelers < 1:
        return ValidationResult(valid=False, error_message="At least 1 traveler required.")
    if travelers > 50:
        return ValidationResult(valid=False, error_message="Maximum 50 travelers supported.")

    safe = re.sub(r"[<>{}\[\]|\\^`]", "", destination)
    return ValidationResult(valid=True, sanitized_query=safe)