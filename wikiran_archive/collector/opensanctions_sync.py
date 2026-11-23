"""
OpenSanctions Consolidated Global Sanctions Collector & Offline SQLite/FTS5 Indexer.

Uses official OpenSanctions bulk datasets:
  - Catalog Index: https://data.opensanctions.org/datasets/latest/index.json
  - Consolidated Sanctions CSV: https://data.opensanctions.org/datasets/latest/sanctions/targets.simple.csv
    (Combines UN, EU, UK OFSI, US OFAC, Switzerland SECO, Canada, Australia, Japan, and 100+ official lists)

Supports:
  - Lightweight update detection via index.json (`last_change` & `target_count`)
  - Streaming bulk download & raw CSV archival under `exports/opensanctions_raw/`
  - High-speed chunked SQLite + FTS5 indexing for instant 100% offline screening
"""

from __future__ import annotations

import csv
import json
import sqlite3
import tempfile
import urllib.error
import urllib.request
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from ..database.repository import ArchiveRepository, utc_now_iso

OPENSANCTIONS_INDEX_URL = "https://data.opensanctions.org/datasets/latest/index.json"
OPENSANCTIONS_DATASET_BASE = "https://data.opensanctions.org/datasets/latest"
OPENSANCTIONS_USER_AGENT = "WikIranArchive-OpenSanctionsSync/2.0 (+https://www.opensanctions.org/datasets/)"


def _default_json_fetch(url: str, timeout: int = 30) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": OPENSANCTIONS_USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return int(exc.code), body


def _stream_download_file(url: str, destination: Path, timeout: int = 180) -> int:
    """Stream a large remote CSV file to disk in 256 KB chunks and return total bytes written."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": OPENSANCTIONS_USER_AGENT,
            "Accept": "text/csv,*/*",
        },
        method="GET",
    )
    total_bytes = 0
    tmp_path = destination.with_suffix(destination.suffix + ".part")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, tmp_path.open("wb") as out:
            while True:
                chunk = resp.read(262144)
                if not chunk:
                    break
                out.write(chunk)
                total_bytes += len(chunk)
        tmp_path.replace(destination)
        return total_bytes
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def _ensure_opensanctions_table(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS opensanctions_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            os_id TEXT NOT NULL UNIQUE,
            schema_type TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL,
            aliases TEXT NOT NULL DEFAULT '',
            birth_date TEXT NOT NULL DEFAULT '',
            countries TEXT NOT NULL DEFAULT '',
            addresses TEXT NOT NULL DEFAULT '',
            identifiers TEXT NOT NULL DEFAULT '',
            sanctions TEXT NOT NULL DEFAULT '',
            phones TEXT NOT NULL DEFAULT '',
            emails TEXT NOT NULL DEFAULT '',
            program_ids TEXT NOT NULL DEFAULT '',
            datasets TEXT NOT NULL DEFAULT '',
            first_seen TEXT NOT NULL DEFAULT '',
            last_seen TEXT NOT NULL DEFAULT '',
            last_change TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            retrieved_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_os_name ON opensanctions_entities(name);
        CREATE INDEX IF NOT EXISTS idx_os_schema ON opensanctions_entities(schema_type);
        CREATE INDEX IF NOT EXISTS idx_os_countries ON opensanctions_entities(countries);
        CREATE INDEX IF NOT EXISTS idx_os_datasets ON opensanctions_entities(datasets);
        """
    )


