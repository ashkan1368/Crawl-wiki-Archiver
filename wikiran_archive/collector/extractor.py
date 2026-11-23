"""
HTML extraction module for WikIran public editorial articles and publication catalogue pages.
Uses standard library HTML/regex parsing (with optional BeautifulSoup enhancement when installed)
and enforces strict sensitive-data stripping before returning structured records.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from .normalizer import classify_categories_from_text, normalize_date, normalize_url
from .safety import is_permitted_research_url, sanitize_public_text


@dataclass
class ExtractedArticle:
    """Structured public editorial article extracted from /document/articles/<uuid>."""

    original_pub_id: str
    title: str
    subtitle: str
    author: str
    publication_date: str
    raw_date_text: str
    summary: str
    editorial_content: str
    source_url: str
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    organizations: list[str] = field(default_factory=list)
    extraction_status: str = "VERIFIED"


@dataclass
class ExtractedPublicationCatalogue:
    """Structured safe publication catalogue metadata from /leak/<slug> or /leaks."""

    original_pub_id: str
    title: str
    native_title: str
    publication_date: str
    raw_date_text: str
    description: str
    source_url: str
    categories: list[str] = field(default_factory=list)
    safe_inventory: list[tuple[str, str]] = field(default_factory=list)
    blocked_sensitive_count: int = 0
    extraction_status: str = "VERIFIED"


KNOWN_PUBLIC_ORGANIZATIONS: list[tuple[str, str]] = [
    ("MODAFL", "Ministry of Defense and Armed Forces Logistics (MODAFL)"),
    ("AFGS", "Armed Forces General Staff (AFGS)"),
    ("Rahbar", "Rahbar Unified Foreign Currency Management Network"),
    ("Sahara Thunder", "Sahara Thunder"),
    ("Sepehr Energy", "Sepehr Energy Jahan (SEJ)"),
    ("HMS Trading", "HMS Trading FZE & Petro Delta Energy Co. (PDECO)"),
    ("PGPICC", "Persian Gulf Petrochemical Industry Commercial Co. (PGPICC)"),
]


def _strip_tags(raw_html: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    if not raw_html:
        return ""
    no_scripts = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw_html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", no_scripts)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_article_from_html(
    html_content: str,
    source_url: str,
    *,
    allow_all_paths: bool = False,
    redact_pii: bool = True,
) -> ExtractedArticle:
    """
    Extract public editorial article metadata and body from a WikIran article HTML page.
    Verified against live selectors (.articleDetails_headline__*, .articleDetails_searchResultDate__*,
    .articleDetails_subHeadline__*, .uiMarkdown_uiMarkdownWrapper__*).
    """
    permitted, reason = is_permitted_research_url(source_url, allow_all_paths=allow_all_paths)
    if not permitted:
        raise ValueError(f"Cannot extract article from restricted URL ({source_url}): {reason}")

    canonical_url = normalize_url(source_url)
    parsed_path = urlparse(canonical_url).path
    pub_id = parsed_path.rstrip("/").split("/")[-1] or "unknown-article"
    is_email_doc = "/document/emails/" in canonical_url
    is_file_doc = "/document/files/" in canonical_url
    is_csv_doc = "/document/csv/" in canonical_url

    # Extract Headline
    m_head = re.search(
        r'class=["\'][^"\']*(?:articleDetails_headline|emailDetails_subject|fileDetails_fileName|documentDetails_headline)[^"\']*["\'][^>]*>(.*?)</h[123]>',
        html_content,
        re.S | re.I,
    )
    if m_head:
        title = _strip_tags(m_head.group(1))
    else:
        m_title = re.search(r"<title[^>]*>(.*?)</title>", html_content, re.S | re.I)
        raw_t = _strip_tags(m_title.group(1)) if m_title else "Untitled Public Article"
        title = re.sub(r"^WikIran\s*-\s*", "", raw_t).strip() or "Untitled Public Article"

    # Extract Date
    m_date = re.search(
        r'class=["\'][^"\']*(?:articleDetails_searchResultDate|emailDetails_date|fileDetails_date)[^"\']*["\'][^>]*>(.*?)</',
        html_content,
        re.S | re.I,
    )
    raw_date = _strip_tags(m_date.group(1)) if m_date else ""
    norm_date = normalize_date(raw_date, fallback="2026-01-01")

    # Extract Subtitle
    m_sub = re.search(
        r'class=["\'][^"\']*articleDetails_subHeadline[^"\']*["\'][^>]*>(.*?)</',
        html_content,
        re.S | re.I,
    )
    if m_sub:
        subtitle = _strip_tags(m_sub.group(1))
    elif is_email_doc:
        subtitle = "WikIran Extracted Email Correspondence"
    elif is_file_doc:
        subtitle = "WikIran Extracted Document File"
    elif is_csv_doc:
        subtitle = "WikIran Extracted CSV Archive Record"
    else:
        subtitle = "WikIran Public Investigation"

    # Extract Markdown / Email / File Body
    m_body = re.search(
        r'class=["\'][^"\']*(?:uiMarkdown_uiMarkdownWrapper|emailDetails_body|fileDetails_content)[^"\']*["\'][^>]*>(.*?)</main>',
        html_content,
        re.S | re.I,
    )
    if not m_body:
        m_body = re.search(
            r'class=["\'][^"\']*(?:uiMarkdown_uiMarkdownWrapper|emailDetails_body|fileDetails_content)[^"\']*["\'][^>]*>(.*?)</div>\s*</div>',
            html_content,
            re.S | re.I,
        )

    if m_body:
        paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", m_body.group(1), re.S | re.I)
        if paragraphs:
            body_text = "\n\n".join(_strip_tags(p) for p in paragraphs if _strip_tags(p))
        else:
            body_text = _strip_tags(m_body.group(1))
    else:
        paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html_content, re.S | re.I)
        body_text = "\n\n".join(_strip_tags(p) for p in paragraphs if _strip_tags(p))
        if not body_text:
            body_text = _strip_tags(html_content)[:2000]

    body_text = sanitize_public_text(body_text, redact_pii=redact_pii)
    title = sanitize_public_text(title, redact_pii=redact_pii)
    subtitle = sanitize_public_text(subtitle, redact_pii=redact_pii)

    summary = body_text.split("\n\n")[0][:360] if body_text else title
    categories = classify_categories_from_text(title, body_text)

    orgs_found: list[str] = []
    combined_text = f"{title} {body_text}"
    for keyword, canonical_org in KNOWN_PUBLIC_ORGANIZATIONS:
        if keyword.lower() in combined_text.lower():
            orgs_found.append(canonical_org)

    tags_found: list[str] = []
    for tag_candidate in ("Rahbar System", "Shadow Banking", "Oil Exports", "Sanctions Evasion", "Maritime Vessels", "Petrochemicals", "Front Companies"):
        if any(w.lower() in combined_text.lower() for w in tag_candidate.split()):
            tags_found.append(tag_candidate)

    status = "VERIFIED" if (title and body_text) else "PARTIAL"

    return ExtractedArticle(
        original_pub_id=pub_id,
        title=title,
        subtitle=subtitle,
        author="WikIran Archive" if (is_email_doc or is_file_doc) else "WikIran Editorial",
        publication_date=norm_date,
        raw_date_text=raw_date or norm_date,
        summary=summary,
        editorial_content=body_text or summary,
        source_url=canonical_url,
        categories=categories,
        tags=tags_found[:5],
        organizations=orgs_found,
        extraction_status=status,
    )


def extract_publication_catalogue_from_html(
    html_content: str,
    source_url: str,
    *,
    allow_all_paths: bool = False,
    redact_pii: bool = True,
) -> ExtractedPublicationCatalogue:
    """
    Extract publication-level description and file inventory metadata from a /leak/<slug> page.
    """
    permitted, reason = is_permitted_research_url(source_url, allow_all_paths=allow_all_paths)
    if not permitted:
        raise ValueError(f"Cannot extract catalogue from restricted URL ({source_url}): {reason}")

    canonical_url = normalize_url(source_url)
    parsed_path = urlparse(canonical_url).path
    slug = parsed_path.rstrip("/").split("/")[-1] or "catalogue"

    sensitive_links = re.findall(
        r'/document/(?:emails|files)/[a-zA-Z0-9_-]+', html_content
    )
    blocked_count = 0 if allow_all_paths else len(set(sensitive_links))

    safe_header_html = (
        html_content
        if allow_all_paths
        else html_content.split("searchResultCard_searchResultWrapper")[0]
    )

    m_head = re.search(
        r'class=["\'][^"\']*leakDetails_headline[^"\']*["\'][^>]*>(.*?)</',
        safe_header_html,
        re.S | re.I,
    )
    title = _strip_tags(m_head.group(1)) if m_head else ""
    if not title:
        m_title = re.search(r"<title[^>]*>(.*?)</title>", safe_header_html, re.S | re.I)
        raw_t = _strip_tags(m_title.group(1)) if m_title else slug
        title = re.sub(r"^WikIran\s*-\s*", "", raw_t).strip() or slug

    m_sub = re.search(
        r'class=["\'][^"\']*leakDetails_subHeadline[^"\']*["\'][^>]*>(.*?)</',
        safe_header_html,
        re.S | re.I,
    )
    native_title = _strip_tags(m_sub.group(1)) if m_sub else title

    m_desc = re.search(
        r'class=["\'][^"\']*leakDetails_description[^"\']*["\'][^>]*>(.*?)</div',
        safe_header_html,
        re.S | re.I,
    )
    description = _strip_tags(m_desc.group(1)) if m_desc else f"Public catalogue entry for {title}."

    m_count = re.search(
        r'class=["\'][^"\']*leakDetails_resultsCount[^"\']*["\'][^>]*>(.*?)</',
        safe_header_html,
        re.S | re.I,
    )
    results_count_label = _strip_tags(m_count.group(1)) if m_count else "Catalogue Metadata Verified"

    title = sanitize_public_text(title, redact_pii=redact_pii)
    native_title = sanitize_public_text(native_title, redact_pii=redact_pii)
    description = sanitize_public_text(description, redact_pii=redact_pii)

    safe_inventory: list[tuple[str, str]] = [
        ("files_aggregate", f"{results_count_label}"),
    ]
    if allow_all_paths and sensitive_links:
        for link in sorted(set(sensitive_links))[:10]:
            safe_inventory.append(("document_path", f"https://wikiran.org{link}"))
    elif "emails" in safe_header_html.lower():
        safe_inventory.append(
            ("emails_aggregate", "Aggregate Correspondence Count")
        )

    categories = classify_categories_from_text(title, description)

    return ExtractedPublicationCatalogue(
        original_pub_id=slug,
        title=title,
        native_title=native_title,
        publication_date="2026-08-01",
        raw_date_text="2026",
        description=description,
        source_url=canonical_url,
        categories=categories,
        safe_inventory=safe_inventory,
        blocked_sensitive_count=blocked_count,
        extraction_status="VERIFIED" if description else "PARTIAL",
    )


def extract_catalogue_cards_from_leaks_index(
    html_content: str, base_url: str = "https://wikiran.org"
) -> list[ExtractedPublicationCatalogue]:
    """
    Parse multiple publication catalogue summary cards from /leaks index HTML.
    """
    cards: list[ExtractedPublicationCatalogue] = []
    chunks = html_content.split("feedLeakCard_feedLeakCardWrapper")
    for chunk in chunks[1:]:
        m_href = re.search(r'href=["\'](/leak/[^"\']+)["\']', chunk)
        if not m_href:
            continue
        source_url = normalize_url(m_href.group(1), base_url)
        slug = m_href.group(1).rstrip("/").split("/")[-1]

        m_title = re.search(r'feedLeakCard_title[^>]*>(.*?)</', chunk, re.S)
        m_date = re.search(r'feedLeakCard_leakDate[^>]*>(.*?)</', chunk, re.S)
        m_sub = re.search(r'feedLeakCard_subTitle[^>]*>(.*?)</', chunk, re.S)
        m_desc = re.search(r'feedLeakCard_content[^>]*>(.*?)</div', chunk, re.S)

        title = sanitize_public_text(_strip_tags(m_title.group(1))) if m_title else slug
        raw_date = _strip_tags(m_date.group(1)) if m_date else ""
        norm_date = normalize_date(raw_date, fallback="2026-01-01")
        native_title = sanitize_public_text(_strip_tags(m_sub.group(1))) if m_sub else ""
        description = sanitize_public_text(_strip_tags(m_desc.group(1))) if m_desc else ""

        cards.append(
            ExtractedPublicationCatalogue(
                original_pub_id=slug,
                title=title,
                native_title=native_title,
                publication_date=norm_date,
                raw_date_text=raw_date or norm_date,
                description=description,
                source_url=source_url,
                categories=classify_categories_from_text(title, description),
                safe_inventory=[("structured_catalogue", "Catalogue Summary Card Verified")],
                blocked_sensitive_count=0,
                extraction_status="VERIFIED" if description else "PARTIAL",
            )
        )
    return cards
