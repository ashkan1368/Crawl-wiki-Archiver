"""
Official U.S. Treasury OFAC Sanctions List Service (SLS) Collector & Offline SQLite/FTS5 Indexer.

Uses the official public OFAC SLS API documented in:
  "OFAC's Sanctions List Service — Basic Application Programming Interface (API) Documentation"
Base URL: https://sanctionslistservice.ofac.treas.gov

Endpoints used:
  - GET /alive                           (health status)
  - GET /changes/history/{year}          (latest publicationID & datePublished for regular update checks)
  - GET /sanctions-lists                 (official list catalogue)
  - GET /sanctions-programs              (official sanctions programs catalogue)
  - GET /api/download/SDN.CSV            (SDN List primary records)
  - GET /api/download/ALT.CSV            (SDN List aliases / AKAs)
  - GET /api/download/ADD.CSV            (SDN List addresses & countries)
  - GET /api/download/SDN_COMMENTS.CSV   (SDN List extended remarks)
  - GET /api/download/CONS_PRIM.CSV      (Non-SDN Consolidated List primary records)
  - GET /api/download/CONS_ALT.CSV       (Non-SDN Consolidated List aliases / AKAs)
  - GET /api/download/CONS_ADD.CSV       (Non-SDN Consolidated List addresses & countries)
  - GET /api/download/CONS_COMMENTS.CSV  (Non-SDN Consolidated List extended remarks)
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
import urllib.error
import urllib.request
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..database.repository import ArchiveRepository, utc_now_iso

OFAC_BASE_URL = "https://sanctionslistservice.ofac.treas.gov"
OFAC_USER_AGENT = "WikIranArchive-OFAC-ComplianceSync/1.0 (+https://sanctionslistservice.ofac.treas.gov)"

OFAC_FILE_BUNDLES: list[tuple[str, str, str, str, str]] = [
    # (list_source, primary_file, alt_file, add_file, comments_file)
    ("SDN", "SDN.CSV", "ALT.CSV", "ADD.CSV", "SDN_COMMENTS.CSV"),
    ("CONSOLIDATED", "CONS_PRIM.CSV", "CONS_ALT.CSV", "CONS_ADD.CSV", "CONS_COMMENTS.CSV"),
]


def _clean_ofac_cell(val: str | None) -> str:
    """Clean OFAC CSV null placeholder ('-0-') and trim whitespace."""
    if val is None:
        return ""
    s = val.strip()
    if s in ("-0-", "-0", ""):
        return ""
    return s


def default_ofac_fetcher(url: str, timeout: int = 45) -> tuple[int, str]:
    """Perform a standard GET request against OFAC's Sanctions List Service."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": OFAC_USER_AGENT,
            "Accept": "*/*",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return int(resp.status), raw.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return int(exc.code), body


