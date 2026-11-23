"""
Live WikIran Full-Archive Search + Structured Archives (Front Companies & Vessels) Sync.

Why this exists:
- wikiran.org hosts 500,000+ leaked emails, PDFs, images, and CSV rows across 28+ leak collections.
- Downloading half a million individual HTML pages via polite crawling takes days.
- This module solves both problems cleanly:
  1. `search_wikiran_live`: Queries https://wikiran.org/search?query=<Q>&tabType=all in real time,
     extracts the exact server hit count, per-leak facet breakdown, and matching result cards
     (emails, PDFs, images, Front Companies, Vessels, articles), and automatically saves every
     returned record into local SQLite (`wikiran_documents` + `fts_archive`) so it becomes
     permanently searchable offline.
  2. `sync_wikiran_structured_archives`: Concurrently and politely downloads ALL 561 Vessels
     (`/leak/vessels?page=1..N`) and ALL 2,007 Front Companies (`/leak/front-companies?page=1..N`)
     directly from WikIran's paginated cards into local SQLite + FTS5 in seconds.
"""

from __future__ import annotations

import html as html_lib
import json
import math
import re
import sqlite3
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

from ..database.repository import ArchiveRepository, utc_now_iso
from .normalizer import normalize_date, normalize_url

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

LEAK_COLLECTION_LABELS: dict[str, str] = {
    "front-companies": "Front Companies Archive",
    "vessels": "Vessels Archive",
    "hms": "HMS Trading FZE & Petro Delta Energy (PDECO)",
    "sej": "Sepehr Energy Jahan",
    "sej2": "Sepehr Energy Jahan – AFGS Oil Command",
    "irgc-oil": "IRGC Oil Command: Nosazan Kaveh & GDCP",
    "sepah": "Bank Sepah",
    "amin2025": "Amin Exchange 2025",
    "amin": "Amin Exchange House (Ebrahimi & Associates)",
    "pedram": "Pedram Pirouzan Exchange (Opal Exchange)",
    "tahayyori": "Tahayyori Exchange (Arz-Iran)",
    "berelian": "Berelian Exchange (Zarringhalam)",
    "radin": "Radin Exchange",
    "sadaf": "Sadaf Exchange",
    "tejarat": "Tejarat Bank & Exchange",
    "rahbar": "The Rahbar Records",
    "kpmc": "Khorasan Powder Metallurgy (KMPC/KHPMCO)",
    "caspian": "Caspian Airlines",
    "safiran": "Safiran Airport Services",
    "triliance": "Triliance Petrochemical Co. Ltd.",
    "sahara-thunder": "Sahara Thunder",
    "pgpicc": "PGPICC (Persian Gulf Petrochemical)",
    "pcc": "Petrochemical Commercial Company",
    "asb": "ASB Group",
    "steel-companies": "Iranian Steel Companies (MSC & KSC)",
    "pmo": "Ports and Maritime Organization",
    "moe": "Ministry of Energy",
    "mefa": "Ministry of Economic Affairs & Finance",
    "tpedc": "Tehran Province Electricity Distribution Co.",
    "sanction-imposed-entities": "Sanction-Imposed Entities",
}


def get_leak_label(slug: str) -> str:
    clean = (slug or "").strip().lower()
    if clean in LEAK_COLLECTION_LABELS:
        return LEAK_COLLECTION_LABELS[clean]
    return clean.replace("-", " ").title() if clean else "WikIran Archive"


