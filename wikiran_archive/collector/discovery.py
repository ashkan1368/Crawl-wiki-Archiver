"""
Source discovery module: inspects robots.txt, public navigation links,
article pagination (/search?tabType=articles&page=N), and publication catalogue index (/leaks, /archives).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .normalizer import normalize_url
from .safety import is_permitted_research_url


@dataclass
class DiscoveryResult:
    """Structured result of inspecting public navigation, sitemaps, and listing pages."""

    article_urls: list[str] = field(default_factory=list)
    catalogue_urls: list[str] = field(default_factory=list)
    document_urls: list[str] = field(default_factory=list)
    crawl_seed_urls: list[str] = field(default_factory=list)
    pagination_pages_found: list[int] = field(default_factory=list)
    blocked_sensitive_urls: list[str] = field(default_factory=list)
    robots_permitted: bool = True
    robots_notes: str = ""


def parse_robots_txt(robots_content: str) -> tuple[bool, str]:
    """
    Inspect robots.txt content for explicit Disallow rules affecting public research paths.
    """
    if not robots_content:
        return True, "Empty robots.txt; standard polite access permitted."

    lines = [line.strip() for line in robots_content.splitlines() if line.strip()]
    disallows: list[str] = []
    for line in lines:
        if line.lower().startswith("disallow:"):
            rule = line.split(":", 1)[1].strip()
            if rule:
                disallows.append(rule)

    if "/" in disallows:
        return False, "robots.txt contains Disallow: /"

    return True, "robots.txt inspected: public research indexing permitted under EU DSM Art. 4 content signals."


def extract_sitemap_urls(xml_content: str, base_url: str = "https://wikiran.org") -> list[str]:
    """Extract <loc>...</loc> URLs from sitemap.xml if present."""
    if not xml_content:
        return []
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml_content, re.I)
    return [normalize_url(u, base_url) for u in locs if u]


def extract_discovered_links(
    html_content: str,
    base_url: str = "https://wikiran.org",
    *,
    allow_all_paths: bool = False,
) -> DiscoveryResult:
    """
    Spider link extractor: extracts permitted article URLs, publication catalogue URLs,
    document/email/file URLs (when allow_all_paths=True), pagination numbers,
    and internal crawl hub links so the spider can traverse to the last page.
    """
    result = DiscoveryResult()
    if not html_content:
        return result

    raw_hrefs = re.findall(r'href=["\']([^"\']+)["\']', html_content)
    # Scan embedded JSON / Next.js __NEXT_DATA__ state for all article, email, file, csv, leak, and archive paths
    embedded_paths = re.findall(
        r'/(?:document/(?:articles|emails|files|csv)/[a-zA-Z0-9_-]+|leak/[a-zA-Z0-9_-]+|archives(?:/[a-zA-Z0-9_-]+)?)',
        html_content,
    )
    # Also scan full https://wikiran.org/... URLs inside scripts or JSON
    embedded_full_urls = re.findall(
        r'https?://(?:www\.)?wikiran\.org/[a-zA-Z0-9_/\-?=&%]+',
        html_content,
    )
    all_candidates = list(raw_hrefs) + list(embedded_paths) + list(embedded_full_urls)

    seen_articles: set[str] = set()
    seen_catalogues: set[str] = set()
    seen_documents: set[str] = set()
    seen_seeds: set[str] = set()
    seen_blocked: set[str] = set()
    pages: set[int] = set()

    for href in all_candidates:
        if (
            href.startswith("/_next")
            or href.startswith("/cdn-cgi")
            or href.startswith("mailto:")
            or href.startswith("javascript:")
        ):
            continue
        full_url = normalize_url(href, base_url)
        permitted, _reason = is_permitted_research_url(full_url, allow_all_paths=allow_all_paths)
        if not permitted:
            if "/document/emails/" in full_url or "/document/files/" in full_url or "/document/csv/" in full_url:
                if full_url not in seen_blocked:
                    seen_blocked.add(full_url)
                    result.blocked_sensitive_urls.append(full_url)
            continue

        if "/document/articles/" in full_url:
            if full_url not in seen_articles:
                seen_articles.add(full_url)
                result.article_urls.append(full_url)
        elif "/leak/" in full_url:
            if full_url not in seen_catalogues:
                seen_catalogues.add(full_url)
                result.catalogue_urls.append(full_url)
        elif allow_all_paths and (
            "/document/emails/" in full_url
            or "/document/files/" in full_url
            or "/document/csv/" in full_url
        ):
            if full_url not in seen_documents:
                seen_documents.add(full_url)
                result.document_urls.append(full_url)
        elif any(
            hub in full_url
            for hub in ("/leaks", "/archives", "/search?tabType=", "/leak/")
        ):
            if full_url not in seen_seeds:
                seen_seeds.add(full_url)
                result.crawl_seed_urls.append(full_url)

        m_page = re.search(r"[?&]page=(\d+)", full_url)
        if m_page:
            pages.add(int(m_page.group(1)))

    # Detect MUI pagination buttons and total page indicators in HTML / Next.js state
    for p_num in re.findall(r'MuiPaginationItem-page[^>]*>(\d+)<', html_content):
        pages.add(int(p_num))
    for p_num in re.findall(r'"(?:totalPages|pageCount|numPages)"\s*:\s*(\d+)', html_content):
        val = int(p_num)
        if val > 0:
            pages.add(val)

    result.pagination_pages_found = sorted(pages)
    return result