def check_ofac_updates(
    repo: ArchiveRepository,
    fetcher: Callable[[str], tuple[int, str]] | None = None,
) -> dict[str, Any]:
    """
    Query OFAC SLS /alive, /changes/history/{year}, /sanctions-lists, and /sanctions-programs
    to determine whether a newer Treasury sanctions publication is available.
    """
    fetch = fetcher or default_ofac_fetcher
    settings = repo.get_settings()
    stored_pub_raw = settings.get("ofac_last_publication_id", "").strip()
    stored_pub_id = int(stored_pub_raw) if stored_pub_raw.isdigit() else None
    stored_date = settings.get("ofac_last_date_published", "")

    alive_ok = False
    try:
        st, _ = fetch(f"{OFAC_BASE_URL}/alive")
        alive_ok = st == 200
    except Exception:
        alive_ok = False

    latest_pub_id: int | None = None
    latest_date_published = ""
    current_year = datetime.now(timezone.utc).year
    for year in (current_year, current_year - 1):
        try:
            st, body = fetch(f"{OFAC_BASE_URL}/changes/history/{year}")
            if st == 200 and body.strip():
                items = json.loads(body)
                if isinstance(items, list) and items:
                    # Pick highest publicationID safely regardless of sort order
                    newest = max(items, key=lambda x: int(x.get("publicationID", 0)))
                    latest_pub_id = int(newest.get("publicationID", 0))
                    latest_date_published = str(newest.get("datePublished", ""))
                    break
        except Exception:
            continue

    sanctions_lists: list[str] = []
    try:
        st, body = fetch(f"{OFAC_BASE_URL}/sanctions-lists")
        if st == 200 and body.strip():
            parsed = json.loads(body)
            if isinstance(parsed, list):
                sanctions_lists = [str(x) for x in parsed]
    except Exception:
        pass

    sanctions_programs: list[str] = []
    try:
        st, body = fetch(f"{OFAC_BASE_URL}/sanctions-programs")
        if st == 200 and body.strip():
            parsed = json.loads(body)
            if isinstance(parsed, list):
                sanctions_programs = [str(x) for x in parsed]
    except Exception:
        pass

    local_count = int(repo.conn.execute("SELECT COUNT(*) FROM ofac_entities;").fetchone()[0])
    update_available = (
        local_count == 0
        or (latest_pub_id is not None and stored_pub_id != latest_pub_id)
    )

    return {
        "ok": True,
        "service_alive": alive_ok,
        "latest_publication_id": latest_pub_id,
        "latest_date_published": latest_date_published,
        "stored_publication_id": stored_pub_id,
        "stored_date_published": stored_date,
        "local_entities_count": local_count,
        "update_available": update_available,
        "sanctions_lists": sanctions_lists,
        "sanctions_programs_count": len(sanctions_programs),
        "checked_at": utc_now_iso(),
    }