def check_opensanctions_updates(
    repo: ArchiveRepository,
    dataset_name: str = "sanctions",
    fetcher: Callable[[str], tuple[int, str]] | None = None,
) -> dict[str, Any]:
    """
    Inspect https://data.opensanctions.org/datasets/latest/index.json to discover available datasets,
    source counts, and whether the chosen dataset (default: `sanctions`) has newer records.
    """
    _ensure_opensanctions_table(repo.conn)
    fetch = fetcher or _default_json_fetch
    settings = repo.get_settings()
    stored_last_change = settings.get("opensanctions_last_change", "").strip()
    stored_dataset = settings.get("opensanctions_dataset", dataset_name).strip() or dataset_name

    st, body = fetch(OPENSANCTIONS_INDEX_URL)
    if st != 200 or not body.strip():
        return {
            "ok": False,
            "error": f"Failed to reach OpenSanctions index.json (HTTP {st}).",
            "checked_at": utc_now_iso(),
        }

    catalog = json.loads(body)
    all_datasets = catalog.get("datasets", []) if isinstance(catalog, dict) else []
    target_meta: dict[str, Any] | None = None
    source_datasets: list[dict[str, Any]] = []

    for ds in all_datasets:
        if not isinstance(ds, dict):
            continue
        if ds.get("name") == dataset_name:
            target_meta = ds
        if ds.get("type") == "source":
            source_datasets.append(
                {
                    "name": ds.get("name", ""),
                    "title": ds.get("title", ""),
                    "target_count": int(ds.get("target_count") or 0),
                    "last_change": str(ds.get("last_change") or ""),
                }
            )

    if target_meta is None:
        return {
            "ok": False,
            "error": f"Dataset '{dataset_name}' was not found in OpenSanctions index.json.",
            "checked_at": utc_now_iso(),
        }

    remote_last_change = str(target_meta.get("last_change") or "")
    remote_target_count = int(target_meta.get("target_count") or 0)
    remote_entity_count = int(target_meta.get("entity_count") or 0)
    csv_resource_size = 0
    for res in target_meta.get("resources", []):
        if isinstance(res, dict) and res.get("path") == "targets.simple.csv":
            csv_resource_size = int(res.get("size") or 0)
            break

    local_count = int(
        repo.conn.execute("SELECT COUNT(*) FROM opensanctions_entities;").fetchone()[0]
    )
    update_available = (
        local_count == 0
        or stored_dataset != dataset_name
        or (bool(remote_last_change) and stored_last_change != remote_last_change)
    )

    top_sources = sorted(
        source_datasets, key=lambda s: int(s.get("target_count", 0)), reverse=True
    )[:25]

    return {
        "ok": True,
        "dataset_name": dataset_name,
        "dataset_title": str(target_meta.get("title") or "Consolidated Sanctions"),
        "remote_last_change": remote_last_change,
        "stored_last_change": stored_last_change,
        "remote_target_count": remote_target_count,
        "remote_entity_count": remote_entity_count,
        "csv_size_bytes": csv_resource_size,
        "local_entities_count": local_count,
        "catalog_datasets_count": len(all_datasets),
        "source_datasets_count": len(source_datasets),
        "top_sources": top_sources,
        "update_available": update_available,
        "checked_at": utc_now_iso(),
    }


