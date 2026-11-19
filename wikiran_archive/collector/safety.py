"""
Strict safety, scope restriction, and PII redaction filters.
Ensures that exposed private correspondence, banking records, identity documents,
account numbers, confidential contracts, and personal identifiers are never
collected, indexed, or stored.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

FORBIDDEN_URL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"/document/emails/", re.IGNORECASE),
    re.compile(r"/document/files/", re.IGNORECASE),
    re.compile(r"/files/leaks/", re.IGNORECASE),
    re.compile(r"dataTypes%5B0%5D=emails", re.IGNORECASE),
    re.compile(r"dataTypes\[0\]=emails", re.IGNORECASE),
    re.compile(r"dataTypes%5B0%5D=files", re.IGNORECASE),
    re.compile(r"dataTypes\[0\]=files", re.IGNORECASE),
    re.compile(r"\.(pst|eml|msg|mbox|zip|rar|7z|xlsx|xls|csv|doc|docx|pdf)$", re.IGNORECASE),
]

PERMITTED_PATH_PREFIXES: tuple[str, ...] = (
    "/",
    "/robots.txt",
    "/sitemap.xml",
    "/leaks",
    "/archives",
    "/about",
    "/search",
    "/document/articles/",
    "/leak/",
)

# Regex patterns for accidental private identifiers in text
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
IBAN_REGEX = re.compile(r"\b(?:IR|AE|TR|DE|GB|CH|CN)\d{2}[A-Z0-9]{12,26}\b")
ACCOUNT_NUM_REGEX = re.compile(r"\b(?:Account|Acct|IBAN|Sheba|Card)\s*(?:No\.?|Number|#|:)?\s*[\d\-\s]{8,24}\b", re.IGNORECASE)
NATIONAL_ID_REGEX = re.compile(r"\b(?:National\s+ID|Passport\s+No\.?|Code\s+Melli)\s*[:#]?\s*[A-Z0-9\-]{6,15}\b", re.IGNORECASE)


def is_permitted_research_url(url: str, allow_all_paths: bool = False) -> tuple[bool, str]:
    """
    Determine whether a URL is permitted for research collection.
    When allow_all_paths=True (Full Archive Mode), permits all wikiran.org paths
    including /document/emails/*, /document/files/*, and attachment links.
    Returns (is_permitted, reason).
    """
    if not url or not url.strip():
        return False, "Empty URL"

    parsed = urlparse(url)
    if parsed.scheme and parsed.scheme not in ("http", "https"):
        return False, f"Unsupported scheme: {parsed.scheme}"

    if parsed.netloc and "wikiran.org" not in parsed.netloc.lower():
        return False, f"External domain not permitted: {parsed.netloc}"

    if allow_all_paths:
        return True, "Permitted under Full Archive Collection Mode"

    full_path_query = parsed.path + (f"?{parsed.query}" if parsed.query else "")

    for pattern in FORBIDDEN_URL_PATTERNS:
        if pattern.search(full_path_query):
            return False, f"Excluded sensitive path matching pattern: {pattern.pattern}"

    if parsed.path == "/" or any(parsed.path.startswith(p) for p in PERMITTED_PATH_PREFIXES if p != "/"):
        return True, "Permitted public article or catalogue path"

    return False, f"Unverified path outside public research scope: {parsed.path}"


def sanitize_public_text(text: str, redact_pii: bool = True) -> str:
    """
    When redact_pii=True (Strict Mode), redacts emails, bank account / IBAN numbers,
    and personal identity numbers. When redact_pii=False (Full Archive Mode),
    preserves all raw downloaded text unredacted for full-text search.
    """
    if not text:
        return ""
    if not redact_pii:
        return text.strip()
    cleaned = EMAIL_REGEX.sub("[REDACTED-EMAIL]", text)
    cleaned = IBAN_REGEX.sub("[REDACTED-ACCOUNT]", cleaned)
    cleaned = ACCOUNT_NUM_REGEX.sub("[REDACTED-ACCOUNT]", cleaned)
    cleaned = NATIONAL_ID_REGEX.sub("[REDACTED-ID]", cleaned)
    return cleaned.strip()