def _parse_ofac_bundle(
    list_source: str,
    prim_csv: str,
    alt_csv: str,
    add_csv: str,
    comments_csv: str,
    publication_id: int | None,
    date_published: str,
    retrieved_at: str,
) -> list[dict[str, Any]]:
    """Join OFAC Primary + ALT + ADD + COMMENTS CSV files by ent_num into normalized records."""
    aliases_by_ent: dict[int, list[str]] = defaultdict(list)
    if alt_csv.strip():
        reader = csv.reader(io.StringIO(alt_csv))
        for row in reader:
            if len(row) < 4:
                continue
            ent_raw = _clean_ofac_cell(row[0])
            if not ent_raw.isdigit():
                continue
            alt_type = _clean_ofac_cell(row[2])
            alt_name = _clean_ofac_cell(row[3])
            if alt_name:
                label = f"{alt_type}: {alt_name}" if alt_type else alt_name
                aliases_by_ent[int(ent_raw)].append(label)

    addresses_by_ent: dict[int, list[str]] = defaultdict(list)
    countries_by_ent: dict[int, list[str]] = defaultdict(list)
    if add_csv.strip():
        reader = csv.reader(io.StringIO(add_csv))
        for row in reader:
            if len(row) < 5:
                continue
            ent_raw = _clean_ofac_cell(row[0])
            if not ent_raw.isdigit():
                continue
            street = _clean_ofac_cell(row[2])
            city_state = _clean_ofac_cell(row[3])
            country = _clean_ofac_cell(row[4])
            parts = [p for p in (street, city_state, country) if p]
            if parts:
                addresses_by_ent[int(ent_raw)].append(", ".join(parts))
            if country and country not in countries_by_ent[int(ent_raw)]:
                countries_by_ent[int(ent_raw)].append(country)

    ext_comments_by_ent: dict[int, list[str]] = defaultdict(list)
    if comments_csv.strip():
        reader = csv.reader(io.StringIO(comments_csv))
        for row in reader:
            if len(row) < 2:
                continue
            ent_raw = _clean_ofac_cell(row[0])
            if not ent_raw.isdigit():
                continue
            ext = _clean_ofac_cell(row[1])
            if ext:
                ext_comments_by_ent[int(ent_raw)].append(ext)

    records: list[dict[str, Any]] = []
    seen_ent_nums: set[int] = set()
    reader = csv.reader(io.StringIO(prim_csv))
    for row in reader:
        if len(row) < 4:
            continue
        ent_raw = _clean_ofac_cell(row[0])
        if not ent_raw.isdigit():
            continue
        ent_num = int(ent_raw)
        if ent_num in seen_ent_nums:
            continue
        seen_ent_nums.add(ent_num)

        sdn_name = _clean_ofac_cell(row[1])
        if not sdn_name:
            continue
        sdn_type = _clean_ofac_cell(row[2]) or "entity"
        raw_programs = _clean_ofac_cell(row[3])
        programs = "; ".join(
            p.strip(" []\t\r\n")
            for p in raw_programs.replace("] [", ";").replace("][", ";").split(";")
            if p.strip(" []\t\r\n")
        )
        title = _clean_ofac_cell(row[4]) if len(row) > 4 else ""
        call_sign = _clean_ofac_cell(row[5]) if len(row) > 5 else ""
        vessel_type = _clean_ofac_cell(row[6]) if len(row) > 6 else ""
        tonnage = _clean_ofac_cell(row[7]) if len(row) > 7 else ""
        grt = _clean_ofac_cell(row[8]) if len(row) > 8 else ""
        vessel_flag = _clean_ofac_cell(row[9]) if len(row) > 9 else ""
        vessel_owner = _clean_ofac_cell(row[10]) if len(row) > 10 else ""
        remarks = _clean_ofac_cell(row[11]) if len(row) > 11 else ""

        if ent_num in ext_comments_by_ent:
            extra = " ".join(ext_comments_by_ent[ent_num])
            remarks = f"{remarks} {extra}".strip() if remarks else extra

        aliases_text = " | ".join(aliases_by_ent.get(ent_num, []))
        addresses_text = " ; ".join(addresses_by_ent.get(ent_num, []))
        countries_text = ", ".join(countries_by_ent.get(ent_num, []))

        records.append(
            {
                "ent_num": ent_num,
                "list_source": list_source,
                "sdn_name": sdn_name,
                "sdn_type": sdn_type,
                "programs": programs,
                "title": title,
                "call_sign": call_sign,
                "vessel_type": vessel_type,
                "tonnage": tonnage,
                "grt": grt,
                "vessel_flag": vessel_flag,
                "vessel_owner": vessel_owner,
                "remarks": remarks,
                "aliases_text": aliases_text,
                "addresses_text": addresses_text,
                "countries_text": countries_text,
                "publication_id": publication_id,
                "date_published": (date_published or "")[:10],
                "source_url": f"{OFAC_BASE_URL}/entities/{ent_num}",
                "retrieved_at": retrieved_at,
            }
        )

    return records