def _parse_and_load_opensanctions_csv(
    repo: ArchiveRepository,
    csv_path: Path,
    dataset_name: str,
) -> tuple[int, int]:
    """
    Parse OpenSanctions `targets.simple.csv` into `opensanctions_entities` and `fts_archive`.
    Returns (total_loaded, iran_linked_count).
    """
    _ensure_opensanctions_table(repo.conn)
    now = utc_now_iso()

    # Clear previous OpenSanctions records cleanly before atomic bulk load
    repo.conn.execute("DELETE FROM fts_archive WHERE record_type = 'OPENSANCTIONS';")
    repo.conn.execute("DELETE FROM opensanctions_entities;")

    insert_entity_sql = """
        INSERT OR REPLACE INTO opensanctions_entities (
            os_id, schema_type, name, aliases, birth_date, countries,
            addresses, identifiers, sanctions, phones, emails,
            program_ids, datasets, first_seen, last_seen, last_change,
            source_url, retrieved_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    batch: list[tuple[Any, ...]] = []
    total_loaded = 0
    iran_linked = 0

    csv.field_size_limit(10 * 1024 * 1024)
    with csv_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            os_id = (row.get("id") or "").strip()
            name = (row.get("name") or "").strip()
            if not os_id or not name:
                continue

            schema_type = (row.get("schema") or "").strip()
            aliases = (row.get("aliases") or "").strip()[:4000]
            birth_date = (row.get("birth_date") or "").strip()[:120]
            countries = (row.get("countries") or "").strip()[:400]
            addresses = (row.get("addresses") or "").strip()[:2000]
            identifiers = (row.get("identifiers") or "").strip()[:1500]
            sanctions = (row.get("sanctions") or "").strip()[:3000]
            phones = (row.get("phones") or "").strip()[:500]
            emails = (row.get("emails") or "").strip()[:500]
            program_ids = (row.get("program_ids") or "").strip()[:800]
            datasets = (row.get("dataset") or dataset_name).strip()[:1000]
            first_seen = (row.get("first_seen") or "").strip()[:32]
            last_seen = (row.get("last_seen") or "").strip()[:32]
            last_change = (row.get("last_change") or "").strip()[:32]
            source_url = f"https://www.opensanctions.org/entities/{os_id}/"

            # Check Iran relevance
            c_tokens = {c.strip().lower() for c in countries.split(";") if c.strip()}
            combined_upper = f"{program_ids} {sanctions} {datasets} {addresses}".upper()
            if (
                "ir" in c_tokens
                or "IRAN" in combined_upper
                or "IRGC" in combined_upper
                or "IFSR" in combined_upper
            ):
                iran_linked += 1

            batch.append(
                (
                    os_id,
                    schema_type,
                    name,
                    aliases,
                    birth_date,
                    countries,
                    addresses,
                    identifiers,
                    sanctions,
                    phones,
                    emails,
                    program_ids,
                    datasets,
                    first_seen,
                    last_seen,
                    last_change,
                    source_url,
                    now,
                )
            )
            total_loaded += 1

            if len(batch) >= 2500:
                repo.conn.executemany(insert_entity_sql, batch)
                batch.clear()

    if batch:
        repo.conn.executemany(insert_entity_sql, batch)
        batch.clear()

    # Populate FTS5 index directly from opensanctions_entities via fast single SQL statement
    repo.conn.execute(
        """
        INSERT INTO fts_archive (
            record_type, record_id, title, editorial_content, summary,
            organization_names, entity_names, category_names, tag_names,
            publication_date, source_url
        )
        SELECT
            'OPENSANCTIONS',
            CAST(id AS TEXT),
            name,
            TRIM(
                COALESCE(aliases, '') || ' ' ||
                COALESCE(identifiers, '') || ' ' ||
                COALESCE(addresses, '') || ' ' ||
                COALESCE(sanctions, '') || ' ' ||
                COALESCE(emails, '') || ' ' ||
                COALESCE(phones, '')
            ),
            TRIM(
                'OpenSanctions ' || COALESCE(schema_type, 'Entity') ||
                CASE WHEN countries != '' THEN ' | Countries: ' || countries ELSE '' END ||
                CASE WHEN program_ids != '' THEN ' | Programs: ' || program_ids ELSE '' END ||
                CASE WHEN datasets != '' THEN ' | Lists: ' || datasets ELSE '' END
            ),
            COALESCE(countries, ''),
            COALESCE(aliases, ''),
            'OpenSanctions ' || COALESCE(schema_type, 'Sanctions'),
            TRIM(COALESCE(datasets, '') || ' ' || COALESCE(program_ids, '')),
            SUBSTR(COALESCE(NULLIF(last_change, ''), NULLIF(last_seen, ''), retrieved_at), 1, 10),
            source_url
        FROM opensanctions_entities;
        """
    )
    repo.conn.commit()
    return total_loaded, iran_linked


def sync_opensanctions_dataset(
    repo: ArchiveRepository,
    dataset_name: str = "sanctions",
    *,
    force: bool = False,
    check_only: bool = False,
    exports_dir: str | Path | None = None,
) -> dict[str, Any]:
    """
    Check OpenSanctions index.json for updates, download `targets.simple.csv` (Consolidated Sanctions),
    archive the raw CSV locally, and index every target into SQLite + FTS5 for offline screening.
    """
    _ensure_opensanctions_table(repo.conn)
    check = check_opensanctions_updates(repo, dataset_name=dataset_name)
    if not check.get("ok"):
        return {
            **check,
            "summary": get_opensanctions_summary(repo.conn, repo.get_settings()),
        }

    # Always store fresh catalog stats
    repo.set_setting("opensanctions_catalog_count", str(check.get("catalog_datasets_count", 0)))
    repo.set_setting("opensanctions_sources_count", str(check.get("source_datasets_count", 0)))
    repo.set_setting("opensanctions_last_check_at", utc_now_iso())

    if check_only:
        return {
            "ok": True,
            "synced": False,
            "check": check,
            "message": (
                f"OpenSanctions update available ({check['remote_target_count']:,} targets, changed {check['remote_last_change'][:10]})."
                if check["update_available"]
                else f"OpenSanctions is already up to date ({check['local_entities_count']:,} targets offline)."
            ),
            "summary": get_opensanctions_summary(repo.conn, repo.get_settings()),
        }

    if not force and not check["update_available"]:
        return {
            "ok": True,
            "synced": False,
            "up_to_date": True,
            "check": check,
            "message": f"OpenSanctions {dataset_name} is already up to date ({check['local_entities_count']:,} offline targets).",
            "summary": get_opensanctions_summary(repo.conn, repo.get_settings()),
        }

    now = utc_now_iso()
    job_uuid = str(uuid.uuid4())
    cur = repo.conn.execute(
        """
        INSERT INTO collection_jobs (
            job_uuid, job_type, status, started_at, total_discovered, checkpoint_data
        ) VALUES (?, 'OPENSANCTIONS_SYNC', 'RUNNING', ?, ?, '{}');
        """,
        (job_uuid, now, int(check.get("remote_target_count") or 0)),
    )
    job_id = int(cur.lastrowid)
    repo.conn.commit()

    csv_url = f"{OPENSANCTIONS_DATASET_BASE}/{dataset_name}/targets.simple.csv"
    if exports_dir is not None:
        raw_dir = Path(exports_dir) / "opensanctions_raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        csv_dest = raw_dir / f"{dataset_name}_targets.simple.csv"
        (raw_dir / "index_summary.json").write_text(
            json.dumps(check, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        cleanup_temp = False
    else:
        tmp_dir = Path(tempfile.mkdtemp(prefix="os_sync_"))
        csv_dest = tmp_dir / f"{dataset_name}_targets.simple.csv"
        cleanup_temp = True

    try:
        bytes_downloaded = _stream_download_file(csv_url, csv_dest)
        total_loaded, iran_linked = _parse_and_load_opensanctions_csv(
            repo, csv_dest, dataset_name
        )

        repo.set_setting("opensanctions_dataset", dataset_name)
        repo.set_setting("opensanctions_last_change", str(check.get("remote_last_change") or ""))
        repo.set_setting("opensanctions_last_sync_at", utc_now_iso())

        repo.conn.execute(
            """
            UPDATE collection_jobs
            SET status = 'COMPLETED',
                finished_at = ?,
                total_discovered = ?,
                processed_count = ?,
                new_records_count = ?
            WHERE id = ?;
            """,
            (utc_now_iso(), total_loaded, total_loaded, total_loaded, job_id),
        )
        repo.conn.execute(
            """
            INSERT INTO collection_history (
                job_id, target_url, record_type, http_status, action_taken, timestamp, message
            ) VALUES (?, ?, 'OPENSANCTIONS', 200, 'INSERTED', ?, ?);
            """,
            (
                job_id,
                csv_url,
                utc_now_iso(),
                f"Synced {total_loaded:,} OpenSanctions targets ({iran_linked:,} Iran-linked, {bytes_downloaded / (1024 * 1024):.1f} MB CSV)",
            ),
        )
        repo.conn.commit()
        return {
            "ok": True,
            "synced": True,
            "dataset_name": dataset_name,
            "total_loaded": total_loaded,
            "iran_linked_count": iran_linked,
            "bytes_downloaded": bytes_downloaded,
            "raw_csv_path": str(csv_dest) if not cleanup_temp else "",
            "check": check,
            "message": f"Synced {total_loaded:,} OpenSanctions global sanctions targets ({iran_linked:,} Iran-linked) offline.",
            "summary": get_opensanctions_summary(repo.conn, repo.get_settings()),
        }
    except Exception as exc:
        repo.conn.execute(
            """
            UPDATE collection_jobs
            SET status = 'FAILED', finished_at = ?, error_summary = ?
            WHERE id = ?;
            """,
            (utc_now_iso(), str(exc), job_id),
        )
        repo.conn.commit()
        return {
            "ok": False,
            "synced": False,
            "error": f"OpenSanctions sync failed: {exc}",
            "summary": get_opensanctions_summary(repo.conn, repo.get_settings()),
        }
    finally:
        if cleanup_temp:
            csv_dest.unlink(missing_ok=True)


def get_opensanctions_summary(
    conn: sqlite3.Connection,
    settings: dict[str, str],
) -> dict[str, Any]:
    """Return structured offline OpenSanctions statistics & sample Iran-linked preview."""
    try:
        total = int(conn.execute("SELECT COUNT(*) FROM opensanctions_entities;").fetchone()[0])
    except Exception:
        total = 0

    if total == 0:
        return {
            "total_entities": 0,
            "iran_related_count": 0,
            "dataset_name": settings.get("opensanctions_dataset", "sanctions"),
            "last_change": settings.get("opensanctions_last_change", ""),
            "last_sync_at": settings.get("opensanctions_last_sync_at", ""),
            "last_check_at": settings.get("opensanctions_last_check_at", ""),
            "catalog_datasets_count": int(settings.get("opensanctions_catalog_count", "0") or 0),
            "source_datasets_count": int(settings.get("opensanctions_sources_count", "0") or 0),
            "schema_counts": [],
            "top_source_lists": [],
            "sample_iran_entities": [],
        }

    iran_related = int(
        conn.execute(
            """
            SELECT COUNT(*) FROM opensanctions_entities
            WHERE (';' || LOWER(countries) || ';') LIKE '%;ir;%'
               OR UPPER(program_ids) LIKE '%IRAN%'
               OR UPPER(sanctions) LIKE '%IRAN%'
               OR UPPER(sanctions) LIKE '%IRGC%'
               OR UPPER(datasets) LIKE '%IRAN%';
            """
        ).fetchone()[0]
    )

    schema_rows = conn.execute(
        """
        SELECT schema_type, COUNT(*) AS cnt
        FROM opensanctions_entities
        GROUP BY schema_type
        ORDER BY cnt DESC
        LIMIT 8;
        """
    ).fetchall()
    schema_counts = [{"schema": str(r[0] or "Entity"), "count": int(r[1])} for r in schema_rows]

    ds_counter: Counter[str] = Counter()
    for (ds_raw,) in conn.execute("SELECT datasets FROM opensanctions_entities;").fetchall():
        for part in str(ds_raw or "").split(";"):
            p = part.strip()
            if p:
                ds_counter[p] += 1
    top_source_lists = [{"list": k, "count": v} for k, v in ds_counter.most_common(15)]

    sample_rows = conn.execute(
        """
        SELECT id, os_id, schema_type, name, aliases, countries, addresses,
               identifiers, sanctions, program_ids, datasets, last_change, source_url
        FROM opensanctions_entities
        WHERE (';' || LOWER(countries) || ';') LIKE '%;ir;%'
           OR UPPER(program_ids) LIKE '%IRAN%'
           OR UPPER(sanctions) LIKE '%IRAN%'
           OR UPPER(sanctions) LIKE '%IRGC%'
        ORDER BY last_change DESC, id DESC
        LIMIT 40;
        """
    ).fetchall()

    return {
        "total_entities": total,
        "iran_related_count": iran_related,
        "dataset_name": settings.get("opensanctions_dataset", "sanctions"),
        "last_change": settings.get("opensanctions_last_change", ""),
        "last_sync_at": settings.get("opensanctions_last_sync_at", ""),
        "last_check_at": settings.get("opensanctions_last_check_at", ""),
        "catalog_datasets_count": int(settings.get("opensanctions_catalog_count", "0") or 0),
        "source_datasets_count": int(settings.get("opensanctions_sources_count", "0") or 0),
        "schema_counts": schema_counts,
        "top_source_lists": top_source_lists,
        "sample_iran_entities": [dict(r) for r in sample_rows],
    }
