"""Customer ka sensitive data LLM ko bhejne se PEHLE mask karo."""
import re

PATTERNS = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("PAN", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")),
    ("CARD", re.compile(r"\b\d(?:[ -]?\d){12,15}\b")),
    ("AADHAAR", re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b")),
    ("PHONE", re.compile(r"(?:\+?91[\s-]?)?\b[6-9]\d{9}\b")),
]


def redact(text: str) -> str:
    for label, rx in PATTERNS:
        text = rx.sub(f"[{label}]", text)
    return text