def sync_ofac_lists(
    repo: ArchiveRepository,
    *,
    force: bool = False,
    check_only: bool = False,
    exports_dir: str | Path | None = None,
    fetcher: Callable[[str], tuple[int, str]] | None = None,
) -> dict[str, Any]:
    """
    Check for OFAC updates and download/index the complete U.S. Treasury SDN + Non-SDN
    Consolidated sanctions datasets into local SQLite + FTS5 for instant offline screening.
    """
    fetch = fetcher or default_ofac_fetcher
    check_info = check_ofac_updates(repo, fetcher=fetch)

    if check_only:
        return {
            **check_info,
            "action": "CHECK_ONLY",
            "summary": get_ofac_summary(repo.conn, repo.get_settings()),
        }

    if not force and not check_info["update_available"] and check_info["local_entities_count"] > 0:
        return {
            **check_info,
            "action": "UP_TO_DATE",
            "synced_count": check_info["local_entities_count"],
            "summary": get_ofac_summary(repo.conn, repo.get_settings()),
        }

    now_iso = utc_now_iso()
    cur_job = repo.conn.execute(
        """
        INSERT INTO collection_jobs (job_uuid, job_type, status, started_at, checkpoint_data)
        VALUES (?, 'OFAC_SANCTIONS_SYNC', 'RUNNING', ?, '{}');
        """,
        (str(uuid.uuid4()), now_iso),
    )
    job_id = int(cur_job.lastrowid)
    repo.conn.commit()
    pub_id = check_info.get("latest_publication_id")
    date_pub = check_info.get("latest_date_published") or now_iso[:10]

    # Ensure OFAC source record exists in sources table
    repo.upsert_source(
        name="U.S. Treasury OFAC Sanctions List Service (SDN + Consolidated)",
        source_type="OFAC_SANCTIONS_API",
        base_url=OFAC_BASE_URL,
        source_url=f"{OFAC_BASE_URL}/api/download/SDN.CSV",
        robots_status="PUBLIC_API",
    )

    def _log_hist(url: str, http_st: int, action: str, msg: str) -> None:
        repo.conn.execute(
            """
            INSERT INTO collection_history (job_id, target_url, record_type, http_status, action_taken, timestamp, message)
            VALUES (?, ?, 'OFAC_SANCTION', ?, ?, ?, ?);
            """,
            (job_id, url, http_st, action, utc_now_iso(), msg),
        )

    all_records: list[dict[str, Any]] = []
    downloaded_files = 0
    failed_files = 0
    raw_dir: Path | None = None
    if exports_dir is not None:
        try:
            raw_dir = Path(exports_dir) / "ofac_raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            raw_dir = None

    for list_source, prim_file, alt_file, add_file, comments_file in OFAC_FILE_BUNDLES:
        file_texts: dict[str, str] = {}
        for fname in (prim_file, alt_file, add_file, comments_file):
            url = f"{OFAC_BASE_URL}/api/download/{fname}"
            try:
                st, text = fetch(url)
                if st == 200:
                    file_texts[fname] = text
                    downloaded_files += 1
                    if raw_dir is not None:
                        try:
                            (raw_dir / fname).write_text(text, encoding="utf-8")
                        except Exception:
                            pass
                    _log_hist(url, st, "DOWNLOADED", f"Downloaded {fname} ({len(text.encode('utf-8')):,} bytes)")
                else:
                    file_texts[fname] = ""
                    failed_files += 1
                    _log_hist(url, st, "FAILED", f"HTTP {st} downloading {fname}")
            except Exception as exc:
                file_texts[fname] = ""
                failed_files += 1
                _log_hist(url, 0, "FAILED", f"Network error downloading {fname}: {exc}")

        if file_texts.get(prim_file):
            parsed = _parse_ofac_bundle(
                list_source=list_source,
                prim_csv=file_texts[prim_file],
                alt_csv=file_texts.get(alt_file, ""),
                add_csv=file_texts.get(add_file, ""),
                comments_csv=file_texts.get(comments_file, ""),
                publication_id=pub_id,
                date_published=date_pub,
                retrieved_at=now_iso,
            )
            all_records.extend(parsed)

    if not all_records:
        repo.conn.execute(
            """
            UPDATE collection_jobs
            SET status = 'FAILED', finished_at = ?, total_discovered = ?,
                processed_count = ?, failed_count = ?, error_summary = ?
            WHERE id = ?;
            """,
            (
                utc_now_iso(),
                downloaded_files + failed_files,
                downloaded_files,
                failed_files,
                "No OFAC records could be downloaded from sanctionslistservice.ofac.treas.gov.",
                job_id,
            ),
        )
        repo.conn.commit()
        return {
            "ok": False,
            "action": "FAILED",
            "error": "Unable to download OFAC sanctions files from U.S. Treasury SLS.",
            "summary": get_ofac_summary(repo.conn, repo.get_settings()),
        }

    # Atomically replace ofac_entities and OFAC entries in fts_archive in a single transaction
    cur = repo.conn.cursor()
    cur.execute("DELETE FROM fts_archive WHERE record_type = 'OFAC_SANCTION';")
    cur.execute("DELETE FROM ofac_entities;")

    insert_rows = [
        (
            r["ent_num"],
            r["list_source"],
            r["sdn_name"],
            r["sdn_type"],
            r["programs"],
            r["title"],
            r["call_sign"],
            r["vessel_type"],
            r["tonnage"],
            r["grt"],
            r["vessel_flag"],
            r["vessel_owner"],
            r["remarks"],
            r["aliases_text"],
            r["addresses_text"],
            r["countries_text"],
            r["publication_id"],
            r["date_published"],
            r["source_url"],
            r["retrieved_at"],
        )
        for r in all_records
    ]

    cur.executemany(
        """
        INSERT OR REPLACE INTO ofac_entities (
            ent_num, list_source, sdn_name, sdn_type, programs, title,
            call_sign, vessel_type, tonnage, grt, vessel_flag, vessel_owner,
            remarks, aliases_text, addresses_text, countries_text,
            publication_id, date_published, source_url, retrieved_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        insert_rows,
    )

    # Bulk-populate fts_archive directly via SQL SELECT from ofac_entities (ultra-fast!)
    cur.execute(
        """
        INSERT INTO fts_archive (
            record_type, record_id, title, editorial_content, summary,
            organization_names, entity_names, category_names, tag_names,
            publication_date, source_url
        )
        SELECT
            'OFAC_SANCTION',
            CAST(id AS TEXT),
            sdn_name,
            TRIM(
                sdn_name || ' ' || aliases_text || ' ' || programs || ' ' ||
                sdn_type || ' ' || title || ' ' || addresses_text || ' ' ||
                countries_text || ' ' || call_sign || ' ' || vessel_flag || ' ' ||
                vessel_owner || ' ' || remarks || ' OFAC-' || CAST(ent_num AS TEXT)
            ),
            TRIM(
                'OFAC ' || list_source || ' (' || COALESCE(NULLIF(sdn_type, ''), 'entity') || ')'
                || CASE WHEN programs != '' THEN ' | Programs: ' || programs ELSE '' END
                || CASE WHEN countries_text != '' THEN ' | Countries: ' || countries_text ELSE '' END
                || CASE WHEN aliases_text != '' THEN ' | AKAs: ' || SUBSTR(aliases_text, 1, 240) ELSE '' END
            ),
            sdn_name || CASE WHEN vessel_owner != '' THEN ' ' || vessel_owner ELSE '' END,
            aliases_text,
            'OFAC ' || list_source || ' Sanctions',
            programs,
            COALESCE(NULLIF(date_published, ''), SUBSTR(retrieved_at, 1, 10)),
            source_url
        FROM ofac_entities;
        """
    )

    repo.conn.commit()

    if pub_id is not None:
        repo.set_setting("ofac_last_publication_id", str(pub_id))
    repo.set_setting("ofac_last_date_published", date_pub)
    repo.set_setting("ofac_last_synced_at", now_iso)
    if check_info.get("sanctions_lists"):
        repo.set_setting("ofac_lists_json", json.dumps(check_info["sanctions_lists"]))
    if check_info.get("sanctions_programs_count"):
        repo.set_setting("ofac_programs_count", str(check_info["sanctions_programs_count"]))

    checkpoint_payload = json.dumps(
        {
            "publication_id": pub_id,
            "date_published": date_pub,
            "files_downloaded": downloaded_files,
            "content_hash": hashlib.sha256(f"{pub_id}:{len(all_records)}:{date_pub}".encode("utf-8")).hexdigest(),
        }
    )
    repo.conn.execute(
        """
        UPDATE collection_jobs
        SET status = 'COMPLETED', finished_at = ?, total_discovered = ?,
            processed_count = ?, new_records_count = ?, failed_count = ?,
            checkpoint_data = ?
        WHERE id = ?;
        """,
        (
            utc_now_iso(),
            len(all_records),
            len(all_records),
            len(all_records),
            failed_files,
            checkpoint_payload,
            job_id,
        ),
    )
    repo.conn.commit()

    summary = get_ofac_summary(repo.conn, repo.get_settings())
    return {
        "ok": True,
        "action": "SYNCED",
        "publication_id": pub_id,
        "date_published": date_pub,
        "synced_count": len(all_records),
        "downloaded_files": downloaded_files,
        "failed_files": failed_files,
        "summary": summary,
    }


def get_ofac_summary(conn: sqlite3.Connection, settings: dict[str, str] | None = None) -> dict[str, Any]:
    """Return offline OFAC dataset summary metrics, top programs, and list breakdown."""
    settings = settings or {}
    try:
        total = int(conn.execute("SELECT COUNT(*) FROM ofac_entities;").fetchone()[0])
    except Exception:
        total = 0

    if total == 0:
        return {
            "total_entities": 0,
            "sdn_count": 0,
            "consolidated_count": 0,
            "iran_related_count": 0,
            "individuals_count": 0,
            "organizations_count": 0,
            "vessels_count": 0,
            "aircraft_count": 0,
            "last_publication_id": settings.get("ofac_last_publication_id", ""),
            "last_date_published": settings.get("ofac_last_date_published", ""),
            "last_synced_at": settings.get("ofac_last_synced_at", ""),
            "sanctions_lists": json.loads(settings.get("ofac_lists_json", "[]") or "[]"),
            "sanctions_programs_count": int(settings.get("ofac_programs_count", "0") or "0"),
            "top_programs": [],
            "sample_iran_entities": [],
        }

    sdn_count = int(
        conn.execute("SELECT COUNT(*) FROM ofac_entities WHERE list_source = 'SDN';").fetchone()[0]
    )
    cons_count = int(
        conn.execute("SELECT COUNT(*) FROM ofac_entities WHERE list_source = 'CONSOLIDATED';").fetchone()[0]
    )
    iran_count = int(
        conn.execute(
            """
            SELECT COUNT(*) FROM ofac_entities
            WHERE UPPER(programs) LIKE '%IRAN%'
               OR UPPER(programs) LIKE '%IRGC%'
               OR UPPER(programs) LIKE '%IFSR%'
               OR UPPER(programs) LIKE '%IFCA%'
               OR UPPER(programs) LIKE '%FSE-IR%'
               OR UPPER(programs) LIKE '%HRIT-IR%'
               OR UPPER(countries_text) LIKE '%IRAN%';
            """
        ).fetchone()[0]
    )

    type_rows = conn.execute(
        "SELECT LOWER(COALESCE(sdn_type, 'entity')) AS t, COUNT(*) AS c FROM ofac_entities GROUP BY t;"
    ).fetchall()
    type_counts = {str(r["t"]): int(r["c"]) for r in type_rows}

    import re as _re
    prog_counter: Counter[str] = Counter()
    for r in conn.execute("SELECT programs FROM ofac_entities WHERE programs != '';").fetchall():
        for token in _re.split(r"(?:;|\s*\]\s*\[\s*)", str(r["programs"])):
            p = token.strip(" []\t\r\n")
            if p:
                prog_counter[p] += 1

    top_programs = [{"program": p, "count": c} for p, c in prog_counter.most_common(12)]

    sample_rows = conn.execute(
        """
        SELECT id, ent_num, list_source, sdn_name, sdn_type, programs,
               aliases_text, countries_text, remarks, date_published, source_url
        FROM ofac_entities
        WHERE UPPER(programs) LIKE '%IRAN%' OR UPPER(programs) LIKE '%IRGC%'
        ORDER BY ent_num DESC
        LIMIT 20;
        """
    ).fetchall()

    return {
        "total_entities": total,
        "sdn_count": sdn_count,
        "consolidated_count": cons_count,
        "iran_related_count": iran_count,
        "individuals_count": type_counts.get("individual", 0),
        "organizations_count": type_counts.get("entity", 0) + type_counts.get("", 0),
        "vessels_count": type_counts.get("vessel", 0),
        "aircraft_count": type_counts.get("aircraft", 0),
        "last_publication_id": settings.get("ofac_last_publication_id", ""),
        "last_date_published": settings.get("ofac_last_date_published", ""),
        "last_synced_at": settings.get("ofac_last_synced_at", ""),
        "sanctions_lists": json.loads(settings.get("ofac_lists_json", "[]") or "[]"),
        "sanctions_programs_count": int(settings.get("ofac_programs_count", "0") or "0"),
        "top_programs": top_programs,
        "sample_iran_entities": [dict(r) for r in sample_rows],
    }
