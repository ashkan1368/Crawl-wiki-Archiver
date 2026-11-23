"""
Real-time Live Sanctions Search against official public portals (zero API key required,
pure Python standard library):
1. U.S. Treasury OFAC Sanctions List Search (`https://sanctionssearch.ofac.treas.gov/`)
2. OpenSanctions Global Sanctions & Watchlists (`https://www.opensanctions.org/search/`)
"""

from __future__ import annotations

import html as html_lib
import http.cookiejar
import re
import urllib.parse
import urllib.request
from typing import Any

from ..database.repository import utc_now_iso
from ..search.fts_search import matches_exact_word_or_phrase, parse_exact_query

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

OFAC_SEARCH_URL = "https://sanctionssearch.ofac.treas.gov/"
OPENSANCTIONS_SEARCH_BASE = "https://www.opensanctions.org/search/"


def _strip_tags(raw: str) -> str:
    if not raw:
        return ""
    cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html_lib.unescape(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def search_ofac_live(
    query: str,
    *,
    exact_match: bool = False,
    max_results: int = 40,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """
    Perform a live real-time search directly against the official U.S. Treasury OFAC
    Sanctions List Search web service (`https://sanctionssearch.ofac.treas.gov/`).
    """
    clean_q, effective_exact = parse_exact_query(query, exact_match)
    if not clean_q:
        return {
            "online": True,
            "query": "",
            "exact_match": effective_exact,
            "total_int": 0,
            "total_label": "0 results",
            "fetched_count": 0,
            "results": [],
            "search_url": OFAC_SEARCH_URL,
        }

    try:
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        opener.addheaders = [
            ("User-Agent", USER_AGENT),
            ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
            ("Accept-Language", "en-US,en;q=0.9"),
        ]

        # Step 1: Fetch session cookies & ASP.NET form state
        init_html = opener.open(OFAC_SEARCH_URL, timeout=timeout).read().decode("utf-8", errors="replace")
        form_fields: dict[str, str] = {}
        for m in re.finditer(r"<input\b([^>]+)>", init_html, flags=re.I):
            attrs = m.group(1)
            nm = re.search(r'name=["\']([^"\']+)["\']', attrs, flags=re.I)
            if not nm:
                continue
            name = nm.group(1)
            tp = re.search(r'type=["\']([^"\']+)["\']', attrs, flags=re.I)
            vl = re.search(r'value=["\']([^"\']*)["\']', attrs, flags=re.I)
            ftype = (tp.group(1) if tp else "text").lower()
            if ftype in ("hidden", "text", "submit") or "txt" in name.lower():
                form_fields[name] = html_lib.unescape(vl.group(1)) if vl else ""

        post_data = {
            k: v
            for k, v in form_fields.items()
            if "btnReset" not in k and "btnDownload" not in k
        }
        min_score = "100" if effective_exact else "85"
        for k in list(post_data.keys()):
            if "txtLastName" in k:
                post_data[k] = clean_q
            elif "Slider1_Boundcontrol" in k or k.endswith("$Slider1"):
                post_data[k] = min_score

        encoded = urllib.parse.urlencode(post_data).encode("utf-8")
        post_req = urllib.request.Request(
            OFAC_SEARCH_URL,
            data=encoded,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": OFAC_SEARCH_URL,
                "Origin": "https://sanctionssearch.ofac.treas.gov",
            },
        )
        res_html = opener.open(post_req, timeout=timeout).read().decode("utf-8", errors="replace")

        now = utc_now_iso()
        formatted: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        m_tbl = re.search(
            r'<table[^>]*id=["\'][^"\']*gvSearchResults[^"\']*["\'][^>]*>(.*?)</table>',
            res_html,
            flags=re.S | re.I,
        )
        if m_tbl:
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", m_tbl.group(1), flags=re.S | re.I)
            for idx, r_html in enumerate(rows, start=1):
                cells = [
                    _strip_tags(td)
                    for td in re.findall(r"<td[^>]*>(.*?)</td>", r_html, flags=re.S | re.I)
                ]
                if len(cells) < 5:
                    continue
                name = cells[0].strip()
                address = cells[1].strip() if len(cells) > 1 else ""
                sdn_type = cells[2].strip() if len(cells) > 2 else ""
                programs = cells[3].strip() if len(cells) > 3 else ""
                list_source = cells[4].strip() if len(cells) > 4 else "SDN"
                score = cells[5].strip() if len(cells) > 5 else "100"
                if not name:
                    continue

                m_href = re.search(r'href=["\']([^"\']*Details\.aspx\?id=(\d+)[^"\']*)["\']', r_html, flags=re.I)
                ent_num_str = m_href.group(2) if m_href else ""
                ent_num = int(ent_num_str) if ent_num_str.isdigit() else None
                detail_url = (
                    f"https://sanctionssearch.ofac.treas.gov/Details.aspx?id={ent_num_str}"
                    if ent_num_str
                    else OFAC_SEARCH_URL
                )
                dedup_key = ent_num_str or f"{name.lower()}|{list_source.lower()}"
                if dedup_key in seen_ids:
                    continue
                seen_ids.add(dedup_key)

                rec: dict[str, Any] = {
                    "record_type": "OFAC_LIVE",
                    "id": -(100000 + (ent_num or idx)),
                    "title": name,
                    "native_title": "",
                    "short_description": (
                        f"OFAC Live {list_source} ({sdn_type or 'Entity'})"
                        + (f" · Programs: {programs}" if programs else "")
                        + (f" · Match Score: {score}%" if score else "")
                    ),
                    "editorial_content": (
                        f"Official U.S. Treasury OFAC Live Portal Result\n"
                        f"List: {list_source} · Type: {sdn_type or 'Entity'} · Score: {score}%\n"
                        + (f"Programs: {programs}\n" if programs else "")
                        + (f"Address: {address}\n" if address else "")
                    ).strip(),
                    "publication_date": now[:10],
                    "category_en": f"OFAC Live {list_source} ({programs or 'SANCTIONS'})",
                    "category_fa": f"استعلام زنده اوفک OFAC {list_source} ({programs or 'تحریم'})",
                    "organizations": sdn_type or list_source,
                    "tags": programs or list_source,
                    "source_name": f"U.S. Treasury OFAC Live ({list_source})",
                    "source_url": detail_url,
                    "extraction_status": "OFAC_LIVE_VERIFIED",
                    "retrieved_at": now,
                    "record_version": 1,
                    "ofac_ent_num": ent_num,
                    "ofac_list_source": list_source,
                    "ofac_sdn_type": sdn_type,
                    "ofac_programs": programs,
                    "ofac_aliases": "",
                    "ofac_addresses": address,
                    "ofac_countries": "",
                    "ofac_match_score": score,
                    "os_id": "",
                    "os_schema": "",
                    "os_datasets": "",
                    "os_identifiers": "",
                    "wikiran_doc_type": "",
                }
                if effective_exact and not matches_exact_word_or_phrase(rec, clean_q):
                    continue
                formatted.append(rec)
                if len(formatted) >= max_results:
                    break

        total_found = len(formatted)
        return {
            "online": True,
            "query": clean_q,
            "exact_match": effective_exact,
            "total_int": total_found,
            "total_label": f"{total_found:,} official hit{'s' if total_found != 1 else ''}",
            "fetched_count": total_found,
            "results": formatted,
            "search_url": OFAC_SEARCH_URL,
        }
    except Exception as exc:
        return {
            "online": False,
            "error": str(exc),
            "query": clean_q,
            "exact_match": effective_exact,
            "total_int": 0,
            "total_label": "Offline",
            "fetched_count": 0,
            "results": [],
            "search_url": OFAC_SEARCH_URL,
        }


def search_opensanctions_live(
    query: str,
    *,
    exact_match: bool = False,
    max_results: int = 30,
    timeout: float = 14.0,
) -> dict[str, Any]:
    """
    Perform a live real-time search directly against OpenSanctions' public search portal
    (`https://www.opensanctions.org/search/?q=...`), requiring zero API key.
    """
    clean_q, effective_exact = parse_exact_query(query, exact_match)
    if not clean_q:
        return {
            "online": True,
            "query": "",
            "exact_match": effective_exact,
            "total_int": 0,
            "total_label": "0 results",
            "fetched_count": 0,
            "results": [],
            "search_url": OPENSANCTIONS_SEARCH_BASE,
        }

    search_param = f'"{clean_q}"' if (effective_exact and " " in clean_q) else clean_q
    search_url = f"{OPENSANCTIONS_SEARCH_BASE}?{urllib.parse.urlencode({'q': search_param})}"

    try:
        req = urllib.request.Request(
            search_url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        raw_html = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", errors="replace")

        # Parse all <li> result items referencing /entities/<id>/
        cards = re.findall(
            r'<li[^>]*class=["\'][^"\']*resultItem[^"\']*["\'][^>]*>(.*?)</li>',
            raw_html,
            flags=re.S | re.I,
        )
        if not cards:
            cards = re.findall(
                r"<li[^>]*>(?:(?!<li).)*?/entities/(?:(?!<li).)*?</li>",
                raw_html,
                flags=re.S | re.I,
            )

        now = utc_now_iso()
        formatted: list[dict[str, Any]] = []
        seen_os_ids: set[str] = set()

        for idx, card_html in enumerate(cards, start=1):
            m_link = re.search(
                r'<a[^>]*href=["\'](/entities/([^/"\']+)/?)["\'][^>]*>(.*?)</a>',
                card_html,
                flags=re.S | re.I,
            )
            if not m_link:
                continue
            rel_href = m_link.group(1).strip()
            os_id = m_link.group(2).strip()
            title = _strip_tags(m_link.group(3))
            if not title or not os_id or os_id in seen_os_ids:
                continue
            seen_os_ids.add(os_id)

            # Extract badge spans (schema type vs risk/sanction flags)
            badge_matches = re.findall(
                r'<span[^>]*class=["\']([^"\']*badge[^"\']*)["\'][^>]*>(.*?)</span>',
                card_html,
                flags=re.S | re.I,
            )
            schema_type = ""
            risk_badges: list[str] = []
            for b_cls, b_inner in badge_matches:
                lbl = _strip_tags(b_inner)
                if not lbl:
                    continue
                if "bg-light" in b_cls and not schema_type:
                    schema_type = lbl
                else:
                    risk_badges.append(lbl)

            # Extract countries/details from the remainder of <p ...resultDetails>
            details_text = _strip_tags(
                re.sub(
                    r'<span[^>]*class=["\'][^"\']*badge[^"\']*["\'][^>]*>.*?</span>',
                    "",
                    re.sub(r"<div[^>]*resultTitle[^>]*>.*?</div>", "", card_html, flags=re.S | re.I),
                    flags=re.S | re.I,
                )
            )
            countries_clean = re.sub(r"^[·•\s]+", "", details_text).strip()
            countries_list = [c.strip() for c in re.split(r"\s*[·•]\s*", countries_clean) if c.strip()]
            countries_str = ", ".join(countries_list)
            badges_str = ", ".join(risk_badges)

            full_url = f"https://www.opensanctions.org{rel_href}"
            rec: dict[str, Any] = {
                "record_type": "OPENSANCTIONS_LIVE",
                "id": -(200000 + idx),
                "title": title,
                "native_title": "",
                "short_description": (
                    f"OpenSanctions Live ({schema_type or 'Entity'})"
                    + (f" · Status: {badges_str}" if badges_str else "")
                    + (f" · Countries: {countries_str}" if countries_str else "")
                ),
                "editorial_content": (
                    f"Live OpenSanctions.org Global Search Hit\n"
                    f"Entity ID: {os_id} · Schema: {schema_type or 'Entity'}\n"
                    + (f"Topics / Sanctions Flags: {badges_str}\n" if badges_str else "")
                    + (f"Countries / Jurisdictions: {countries_str}\n" if countries_str else "")
                ).strip(),
                "publication_date": now[:10],
                "category_en": f"OpenSanctions Live {schema_type or 'Entity'}" + (f" ({badges_str})" if badges_str else ""),
                "category_fa": f"استعلام زنده OpenSanctions ({schema_type or 'نهاد'})" + (f" · {badges_str}" if badges_str else ""),
                "organizations": countries_str or schema_type or "Global",
                "tags": badges_str or schema_type or "OpenSanctions",
                "source_name": "OpenSanctions.org Live Global Portal",
                "source_url": full_url,
                "extraction_status": "OPENSANCTIONS_LIVE_VERIFIED",
                "retrieved_at": now,
                "record_version": 1,
                "ofac_ent_num": None,
                "ofac_list_source": "",
                "ofac_sdn_type": "",
                "ofac_programs": "",
                "ofac_aliases": "",
                "ofac_addresses": "",
                "ofac_countries": countries_str,
                "os_id": os_id,
                "os_schema": schema_type or "Entity",
                "os_datasets": badges_str or "opensanctions_live",
                "os_identifiers": os_id,
                "wikiran_doc_type": "",
            }
            if effective_exact and not matches_exact_word_or_phrase(rec, clean_q):
                continue
            formatted.append(rec)
            if len(formatted) >= max_results:
                break

        total_found = len(formatted)
        return {
            "online": True,
            "query": clean_q,
            "exact_match": effective_exact,
            "total_int": total_found,
            "total_label": f"{total_found:,} live entit{'ies' if total_found != 1 else 'y'}",
            "fetched_count": total_found,
            "results": formatted,
            "search_url": search_url,
        }
    except Exception as exc:
        return {
            "online": False,
            "error": str(exc),
            "query": clean_q,
            "exact_match": effective_exact,
            "total_int": 0,
            "total_label": "Offline",
            "fetched_count": 0,
            "results": [],
            "search_url": search_url,
        }
