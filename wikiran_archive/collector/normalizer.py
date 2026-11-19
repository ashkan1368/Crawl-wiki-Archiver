"""
Data normalization module for dates, URLs, categories, and public organizational mentions.
"""

from __future__ import annotations

import html
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse, urlunparse

MONTH_MAP: dict[str, int] = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def normalize_date(raw_date: str | None, fallback: str = "2026-01-01") -> str:
    """
    Normalize date strings such as 'Nov 2026', 'August 15, 2025', '2026-11-01', or '6/26/2022'
    into canonical ISO-8601 'YYYY-MM-DD' format.
    """
    if not raw_date:
        return fallback
    cleaned = html.unescape(raw_date).strip()
    if not cleaned:
        return fallback

    # Already YYYY-MM-DD
    m_iso = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", cleaned)
    if m_iso:
        y, m, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
        return f"{y:04d}-{m:02d}-{d:02d}"

    # Format: 'Nov 2026' or 'November 2026'
    m_my = re.match(r"^([A-Za-z]+)\s+(\d{4})$", cleaned)
    if m_my:
        m_name = m_my.group(1).lower()
        year = int(m_my.group(2))
        month = MONTH_MAP.get(m_name[:3], 1)
        return f"{year:04d}-{month:02d}-01"

    # Format: 'Nov 18, 2026' or '18 Nov 2026'
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Search for Month YYYY anywhere inside text
    m_any = re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b", cleaned, re.I)
    if m_any:
        month = MONTH_MAP.get(m_any.group(1).lower()[:3], 1)
        year = int(m_any.group(2))
        return f"{year:04d}-{month:02d}-01"

    return fallback


def normalize_url(url: str, base_url: str = "https://wikiran.org") -> str:
    """Resolve relative links against base_url and strip fragments/trailing slashes."""
    if not url:
        return base_url
    unescaped = html.unescape(url.strip())
    joined = urljoin(base_url, unescaped)
    parsed = urlparse(joined)
    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((parsed.scheme or "https", parsed.netloc or "wikiran.org", path, "", parsed.query, ""))


def classify_categories_from_text(title: str, content: str) -> list[str]:
    """Map article or publication text to canonical category slugs."""
    combined = f"{title} {content}".lower()
    matched: list[str] = []
    if any(k in combined for k in ("rahbar", "bank", "currency", "exchange", "financial", "ledger")):
        matched.append("shadow-banking-currency")
    if any(k in combined for k in ("oil", "tanker", "vessel", "maritime", "petroleum", "sepehr", "sahara")):
        matched.append("maritime-oil-trade")
    if any(k in combined for k in ("modafl", "defense", "military", "missile", "drone", "procurement", "afgs")):
        matched.append("defense-industrial-procurement")
    if any(k in combined for k in ("front compan", "sanction", "shell", "broker", "intermediar", "hms", "pdeco")):
        matched.append("front-companies-sanctions")
    if any(k in combined for k in ("ministry", "petrochemical", "pgpicc", "state", "institution")):
        matched.append("state-economic-institutions")
    if not matched:
        matched.append("front-companies-sanctions")
    return matched