def _strip_tags(raw: str) -> str:
    if not raw:
        return ""
    cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html_lib.unescape(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _http_get_text(url: str, timeout: float = 14.0) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _classify_doc_type(href: str, sources: list[str]) -> str:
    low_href = href.lower()
    low_sources = {s.lower() for s in sources}
    if "front-companies" in low_sources:
        return "FRONT_COMPANY"
    if "vessels" in low_sources:
        return "VESSEL"
    if "/document/emails/" in low_href:
        return "LEAKED_EMAIL"
    if "/document/files/" in low_href:
        return "LEAKED_FILE"
    if "/document/csv/" in low_href:
        return "LEAKED_CSV"
    if "/document/articles/" in low_href:
        return "ARTICLE"
    return "LEAKED_FILE"


def _parse_structured_csv_fields(
    doc_type: str, title: str, description: str
) -> tuple[str, str, str, str]:
    """
    Parse pipe-delimited Front Companies / Vessels description fields.
    Returns (country_or_flag, bank_or_operator, identifier_or_imo, clean_snippet).
    """
    parts = [p.strip() for p in description.split("|")]
    if doc_type == "FRONT_COMPANY" and len(parts) >= 3:
        # Format: Company Name | Jurisdiction/Country | Bank Name | Account/ID | Source Leak
        country = parts[1] if len(parts) > 1 else ""
        bank = parts[2] if len(parts) > 2 else ""
        identifier = parts[3] if len(parts) > 3 else ""
        origin_leak = parts[4] if len(parts) > 4 else ""
        summary_bits = [b for b in [
            f"Jurisdiction: {country}" if country else "",
            f"Bank: {bank}" if bank else "",
            f"Account/Ref: {identifier}" if identifier else "",
            f"Leak: {get_leak_label(origin_leak)}" if origin_leak else "",
        ] if b]
        return country, bank, identifier, " · ".join(summary_bits) or description

    if doc_type == "VESSEL" and len(parts) >= 5:
        # Format: Vessel Name | Alt Name | IMO | Owner/Operator | Flag | Vessel Type | ... | Sanctioned | Leak
        alt_name = parts[1] if len(parts) > 1 else ""
        imo = parts[2] if len(parts) > 2 else ""
        owner = parts[3] if len(parts) > 3 else ""
        flag = parts[4] if len(parts) > 4 else ""
        vtype = parts[5] if len(parts) > 5 else ""
        sanctioned = parts[7] if len(parts) > 7 else ""
        origin_leak = parts[8] if len(parts) > 8 else ""
        summary_bits = [b for b in [
            f"IMO: {imo}" if imo else "",
            f"Flag: {flag}" if flag else "",
            f"Type: {vtype}" if vtype else "",
            f"Operator: {owner}" if owner else "",
            f"Alt: {alt_name}" if alt_name else "",
            f"Sanctioned: {sanctioned}" if sanctioned else "",
            f"Leak: {get_leak_label(origin_leak)}" if origin_leak else "",
        ] if b]
        return flag, owner, imo, " · ".join(summary_bits) or description

    return "", "", "", description


def parse_search_cards_from_html(
    raw_html: str, base_url: str = "https://wikiran.org"
) -> list[dict[str, Any]]:
    """Parse all searchResultCard items from a WikIran search or /leak/<slug> page."""
    if not raw_html or "searchResultCard_searchResultWrapper" not in raw_html:
        return []

    chunks = raw_html.split("searchResultCard_searchResultWrapper")
    records: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for chunk in chunks[1:]:
        # Bound chunk to this card only
        card_html = chunk[:6000]
        m_href = re.search(r'href=["\'](/document/[^"\']+)["\']', card_html)
        if not m_href:
            continue

        rel_href = m_href.group(1).strip()
        full_url = normalize_url(rel_href, base_url)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # Build stable doc_id like "csv:0f8dc1ba..." or "emails:2299c00f..."
        path_parts = [p for p in urllib.parse.urlparse(full_url).path.split("/") if p]
        if len(path_parts) >= 3 and path_parts[0] == "document":
            doc_id = f"{path_parts[1]}:{path_parts[2]}"
        else:
            doc_id = rel_href.lstrip("/")

        # Extract date if present inside header
        m_date = re.search(
            r'searchResultCard_searchResultDate__[^>]*>(.*?)</span>', card_html, re.S
        )
        raw_date = _strip_tags(m_date.group(1)) if m_date else ""
        iso_date = normalize_date(raw_date, fallback="") if raw_date else ""

        # Extract header title (prefer uiResponsiveText inside h2 to skip SVG icons & file badges)
        m_h2 = re.search(r"<h2[^>]*>(.*?)</h2>", card_html, re.S | re.I)
        title = ""
        if m_h2:
            h2_inner = m_h2.group(1)
            # Remove the date span from h2 before reading title
            h2_no_date = re.sub(
                r'<span[^>]*searchResultCard_searchResultDate__[^>]*>.*?</span>',
                "",
                h2_inner,
                flags=re.S,
            )
            m_resp = re.search(
                r'uiResponsiveText_responsiveText__[^>]*>(.*?)</span>', h2_no_date, re.S
            )
            title = _strip_tags(m_resp.group(1)) if m_resp else _strip_tags(h2_no_date)
        if not title:
            title = doc_id

        # Extract description / snippet / CSV row
        m_desc = re.search(
            r'searchResultCard_searchDescription__[^>]*>(.*?)</div>', card_html, re.S
        )
        raw_desc = _strip_tags(m_desc.group(1)) if m_desc else ""
        # Truncate noisy tracking query strings inside email snippets
        if len(raw_desc) > 480:
            raw_desc = raw_desc[:477].rstrip() + "..."

        # Extract source leak chips
        raw_sources = re.findall(r'MuiChip-label[^>]*>(.*?)</span>', card_html, re.S)
        sources = [_strip_tags(s) for s in raw_sources if _strip_tags(s)]

        doc_type = _classify_doc_type(rel_href, sources)
        country_or_flag, bank_or_operator, identifier_or_imo, clean_snippet = (
            _parse_structured_csv_fields(doc_type, title, raw_desc)
        )

        # Keep full raw CSV row in snippet if Front Company/Vessel had extra columns
        records.append(
            {
                "doc_id": doc_id,
                "doc_type": doc_type,
                "title": title,
                "snippet": clean_snippet or raw_desc or title,
                "raw_description": raw_desc,
                "leak_sources": ", ".join(sources),
                "leak_source_labels": ", ".join(get_leak_label(s) for s in sources) if sources else "WikIran Archive",
                "country_or_flag": country_or_flag,
                "bank_or_operator": bank_or_operator,
                "identifier_or_imo": identifier_or_imo,
                "document_date": iso_date,
                "source_url": full_url,
            }
        )

    return records


def parse_search_summary_from_html(raw_html: str) -> dict[str, Any]:
    """
    Extract exact total result count and per-leak facet hit counts from WikIran HTML / RSC stream.
    """
    total_label = ""
    total_int = 0

    # Pattern 1: RSC payload [[10000,"+ results"]," ","for: ..."] or [[42," results"],...]
    m_rsc_cnt = re.search(
        r'page_resultsCount__[^"]*"[^}]*?"children":\[\[?(\d+),"(\+?\s*results)"\]',
        raw_html,
    )
    if m_rsc_cnt:
        total_int = int(m_rsc_cnt.group(1))
        total_label = f"{total_int}{m_rsc_cnt.group(2)}"
    else:
        # Pattern 2: Rendered HTML >2007 results< or >10000+ results<
        m_html_cnt = re.search(r">(\d+)(\+?\s+results)", raw_html, re.I)
        if m_html_cnt:
            total_int = int(m_html_cnt.group(1))
            total_label = f"{total_int}{m_html_cnt.group(2)}"

    # Extract RSC summary array: \"summary\":[{\"source\":\"hms\",\"amount\":2762},...]
    facets: list[dict[str, Any]] = []
    m_summary = re.search(r'\\?"summary\\?":(\[[^\]]+\])', raw_html)
    if m_summary:
        raw_arr = m_summary.group(1).replace('\\"', '"')
        try:
            parsed = json.loads(raw_arr)
            if isinstance(parsed, list):
                for item in parsed:
                    if not isinstance(item, dict):
                        continue
                    src = str(item.get("source") or "").strip()
                    amt = int(item.get("amount") or 0)
                    if src and amt > 0:
                        facets.append(
                            {
                                "source": src,
                                "label": get_leak_label(src),
                                "amount": amt,
                            }
                        )
                facets.sort(key=lambda x: x["amount"], reverse=True)
        except Exception:
            pass

    if not total_label and facets:
        approx = sum(f["amount"] for f in facets)
        total_int = approx
        total_label = f"{approx:,} results"

    return {
        "total_int": total_int,
        "total_label": total_label or "0 results",
        "facets": facets,
    }


def ensure_wikiran_documents_table(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS wikiran_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT NOT NULL UNIQUE,
            doc_type TEXT NOT NULL DEFAULT 'LEAKED_FILE',
            title TEXT NOT NULL,
            snippet TEXT NOT NULL DEFAULT '',
            leak_sources TEXT NOT NULL DEFAULT '',
            country_or_flag TEXT NOT NULL DEFAULT '',
            bank_or_operator TEXT NOT NULL DEFAULT '',
            identifier_or_imo TEXT NOT NULL DEFAULT '',
            document_date TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL UNIQUE,
            retrieved_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_wdoc_type ON wikiran_documents(doc_type);
        CREATE INDEX IF NOT EXISTS idx_wdoc_title ON wikiran_documents(title);
        CREATE INDEX IF NOT EXISTS idx_wdoc_sources ON wikiran_documents(leak_sources);
        """
    )


def upsert_wikiran_documents_batch(
    conn: sqlite3.Connection, records: list[dict[str, Any]]
) -> tuple[int, int]:
    """
    Upsert parsed WikIran document cards into `wikiran_documents` AND `fts_archive`.
    Returns (newly_inserted_count, total_upserted_count).
    """
    if not records:
        return 0, 0

    ensure_wikiran_documents_table(conn)
    now = utc_now_iso()
    newly_inserted = 0
    total_upserted = 0

    for rec in records:
        doc_id = str(rec.get("doc_id") or "").strip()
        source_url = str(rec.get("source_url") or "").strip()
        title = str(rec.get("title") or "").strip()
        if not doc_id or not source_url or not title:
            continue

        doc_type = str(rec.get("doc_type") or "LEAKED_FILE")
        snippet = str(rec.get("snippet") or "")
        raw_desc = str(rec.get("raw_description") or snippet)
        leak_sources = str(rec.get("leak_sources") or "")
        leak_labels = str(rec.get("leak_source_labels") or get_leak_label(leak_sources))
        country_or_flag = str(rec.get("country_or_flag") or "")
        bank_or_operator = str(rec.get("bank_or_operator") or "")
        identifier_or_imo = str(rec.get("identifier_or_imo") or "")
        document_date = str(rec.get("document_date") or "")

        existing = conn.execute(
            "SELECT id, title, snippet, leak_sources FROM wikiran_documents WHERE doc_id = ? OR source_url = ?;",
            (doc_id, source_url),
        ).fetchone()

        needs_fts_insert = True
        if existing:
            row_id = int(existing[0])
            unchanged = (
                str(existing[1] or "") == title
                and str(existing[2] or "") == snippet
                and str(existing[3] or "") == leak_sources
            )
            if unchanged:
                needs_fts_insert = False
                total_upserted += 1
                continue
            conn.execute(
                """
                UPDATE wikiran_documents
                SET doc_type = ?, title = ?, snippet = ?, leak_sources = ?,
                    country_or_flag = ?, bank_or_operator = ?, identifier_or_imo = ?,
                    document_date = ?, retrieved_at = ?
                WHERE id = ?;
                """,
                (
                    doc_type,
                    title,
                    snippet,
                    leak_sources,
                    country_or_flag,
                    bank_or_operator,
                    identifier_or_imo,
                    document_date,
                    now,
                    row_id,
                ),
            )
            # Only delete old FTS5 entry when an existing record actually changed
            conn.execute(
                "DELETE FROM fts_archive WHERE record_type = 'WIKIRAN_DOC' AND record_id = ?;",
                (str(row_id),),
            )
        else:
            cur = conn.execute(
                """
                INSERT INTO wikiran_documents (
                    doc_id, doc_type, title, snippet, leak_sources,
                    country_or_flag, bank_or_operator, identifier_or_imo,
                    document_date, source_url, retrieved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    doc_id,
                    doc_type,
                    title,
                    snippet,
                    leak_sources,
                    country_or_flag,
                    bank_or_operator,
                    identifier_or_imo,
                    document_date,
                    source_url,
                    now,
                ),
            )
            row_id = int(cur.lastrowid)
            newly_inserted += 1

        if needs_fts_insert:
            full_body = " | ".join(
                b for b in [title, snippet, raw_desc, country_or_flag, bank_or_operator, identifier_or_imo, leak_labels] if b
            )
            conn.execute(
                """
                INSERT INTO fts_archive (
                    record_type, record_id, title, editorial_content, summary,
                    organization_names, entity_names, category_names, tag_names,
                    publication_date, source_url
                ) VALUES ('WIKIRAN_DOC', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    str(row_id),
                    title,
                    full_body,
                    snippet,
                    " ".join(b for b in [bank_or_operator, country_or_flag] if b),
                    identifier_or_imo,
                    f"WikIran {doc_type.replace('_', ' ').title()} {leak_labels}",
                    f"{doc_type} {leak_sources}",
                    document_date or now[:10],
                    source_url,
                ),
            )
        total_upserted += 1

    conn.commit()
    return newly_inserted, total_upserted


def _doc_type_display(doc_type: str) -> tuple[str, str]:
    mapping = {
        "FRONT_COMPANY": ("WikIran Front Company", "شرکت پوششی ویکی‌ایران"),
        "VESSEL": ("WikIran Vessel Archive", "آرشیو کشتی‌های ویکی‌ایران"),
        "LEAKED_EMAIL": ("WikIran Leaked Email", "ایمیل افشاشده ویکی‌ایران"),
        "LEAKED_FILE": ("WikIran Leaked Document", "سند افشاشده ویکی‌ایران"),
        "LEAKED_CSV": ("WikIran CSV Record", "رکورد CSV ویکی‌ایران"),
        "ARTICLE": ("WikIran Investigation", "مقاله تحقیقی ویکی‌ایران"),
    }
    return mapping.get(doc_type, ("WikIran Archive Document", "سند آرشیو ویکی‌ایران"))


def search_wikiran_live(
    repo: ArchiveRepository,
    query: str,
    *,
    max_pages: int = 2,
    tab_type: str = "all",
    leak_source: str | None = None,
    auto_cache: bool = True,
) -> dict[str, Any]:
    """
    Live-query wikiran.org/search across ALL 500,000+ leaked documents, emails, PDFs,
    Front Companies, Vessels, and articles. Auto-saves every returned hit into local SQLite + FTS5.
    """
    q = (query or "").strip()
    if not q:
        return {
            "online": True,
            "query": "",
            "total_label": "",
            "total_int": 0,
            "facets": [],
            "results": [],
            "cached_new_count": 0,
            "search_url": "https://wikiran.org/search",
        }

    settings = repo.get_settings()
    base_url = settings.get("source_base_url", "https://wikiran.org").rstrip("/")

    params: list[tuple[str, str]] = [("query", q), ("tabType", tab_type or "all")]
    if leak_source:
        params.append(("leaksSources[0]", leak_source))
    base_search_url = f"{base_url}/search?{urllib.parse.urlencode(params)}"

    all_cards: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    summary_meta: dict[str, Any] = {"total_int": 0, "total_label": "0 results", "facets": []}

    try:
        for page in range(1, max(1, min(max_pages, 5)) + 1):
            page_url = base_search_url if page == 1 else f"{base_search_url}&page={page}"
            raw_html = _http_get_text(page_url, timeout=12.0)
            if page == 1:
                summary_meta = parse_search_summary_from_html(raw_html)
            cards = parse_search_cards_from_html(raw_html, base_url=base_url)
            new_on_page = 0
            for c in cards:
                if c["source_url"] not in seen_urls:
                    seen_urls.add(c["source_url"])
                    all_cards.append(c)
                    new_on_page += 1
            if len(cards) < 10 or new_on_page == 0:
                break
    except Exception as exc:
        return {
            "online": False,
            "error": str(exc),
            "query": q,
            "total_label": "Offline",
            "total_int": 0,
            "facets": [],
            "results": [],
            "cached_new_count": 0,
            "search_url": base_search_url,
        }

    cached_new = 0
    if auto_cache and all_cards:
        try:
            cached_new, _ = upsert_wikiran_documents_batch(repo.conn, all_cards)
        except Exception:
            cached_new = 0

    now = utc_now_iso()
    formatted_results: list[dict[str, Any]] = []
    for idx, c in enumerate(all_cards, start=1):
        cat_en, cat_fa = _doc_type_display(c["doc_type"])
        leak_lbl = c["leak_source_labels"] or "WikIran Archive"
        formatted_results.append(
            {
                "record_type": "WIKIRAN_LIVE",
                "wikiran_doc_type": c["doc_type"],
                "id": -idx,
                "title": c["title"],
                "native_title": c["identifier_or_imo"] or "",
                "short_description": c["snippet"],
                "editorial_content": (
                    f"Source Leak: {leak_lbl}\n"
                    f"Document Type: {cat_en}\n"
                    + (f"Jurisdiction / Flag: {c['country_or_flag']}\n" if c["country_or_flag"] else "")
                    + (f"Bank / Operator: {c['bank_or_operator']}\n" if c["bank_or_operator"] else "")
                    + (f"Account / IMO / Ref: {c['identifier_or_imo']}\n" if c["identifier_or_imo"] else "")
                    + f"\nMatched Content:\n{c['raw_description'] or c['snippet']}"
                ),
                "publication_date": c["document_date"] or "",
                "category_en": f"{cat_en} ({leak_lbl})",
                "category_fa": f"{cat_fa} ({leak_lbl})",
                "organizations": " · ".join(
                    b for b in [c["bank_or_operator"], c["country_or_flag"]] if b
                ),
                "tags": c["leak_sources"] or c["doc_type"],
                "source_name": f"WikIran Live — {leak_lbl}",
                "source_url": c["source_url"],
                "extraction_status": "WIKIRAN_LIVE_CACHED" if auto_cache else "WIKIRAN_LIVE",
                "retrieved_at": now,
                "record_version": 1,
                "ofac_ent_num": None,
                "ofac_list_source": "",
                "ofac_sdn_type": "",
                "ofac_programs": "",
                "ofac_aliases": "",
                "ofac_addresses": "",
                "ofac_countries": c["country_or_flag"],
                "os_id": "",
                "os_schema": "",
                "os_datasets": "",
                "os_identifiers": c["identifier_or_imo"],
            }
        )

    return {
        "online": True,
        "query": q,
        "total_label": summary_meta["total_label"],
        "total_int": summary_meta["total_int"],
        "facets": summary_meta["facets"],
        "fetched_count": len(formatted_results),
        "cached_new_count": cached_new,
        "results": formatted_results,
        "search_url": base_search_url,
    }


def _is_stop_signaled(conn: sqlite3.Connection) -> bool:
    try:
        row = conn.execute(
            "SELECT value FROM application_settings WHERE key = 'stop_crawl_requested';"
        ).fetchone()
        return bool(row and str(row[0]).lower() == "true")
    except Exception:
        return False


def sync_wikiran_structured_archives(
    repo: ArchiveRepository,
    *,
    target: str = "both",
    max_workers: int = 6,
) -> dict[str, Any]:
    """
    Download ALL structured records from WikIran's Front Companies Archive (2,007 rows)
    and/or Vessels Archive (561 rows) directly into local SQLite + FTS5.
    target: 'both' | 'front-companies' | 'vessels'
    """
    ensure_wikiran_documents_table(repo.conn)
    repo.set_setting("stop_crawl_requested", "false")
    settings = repo.get_settings()
    base_url = settings.get("source_base_url", "https://wikiran.org").rstrip("/")

    targets: list[str] = []
    t_low = (target or "both").strip().lower()
    if t_low in ("both", "all"):
        targets = ["vessels", "front-companies"]
    elif t_low in ("vessels", "front-companies"):
        targets = [t_low]
    else:
        targets = ["vessels", "front-companies"]

    now = utc_now_iso()
    job_uuid = str(uuid.uuid4())
    cur = repo.conn.execute(
        """
        INSERT INTO collection_jobs (
            job_uuid, job_type, status, started_at, checkpoint_data
        ) VALUES (?, 'WIKIRAN_STRUCTURED_SYNC', 'RUNNING', ?, ?);
        """,
        (job_uuid, now, json.dumps({"targets": targets})),
    )
    job_id = int(cur.lastrowid)
    repo.conn.commit()

    total_pages_fetched = 0
    total_records_upserted = 0
    total_new_records = 0
    per_target_stats: dict[str, dict[str, Any]] = {}
    stopped_by_user = False

    try:
        for slug in targets:
            if _is_stop_signaled(repo.conn):
                stopped_by_user = True
                break

            page1_url = f"{base_url}/search?tabType=documents&leaksSources%5B0%5D={urllib.parse.quote(slug)}&page=1"
            p1_html = _http_get_text(page1_url, timeout=18.0)
            p1_meta = parse_search_summary_from_html(p1_html)
            p1_cards = parse_search_cards_from_html(p1_html, base_url=base_url)

            # Force correct doc_type for this structured archive
            forced_type = "VESSEL" if slug == "vessels" else "FRONT_COMPANY"
            for c in p1_cards:
                c["doc_type"] = forced_type
                if not c["leak_sources"]:
                    c["leak_sources"] = slug
                    c["leak_source_labels"] = get_leak_label(slug)

            n_new, n_ups = upsert_wikiran_documents_batch(repo.conn, p1_cards)
            total_new_records += n_new
            total_records_upserted += n_ups
            total_pages_fetched += 1

            # Read exact count for THIS leak slug from facets (fallback to leak page header)
            facet_match = next(
                (int(f["amount"]) for f in p1_meta.get("facets", []) if str(f.get("source", "")).lower() == slug.lower()),
                0,
            )
            if facet_match <= 0:
                try:
                    leak_hdr_html = _http_get_text(f"{base_url}/leak/{slug}", timeout=12.0)
                    leak_hdr_meta = parse_search_summary_from_html(leak_hdr_html)
                    facet_match = int(leak_hdr_meta.get("total_int", 0))
                except Exception:
                    facet_match = 0

            expected_total = max(facet_match, len(p1_cards))
            total_pages = min(300, max(1, math.ceil(expected_total / 10)))
            slug_new = n_new
            slug_upserted = n_ups
            slug_pages = 1
            slug_failed = 0

            repo.conn.execute(
                """
                UPDATE collection_jobs
                SET total_discovered = total_discovered + ?, processed_count = ?, new_records_count = ?
                WHERE id = ?;
                """,
                (expected_total, total_records_upserted, total_new_records, job_id),
            )
            repo.conn.commit()

            # Fetch remaining pages in polite concurrent batches
            remaining_pages = list(range(2, total_pages + 1))
            batch_size = max(max_workers * 4, 24)

            for start_i in range(0, len(remaining_pages), batch_size):
                if _is_stop_signaled(repo.conn):
                    stopped_by_user = True
                    break
                batch_pages = remaining_pages[start_i : start_i + batch_size]
                batch_cards: list[dict[str, Any]] = []

                def _fetch_one(p_num: int) -> tuple[int, list[dict[str, Any]]]:
                    u = f"{base_url}/search?tabType=documents&leaksSources%5B0%5D={urllib.parse.quote(slug)}&page={p_num}"
                    h = _http_get_text(u, timeout=18.0)
                    parsed = parse_search_cards_from_html(h, base_url=base_url)
                    for item in parsed:
                        item["doc_type"] = forced_type
                        if not item["leak_sources"]:
                            item["leak_sources"] = slug
                            item["leak_source_labels"] = get_leak_label(slug)
                    return p_num, parsed

                with ThreadPoolExecutor(max_workers=max_workers) as pool:
                    futures = [pool.submit(_fetch_one, pn) for pn in batch_pages]
                    for fut in as_completed(futures):
                        try:
                            _pn, parsed_cards = fut.result()
                            batch_cards.extend(parsed_cards)
                            slug_pages += 1
                            total_pages_fetched += 1
                        except Exception:
                            slug_failed += 1

                if batch_cards:
                    b_new, b_ups = upsert_wikiran_documents_batch(repo.conn, batch_cards)
                    slug_new += b_new
                    slug_upserted += b_ups
                    total_new_records += b_new
                    total_records_upserted += b_ups

                    repo.conn.execute(
                        """
                        UPDATE collection_jobs
                        SET processed_count = ?, new_records_count = ?, failed_count = failed_count + ?
                        WHERE id = ?;
                        """,
                        (total_records_upserted, total_new_records, slug_failed, job_id),
                    )
                    repo.conn.commit()

            per_target_stats[slug] = {
                "expected_total": expected_total,
                "pages_fetched": slug_pages,
                "total_pages": total_pages,
                "upserted": slug_upserted,
                "newly_added": slug_new,
                "failed_pages": slug_failed,
            }

            repo.conn.execute(
                """
                INSERT INTO collection_history (
                    job_id, target_url, record_type, http_status, action_taken, timestamp, message
                ) VALUES (?, ?, 'WIKIRAN_DOC', 200, 'INSERTED', ?, ?);
                """,
                (
                    job_id,
                    f"{base_url}/leak/{slug}",
                    utc_now_iso(),
                    f"Synced {slug_upserted:,} {get_leak_label(slug)} records across {slug_pages}/{total_pages} pages ({slug_new:,} new).",
                ),
            )
            repo.conn.commit()

        repo.set_setting("wikiran_structured_last_sync", utc_now_iso())
        final_status = "INTERRUPTED" if stopped_by_user else "COMPLETED"
        err_msg = "Stopped by user before completing all pages." if stopped_by_user else None
        repo.conn.execute(
            """
            UPDATE collection_jobs
            SET status = ?, finished_at = ?, processed_count = ?, new_records_count = ?, error_summary = ?
            WHERE id = ?;
            """,
            (final_status, utc_now_iso(), total_records_upserted, total_new_records, err_msg, job_id),
        )
        repo.conn.commit()

        return {
            "ok": True,
            "status": final_status,
            "pages_fetched": total_pages_fetched,
            "records_upserted": total_records_upserted,
            "newly_added": total_new_records,
            "targets": per_target_stats,
            "summary": get_wikiran_documents_summary(repo.conn, repo.get_settings()),
        }
    except Exception as exc:
        repo.conn.execute(
            """
            UPDATE collection_jobs
            SET status = 'FAILED', finished_at = ?, error_summary = ?
            WHERE id = ?;
            """,
            (utc_now_iso(), f"WikIran structured archive sync failed: {exc}", job_id),
        )
        repo.conn.commit()
        return {
            "ok": False,
            "error": str(exc),
            "summary": get_wikiran_documents_summary(repo.conn, repo.get_settings()),
        }


def get_wikiran_documents_summary(
    conn: sqlite3.Connection, settings: dict[str, str] | None = None
) -> dict[str, Any]:
    """Return offline counts of WikIran structured & cached leak documents."""
    ensure_wikiran_documents_table(conn)
    rows = conn.execute(
        "SELECT doc_type, COUNT(*) FROM wikiran_documents GROUP BY doc_type;"
    ).fetchall()
    counts = {str(r[0]): int(r[1]) for r in rows}
    total = sum(counts.values())
    last_sync = (settings or {}).get("wikiran_structured_last_sync", "")
    return {
        "total": total,
        "front_companies": counts.get("FRONT_COMPANY", 0),
        "vessels": counts.get("VESSEL", 0),
        "leaked_emails": counts.get("LEAKED_EMAIL", 0),
        "leaked_files": counts.get("LEAKED_FILE", 0) + counts.get("LEAKED_CSV", 0),
        "other_docs": counts.get("ARTICLE", 0),
        "last_sync_at": last_sync,
    }


LEAK_COLLECTION_META: list[dict[str, Any]] = [
    {"slug": "front-companies", "category": "Structured Archive", "default_remote": 2007},
    {"slug": "vessels", "category": "Structured Archive", "default_remote": 561},
    {"slug": "sepah", "category": "Banking & Exchange", "default_remote": 10000},
    {"slug": "amin2025", "category": "Banking & Exchange", "default_remote": 10000},
    {"slug": "amin", "category": "Banking & Exchange", "default_remote": 10000},
    {"slug": "radin", "category": "Banking & Exchange", "default_remote": 10000},
    {"slug": "tahayyori", "category": "Banking & Exchange", "default_remote": 4023},
    {"slug": "pedram", "category": "Banking & Exchange", "default_remote": 3969},
    {"slug": "berelian", "category": "Banking & Exchange", "default_remote": 1352},
    {"slug": "tejarat", "category": "Banking & Exchange", "default_remote": 348},
    {"slug": "rahbar", "category": "Banking & Exchange", "default_remote": 48},
    {"slug": "sadaf", "category": "Banking & Exchange", "default_remote": 0},
    {"slug": "pcc", "category": "Energy & Oil", "default_remote": 10000},
    {"slug": "pgpicc", "category": "Energy & Oil", "default_remote": 10000},
    {"slug": "hms", "category": "Energy & Oil", "default_remote": 10000},
    {"slug": "sej", "category": "Energy & Oil", "default_remote": 10000},
    {"slug": "sej2", "category": "Energy & Oil", "default_remote": 10000},
    {"slug": "triliance", "category": "Energy & Oil", "default_remote": 10000},
    {"slug": "irgc-oil", "category": "Energy & Oil", "default_remote": 4121},
    {"slug": "sahara-thunder", "category": "Shipping & Aviation", "default_remote": 10000},
    {"slug": "pmo", "category": "Shipping & Aviation", "default_remote": 10000},
    {"slug": "safiran", "category": "Shipping & Aviation", "default_remote": 10000},
    {"slug": "caspian", "category": "Shipping & Aviation", "default_remote": 1121},
    {"slug": "steel-companies", "category": "Industrial & Government", "default_remote": 10000},
    {"slug": "asb", "category": "Industrial & Government", "default_remote": 10000},
    {"slug": "moe", "category": "Industrial & Government", "default_remote": 10000},
    {"slug": "mefa", "category": "Industrial & Government", "default_remote": 10000},
    {"slug": "kpmc", "category": "Industrial & Government", "default_remote": 2620},
    {"slug": "tpedc", "category": "Industrial & Government", "default_remote": 1129},
    {"slug": "sanction-imposed-entities", "category": "Structured Archive", "default_remote": 0},
]


def get_leak_collections_catalog(
    repo: ArchiveRepository, *, refresh_remote: bool = False
) -> dict[str, Any]:
    """
    Return all 30 WikIran leak collections with their real offline counts in SQLite,
    saved checkpoint pages, and remote WikIran document counts.
    """
    ensure_wikiran_documents_table(repo.conn)
    settings = repo.get_settings()
    base_url = settings.get("source_base_url", "https://wikiran.org").rstrip("/")

    # Optionally refresh live facet counts from wikiran.org/search?tabType=documents
    remote_map: dict[str, int] = {}
    cached_remote_raw = settings.get("wikiran_leak_remote_counts_json", "")
    if cached_remote_raw:
        try:
            parsed_cache = json.loads(cached_remote_raw)
            if isinstance(parsed_cache, dict):
                remote_map = {str(k).lower(): int(v) for k, v in parsed_cache.items()}
        except Exception:
            pass

    refreshed_online = False
    if refresh_remote:
        try:
            html_body = _http_get_text(f"{base_url}/search?tabType=documents", timeout=14.0)
            meta = parse_search_summary_from_html(html_body)
            for f in meta.get("facets", []):
                src = str(f.get("source") or "").strip().lower()
                if src:
                    remote_map[src] = int(f.get("amount") or 0)
            if remote_map:
                repo.set_setting("wikiran_leak_remote_counts_json", json.dumps(remote_map))
                repo.set_setting("wikiran_leak_remote_refreshed_at", utc_now_iso())
                refreshed_online = True
        except Exception:
            refreshed_online = False

    # Count offline wikiran_documents per leak slug
    offline_counts: dict[str, int] = {}
    for row in repo.conn.execute("SELECT leak_sources FROM wikiran_documents;").fetchall():
        raw_s = str(row[0] or "")
        for token in raw_s.split(","):
            slug_tok = token.strip().lower()
            if slug_tok:
                offline_counts[slug_tok] = offline_counts.get(slug_tok, 0) + 1

    known_slugs: set[str] = set()
    collections: list[dict[str, Any]] = []
    for item in LEAK_COLLECTION_META:
        slug = item["slug"]
        known_slugs.add(slug)
        remote_amt = remote_map.get(slug, int(item["default_remote"]))
        off_cnt = offline_counts.get(slug, 0)
        ckpt_page = int(settings.get(f"leak_checkpoint_page_{slug}", "0") or 0)
        last_sync = settings.get(f"leak_checkpoint_time_{slug}", "")
        collections.append(
            {
                "slug": slug,
                "label": get_leak_label(slug),
                "category": item["category"],
                "remote_count": remote_amt,
                "remote_count_label": "10,000+" if remote_amt >= 10000 else f"{remote_amt:,}",
                "offline_count": off_cnt,
                "last_page_synced": ckpt_page,
                "last_synced_at": last_sync,
                "source_url": f"{base_url}/leak/{slug}",
            }
        )

    # Include any newly discovered remote slugs not yet in LEAK_COLLECTION_META
    for extra_slug, extra_amt in remote_map.items():
        if extra_slug not in known_slugs:
            off_cnt = offline_counts.get(extra_slug, 0)
            ckpt_page = int(settings.get(f"leak_checkpoint_page_{extra_slug}", "0") or 0)
            collections.append(
                {
                    "slug": extra_slug,
                    "label": get_leak_label(extra_slug),
                    "category": "Other Leaks",
                    "remote_count": extra_amt,
                    "remote_count_label": "10,000+" if extra_amt >= 10000 else f"{extra_amt:,}",
                    "offline_count": off_cnt,
                    "last_page_synced": ckpt_page,
                    "last_synced_at": settings.get(f"leak_checkpoint_time_{extra_slug}", ""),
                    "source_url": f"{base_url}/leak/{extra_slug}",
                }
            )

    return {
        "ok": True,
        "refreshed_online": refreshed_online,
        "last_refreshed_at": settings.get("wikiran_leak_remote_refreshed_at", ""),
        "total_offline_docs": sum(offline_counts.values()),
        "collections": collections,
    }


def download_targeted_leaks(
    repo: ArchiveRepository,
    slugs: list[str],
    *,
    max_pages_per_leak: int = 10,
    keyword: str = "",
    start_from_page_1: bool = False,
    max_workers: int = 4,
) -> dict[str, Any]:
    """
    Politely download documents from one or more user-selected WikIran leak collections
    into local SQLite + FTS5 with per-leak page checkpoints and live Stop/Progress support.
    """
    ensure_wikiran_documents_table(repo.conn)
    clean_slugs = [str(s).strip().lower() for s in slugs if str(s).strip()]
    if not clean_slugs:
        return {"ok": False, "error": "Please select at least one leak collection to download."}

    max_pages = max(1, min(int(max_pages_per_leak or 10), 250))
    kw = (keyword or "").strip()
    repo.set_setting("stop_crawl_requested", "false")
    settings = repo.get_settings()
    base_url = settings.get("source_base_url", "https://wikiran.org").rstrip("/")

    now = utc_now_iso()
    job_uuid = str(uuid.uuid4())
    cur = repo.conn.execute(
        """
        INSERT INTO collection_jobs (
            job_uuid, job_type, status, started_at, total_discovered, checkpoint_data
        ) VALUES (?, 'TARGETED_LEAK_DOWNLOAD', 'RUNNING', ?, ?, ?);
        """,
        (
            job_uuid,
            now,
            len(clean_slugs) * max_pages * 10,
            json.dumps({"slugs": clean_slugs, "max_pages": max_pages, "keyword": kw}),
        ),
    )
    job_id = int(cur.lastrowid)
    repo.conn.commit()

    total_pages_fetched = 0
    total_records_upserted = 0
    total_new_records = 0
    per_leak_stats: dict[str, dict[str, Any]] = {}
    stopped_by_user = False

    try:
        for slug in clean_slugs:
            if _is_stop_signaled(repo.conn):
                stopped_by_user = True
                break

            prev_ckpt = int(repo.get_settings().get(f"leak_checkpoint_page_{slug}", "0") or 0)
            start_page = 1 if (start_from_page_1 or kw) else max(1, prev_ckpt + 1)
            end_page = start_page + max_pages - 1

            slug_pages = 0
            slug_new = 0
            slug_upserted = 0
            slug_failed = 0
            highest_page_reached = prev_ckpt
            reached_end = False

            forced_type = (
                "VESSEL"
                if slug == "vessels"
                else ("FRONT_COMPANY" if slug == "front-companies" else None)
            )

            def _build_page_url(p_num: int) -> str:
                params: list[tuple[str, str]] = [
                    ("tabType", "documents"),
                    ("leaksSources[0]", slug),
                    ("page", str(p_num)),
                ]
                if kw:
                    params.append(("query", kw))
                return f"{base_url}/search?{urllib.parse.urlencode(params)}"

            page_numbers = list(range(start_page, end_page + 1))
            batch_size = max(max_workers * 3, 12)

            for i in range(0, len(page_numbers), batch_size):
                if _is_stop_signaled(repo.conn):
                    stopped_by_user = True
                    break

                chunk_pages = page_numbers[i : i + batch_size]
                batch_cards: list[dict[str, Any]] = []
                empty_pages_in_batch = 0

                def _fetch_page(pn: int) -> tuple[int, list[dict[str, Any]]]:
                    raw_h = _http_get_text(_build_page_url(pn), timeout=18.0)
                    cards = parse_search_cards_from_html(raw_h, base_url=base_url)
                    for c in cards:
                        if forced_type:
                            c["doc_type"] = forced_type
                        existing_src = [s.strip().lower() for s in str(c.get("leak_sources") or "").split(",") if s.strip()]
                        if slug not in existing_src:
                            existing_src.append(slug)
                            c["leak_sources"] = ", ".join(existing_src)
                            c["leak_source_labels"] = ", ".join(get_leak_label(s) for s in existing_src)
                    return pn, cards

                with ThreadPoolExecutor(max_workers=max_workers) as pool:
                    futures = [pool.submit(_fetch_page, pn) for pn in chunk_pages]
                    for fut in as_completed(futures):
                        try:
                            pn, parsed_cards = fut.result()
                            slug_pages += 1
                            total_pages_fetched += 1
                            if parsed_cards:
                                batch_cards.extend(parsed_cards)
                                if pn > highest_page_reached:
                                    highest_page_reached = pn
                            else:
                                empty_pages_in_batch += 1
                        except Exception:
                            slug_failed += 1

                if batch_cards:
                    b_new, b_ups = upsert_wikiran_documents_batch(repo.conn, batch_cards)
                    slug_new += b_new
                    slug_upserted += b_ups
                    total_new_records += b_new
                    total_records_upserted += b_ups

                if not kw and highest_page_reached > prev_ckpt:
                    repo.set_setting(f"leak_checkpoint_page_{slug}", str(highest_page_reached))
                    repo.set_setting(f"leak_checkpoint_time_{slug}", utc_now_iso())

                repo.conn.execute(
                    """
                    UPDATE collection_jobs
                    SET processed_count = ?, new_records_count = ?, failed_count = failed_count + ?
                    WHERE id = ?;
                    """,
                    (total_records_upserted, total_new_records, slug_failed, job_id),
                )
                repo.conn.commit()

                # Stop early if all pages in this chunk came back empty (end of leak archive)
                if empty_pages_in_batch == len(chunk_pages):
                    reached_end = True
                    break

            per_leak_stats[slug] = {
                "label": get_leak_label(slug),
                "start_page": start_page,
                "highest_page_reached": highest_page_reached,
                "pages_fetched": slug_pages,
                "upserted": slug_upserted,
                "newly_added": slug_new,
                "failed_pages": slug_failed,
                "reached_end": reached_end,
            }

            repo.conn.execute(
                """
                INSERT INTO collection_history (
                    job_id, target_url, record_type, http_status, action_taken, timestamp, message
                ) VALUES (?, ?, 'WIKIRAN_DOC', 200, 'INSERTED', ?, ?);
                """,
                (
                    job_id,
                    f"{base_url}/leak/{slug}",
                    utc_now_iso(),
                    (
                        f"Targeted leak '{get_leak_label(slug)}': downloaded {slug_upserted:,} docs "
                        f"({slug_new:,} new) across {slug_pages} pages"
                        + (f" matching '{kw}'" if kw else f" (checkpoint page {highest_page_reached})")
                    ),
                ),
            )
            repo.conn.commit()

        final_status = "INTERRUPTED" if stopped_by_user else "COMPLETED"
        err_msg = "Stopped by user (progress saved to checkpoints)." if stopped_by_user else None
        repo.conn.execute(
            """
            UPDATE collection_jobs
            SET status = ?, finished_at = ?, processed_count = ?, new_records_count = ?, error_summary = ?
            WHERE id = ?;
            """,
            (final_status, utc_now_iso(), total_records_upserted, total_new_records, err_msg, job_id),
        )
        repo.conn.commit()

        return {
            "ok": True,
            "status": final_status,
            "pages_fetched": total_pages_fetched,
            "records_upserted": total_records_upserted,
            "newly_added": total_new_records,
            "keyword": kw,
            "per_leak": per_leak_stats,
            "catalog": get_leak_collections_catalog(repo, refresh_remote=False),
            "summary": get_wikiran_documents_summary(repo.conn, repo.get_settings()),
        }
    except Exception as exc:
        repo.conn.execute(
            """
            UPDATE collection_jobs
            SET status = 'FAILED', finished_at = ?, error_summary = ?
            WHERE id = ?;
            """,
            (utc_now_iso(), f"Targeted leak download failed: {exc}", job_id),
        )
        repo.conn.commit()
        return {
            "ok": False,
            "error": str(exc),
            "catalog": get_leak_collections_catalog(repo, refresh_remote=False),
        }

