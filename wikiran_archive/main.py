"""
Main entry point for the WikIran Archive Windows 11 Desktop Application & JSON CLI Bridge.
Supports:
- Launching the PySide6 Desktop GUI (`python -m wikiran_archive.main --gui`)
- Initializing and seeding the SQLite database (`--init-db`)
- Running programmatic reconnaissance (`--recon`)
- Serving JSON state to the interactive desktop preview bridge (`--api <action>`)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .backup.manager import BackupManager
from .collector.engine import CollectionEngine
from .collector.ofac_sync import get_ofac_summary, sync_ofac_lists
from .collector.opensanctions_sync import get_opensanctions_summary, sync_opensanctions_dataset
from .collector.reconnaissance import generate_reconnaissance_markdown, run_reconnaissance
from .collector.scheduler import ScheduledCollectionRunner
from .collector.wikiran_live import (
    download_targeted_leaks,
    get_leak_collections_catalog,
    get_wikiran_documents_summary,
    search_wikiran_live,
    sync_wikiran_structured_archives,
)
from .config.settings import AppPaths, resolve_app_paths
from .database.connection import get_connection, verify_database_integrity
from .database.migrations import run_migrations
from .database.repository import ArchiveRepository
from .database.seed import seed_verified_public_archive
from .export.csv_converter import CsvSpreadsheetWorkbench
from .export.exporters import ArchiveExporter
from .logging_utils.logger import friendly_clerk_message, read_diagnostic_logs, setup_logger
from .search.batch_screener import (
    generate_watchlist_template_csv,
    generate_watchlist_template_xlsx,
    run_batch_watchlist_screening,
)
from .search.fts_search import ArchiveSearchEngine, SearchFilters
from .ui.main_window import DesktopController, launch_pyside6_gui


def ensure_initialized(custom_dir: str | Path | None = None) -> tuple[AppPaths, ArchiveRepository]:
    """Ensure external data directories, versioned migrations, and baseline public seed exist."""
    paths = resolve_app_paths(custom_dir)
    setup_logger(paths.logs_dir)
    conn = get_connection(paths.db_path)
    run_migrations(conn)
    repo = ArchiveRepository(conn)
    seed_verified_public_archive(repo)
    csv_wb = CsvSpreadsheetWorkbench(repo, paths.exports_dir)
    csv_wb.ensure_default_csv_dataset()
    if custom_dir is None:
        csv_wb.ensure_unredacted_ledger_dataset()
    return paths, repo


def _resolve_configured_paths_dict(paths: AppPaths, repo: ArchiveRepository) -> dict[str, str]:
    """Return storage paths reflecting user-configured custom_storage_path if set."""
    custom_raw = repo.get_settings().get("custom_storage_path", "").strip()
    if custom_raw:
        # Handle Windows-style paths (e.g. C:\WikIranArchive or D:\Data\WikIran) cleanly
        if ":" in custom_raw or "\\" in custom_raw:
            base = custom_raw.rstrip("\\/")
            return {
                "base_dir": base,
                "db_path": f"{base}\\data\\wikiran_archive.db",
                "backups_dir": f"{base}\\backups",
                "exports_dir": f"{base}\\exports",
                "logs_dir": f"{base}\\logs",
            }
        try:
            custom_p = Path(custom_raw).expanduser().resolve()
            for sub in ("", "data", "backups", "exports", "logs"):
                (custom_p / sub if sub else custom_p).mkdir(parents=True, exist_ok=True)
            return {
                "base_dir": str(custom_p),
                "db_path": str(custom_p / "data" / "wikiran_archive.db"),
                "backups_dir": str(custom_p / "backups"),
                "exports_dir": str(custom_p / "exports"),
                "logs_dir": str(custom_p / "logs"),
            }
        except Exception:
            pass

    return {
        "base_dir": str(paths.base_dir),
        "db_path": str(paths.db_path),
        "backups_dir": str(paths.backups_dir),
        "exports_dir": str(paths.exports_dir),
        "logs_dir": str(paths.logs_dir),
    }


def format_bytes_human(num_bytes: int) -> str:
    """Format a byte count into a readable KB/MB/GB string."""
    size = float(max(0, num_bytes))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def _dir_size_bytes(directory: Path, exclude_names: set[str] | None = None) -> int:
    if not directory.exists() or not directory.is_dir():
        return 0
    total = 0
    for f in directory.rglob("*"):
        if f.is_file():
            if exclude_names and f.name in exclude_names:
                continue
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return total


def compute_storage_volume(paths: AppPaths, repo: ArchiveRepository) -> dict[str, Any]:
    """Compute real on-disk storage footprint (bytes) and total indexed data volume."""
    db_bytes = 0
    for candidate in (
        paths.db_path,
        paths.db_path.with_name(paths.db_path.name + "-wal"),
        paths.db_path.with_name(paths.db_path.name + "-shm"),
    ):
        if candidate.exists() and candidate.is_file():
            try:
                db_bytes += candidate.stat().st_size
            except OSError:
                pass

    backups_bytes = _dir_size_bytes(paths.backups_dir)
    exports_bytes = _dir_size_bytes(paths.exports_dir)
    logs_bytes = _dir_size_bytes(paths.logs_dir)
    total_bytes = db_bytes + backups_bytes + exports_bytes + logs_bytes

    stats = repo.get_dashboard_stats()
    try:
        csv_rows_count = int(repo.conn.execute("SELECT COUNT(*) FROM imported_csv_rows;").fetchone()[0])
    except Exception:
        csv_rows_count = 0
    try:
        fts_indexed_count = int(repo.conn.execute("SELECT COUNT(*) FROM fts_archive;").fetchone()[0])
    except Exception:
        fts_indexed_count = 0
    try:
        ofac_entities_count = int(repo.conn.execute("SELECT COUNT(*) FROM ofac_entities;").fetchone()[0])
    except Exception:
        ofac_entities_count = 0
    try:
        opensanctions_count = int(
            repo.conn.execute("SELECT COUNT(*) FROM opensanctions_entities;").fetchone()[0]
        )
    except Exception:
        opensanctions_count = 0
    try:
        wikiran_docs_count = int(
            repo.conn.execute("SELECT COUNT(*) FROM wikiran_documents;").fetchone()[0]
        )
    except Exception:
        wikiran_docs_count = 0
    try:
        text_bytes = int(
            repo.conn.execute(
                """
                SELECT
                    COALESCE((SELECT SUM(LENGTH(CAST(title AS BLOB)) + LENGTH(CAST(summary AS BLOB)) + LENGTH(CAST(editorial_content AS BLOB))) FROM articles), 0)
                  + COALESCE((SELECT SUM(LENGTH(CAST(title AS BLOB)) + LENGTH(CAST(description AS BLOB))) FROM publications), 0)
                  + COALESCE((SELECT SUM(LENGTH(CAST(searchable_text AS BLOB))) FROM imported_csv_rows), 0)
                  + COALESCE((SELECT SUM(LENGTH(CAST(sdn_name AS BLOB)) + LENGTH(CAST(aliases_text AS BLOB)) + LENGTH(CAST(addresses_text AS BLOB)) + LENGTH(CAST(remarks AS BLOB))) FROM ofac_entities), 0)
                  + COALESCE((SELECT SUM(LENGTH(CAST(name AS BLOB)) + LENGTH(CAST(aliases AS BLOB)) + LENGTH(CAST(addresses AS BLOB)) + LENGTH(CAST(sanctions AS BLOB))) FROM opensanctions_entities), 0)
                  + COALESCE((SELECT SUM(LENGTH(CAST(title AS BLOB)) + LENGTH(CAST(snippet AS BLOB))) FROM wikiran_documents), 0)
                """
            ).fetchone()[0]
        )
    except Exception:
        text_bytes = 0

    total_records = (
        stats["articles_count"]
        + stats["publications_count"]
        + stats["organizations_count"]
        + stats["entities_count"]
        + stats["file_inventory_count"]
        + csv_rows_count
        + ofac_entities_count
        + opensanctions_count
        + wikiran_docs_count
    )

    return {
        "db_bytes": db_bytes,
        "backups_bytes": backups_bytes,
        "exports_bytes": exports_bytes,
        "logs_bytes": logs_bytes,
        "text_bytes": text_bytes,
        "total_bytes": total_bytes,
        "db_size_label": format_bytes_human(db_bytes),
        "total_size_label": format_bytes_human(total_bytes),
        "text_size_label": format_bytes_human(text_bytes),
        "total_records": int(total_records),
        "articles_count": stats["articles_count"],
        "publications_count": stats["publications_count"],
        "csv_rows_count": csv_rows_count,
        "ofac_entities_count": ofac_entities_count,
        "opensanctions_count": opensanctions_count,
        "wikiran_docs_count": wikiran_docs_count,
        "fts_indexed_count": fts_indexed_count,
    }


def handle_api_command(action: str, payload_json: str = "{}", custom_dir: str | Path | None = None) -> dict[str, Any]:
    """Execute a structured action against the real Python SQLite/FTS5 backend."""
    paths, repo = ensure_initialized(custom_dir)
    payload = json.loads(payload_json or "{}")
    lang = repo.get_settings().get("ui_language", "en")
    scheduler = ScheduledCollectionRunner(str(paths.db_path))
    csv_wb = CsvSpreadsheetWorkbench(repo, paths.exports_dir)

    try:
        if action == "overview":
            ok, msg = verify_database_integrity(paths.db_path)
            backup_mgr = BackupManager(paths.db_path, paths.backups_dir)
            return {
                "ok": True,
                "stats": repo.get_dashboard_stats(),
                "trends": repo.get_collection_trends(),
                "schedule": asdict(scheduler.get_schedule_config(repo)),
                "csv_datasets": csv_wb.list_datasets(),
                "active_csv": csv_wb.get_dataset_details(),
                "settings": repo.get_settings(),
                "articles": repo.list_articles(),
                "publications": repo.list_publications(),
                "organizations": repo.list_organizations(),
                "categories": repo.list_categories(),
                "tags": repo.list_tags(),
                "sources": repo.list_sources(),
                "jobs": repo.list_collection_jobs(),
                "history": repo.list_collection_history(limit=60),
                "changes": repo.list_change_log(limit=30),
                "backups": backup_mgr.list_backups(),
                "integrity": {"verified": ok, "message": msg},
                "logs": read_diagnostic_logs(paths.logs_dir, max_lines=100),
                "paths": _resolve_configured_paths_dict(paths, repo),
                "storage_volume": compute_storage_volume(paths, repo),
                "ofac_summary": get_ofac_summary(repo.conn, repo.get_settings()),
                "opensanctions_summary": get_opensanctions_summary(repo.conn, repo.get_settings()),
                "wikiran_docs_summary": get_wikiran_documents_summary(repo.conn, repo.get_settings()),
                "frontier_stats": CollectionEngine(repo).get_frontier_stats(),
            }

        if action == "csv_import":
            details = csv_wb.import_csv_text(
                csv_text=payload.get("csv_text", ""),
                filename=payload.get("filename", "imported_table.csv"),
                dataset_name=payload.get("dataset_name"),
            )
            return {
                "ok": True,
                "csv_datasets": csv_wb.list_datasets(),
                "active_csv": details,
            }

        if action == "csv_view":
            ds_id = payload.get("dataset_id")
            q = payload.get("query", "")
            preview_all = bool(payload.get("preview_all", False))
            cross_dataset_audit = bool(payload.get("cross_dataset_audit", False))
            details = csv_wb.get_dataset_details(
                dataset_id=int(ds_id) if ds_id is not None else None,
                search_query=str(q),
                preview_all=preview_all,
                cross_dataset_audit=cross_dataset_audit,
            )
            return {
                "ok": True,
                "csv_datasets": csv_wb.list_datasets(),
                "active_csv": details,
            }

        if action == "schedule_update":
            updated_sched = scheduler.update_schedule_config(
                enabled=payload.get("enabled"),
                frequency=payload.get("frequency"),
                time_utc=payload.get("time_utc"),
                day_of_week=payload.get("day_of_week"),
                max_items_per_run=payload.get("max_items_per_run"),
                repo=repo,
            )
            return {"ok": True, "schedule": updated_sched, "settings": repo.get_settings()}

        if action == "schedule_run_now":
            res = scheduler.trigger_scheduled_run_now()
            return {
                "ok": True,
                "schedule": res["schedule"],
                "job": res["job"],
                "stats": repo.get_dashboard_stats(),
                "trends": repo.get_collection_trends(),
                "jobs": repo.list_collection_jobs(),
                "history": repo.list_collection_history(limit=60),
            }

        if action == "search":
            raw_query = str(payload.get("query", "") or "").strip()
            req_source_type = payload.get("source_type") or None
            include_live = bool(payload.get("include_live_wikiran", True))
            leak_source_filter = str(payload.get("leak_source") or "").strip() or None
            live_pages = int(payload.get("live_pages", 2))

            filters = SearchFilters(
                query=raw_query,
                date_from=payload.get("date_from") or None,
                date_to=payload.get("date_to") or None,
                category_slug=payload.get("category_slug") or None,
                organization_name=payload.get("organization_name") or None,
                source_type=req_source_type,
                extraction_status=payload.get("extraction_status") or None,
            )
            engine = ArchiveSearchEngine(repo.conn)
            local_results = engine.search(filters)

            wikiran_live_meta: dict[str, Any] | None = None
            should_run_live = (
                include_live
                and bool(raw_query)
                and req_source_type in (None, "", "ALL", "WIKIRAN_DOC", "WIKIRAN_LIVE")
            )
            merged_results = list(local_results)
            if should_run_live:
                live_resp = search_wikiran_live(
                    repo,
                    raw_query,
                    max_pages=live_pages,
                    tab_type="all",
                    leak_source=leak_source_filter,
                    auto_cache=True,
                )
                wikiran_live_meta = {
                    "online": live_resp.get("online", False),
                    "total_label": live_resp.get("total_label", ""),
                    "total_int": live_resp.get("total_int", 0),
                    "facets": live_resp.get("facets", []),
                    "fetched_count": live_resp.get("fetched_count", 0),
                    "cached_new_count": live_resp.get("cached_new_count", 0),
                    "search_url": live_resp.get("search_url", ""),
                    "error": live_resp.get("error", ""),
                }
                existing_urls = {
                    str(r.get("source_url") or "").rstrip("/") for r in merged_results
                }
                live_new_items = [
                    item
                    for item in live_resp.get("results", [])
                    if str(item.get("source_url") or "").rstrip("/") not in existing_urls
                ]
                # Insert live WikIran hits right after OFAC/OpenSanctions matches so they're immediately visible!
                sanction_items = [
                    r for r in merged_results if r.get("record_type") in ("OFAC_SANCTION", "OPENSANCTIONS")
                ]
                other_local_items = [
                    r for r in merged_results if r.get("record_type") not in ("OFAC_SANCTION", "OPENSANCTIONS")
                ]
                if req_source_type == "WIKIRAN_LIVE":
                    merged_results = live_resp.get("results", [])
                else:
                    merged_results = sanction_items + live_new_items + other_local_items

            return {
                "ok": True,
                "results": merged_results,
                "wikiran_live": wikiran_live_meta,
            }

        if action == "set_settings":
            updates: dict[str, str] = payload.get("settings", {})
            for k, v in updates.items():
                repo.set_setting(k, str(v))
            if updates.get("strict_sensitive_exclusion") == "false":
                csv_wb.ensure_unredacted_ledger_dataset()
            return {
                "ok": True,
                "settings": repo.get_settings(),
                "paths": _resolve_configured_paths_dict(paths, repo),
                "schedule": asdict(scheduler.get_schedule_config(repo)),
                "csv_datasets": csv_wb.list_datasets(),
                "active_csv": csv_wb.get_dataset_details(preview_all=True),
            }

        if action == "update_archive":
            engine = CollectionEngine(repo)
            mode = str(payload.get("mode", "")).strip().lower()
            simulate_interrupt = payload.get("simulate_interrupt_after")
            max_items_val = int(payload.get("max_items", 25))
            deep_spider_val = bool(payload.get("deep_spider", True))

            if mode == "discover":
                summary = engine.run_discovery(
                    max_pages_per_hub=int(payload.get("max_pages_per_hub", 8))
                )
            elif mode == "deep_spider":
                summary = engine.run_deep_spider(max_items=max_items_val)
            elif mode == "check_updates":
                summary = engine.run_update_check(max_recheck=max(10, max_items_val))
            else:
                summary = engine.run_incremental_update(
                    max_items=max_items_val,
                    simulate_interrupt_after=int(simulate_interrupt) if simulate_interrupt is not None else None,
                    deep_spider=deep_spider_val,
                )

            ArchiveSearchEngine(repo.conn)._ensure_views_and_fts_synced()
            return {
                "ok": True,
                "mode": mode or "incremental",
                "job": summary,
                "frontier_stats": engine.get_frontier_stats(),
                "storage_volume": compute_storage_volume(paths, repo),
                "stats": repo.get_dashboard_stats(),
                "trends": repo.get_collection_trends(),
                "jobs": repo.list_collection_jobs(),
                "history": repo.list_collection_history(limit=60),
            }

        if action == "crawl_status":
            jobs = repo.list_collection_jobs()
            latest_job = jobs[0] if jobs else None
            recent_history = repo.list_collection_history(limit=8)
            stats = repo.get_dashboard_stats()
            stop_flag = repo.get_settings().get("stop_crawl_requested", "false") == "true"
            return {
                "ok": True,
                "active_job": latest_job,
                "recent_history": recent_history,
                "articles_count": stats["articles_count"],
                "publications_count": stats["publications_count"],
                "stop_requested": stop_flag,
                "frontier_stats": CollectionEngine(repo).get_frontier_stats(),
                "storage_volume": compute_storage_volume(paths, repo),
            }

        if action == "ofac_status":
            return {
                "ok": True,
                "summary": get_ofac_summary(repo.conn, repo.get_settings()),
                "storage_volume": compute_storage_volume(paths, repo),
            }

        if action == "ofac_sync":
            force_flag = bool(payload.get("force", False))
            check_only_flag = bool(payload.get("check_only", False))
            result = sync_ofac_lists(
                repo,
                force=force_flag,
                check_only=check_only_flag,
                exports_dir=paths.exports_dir,
            )
            return {
                **result,
                "storage_volume": compute_storage_volume(paths, repo),
                "jobs": repo.list_collection_jobs(),
                "history": repo.list_collection_history(limit=60),
            }

        if action == "opensanctions_status":
            return {
                "ok": True,
                "summary": get_opensanctions_summary(repo.conn, repo.get_settings()),
                "storage_volume": compute_storage_volume(paths, repo),
            }

        if action == "opensanctions_sync":
            dataset_name = str(payload.get("dataset", "sanctions")).strip() or "sanctions"
            force_flag = bool(payload.get("force", False))
            check_only_flag = bool(payload.get("check_only", False))
            result = sync_opensanctions_dataset(
                repo,
                dataset_name=dataset_name,
                force=force_flag,
                check_only=check_only_flag,
                exports_dir=paths.exports_dir,
            )
            return {
                **result,
                "storage_volume": compute_storage_volume(paths, repo),
                "jobs": repo.list_collection_jobs(),
                "history": repo.list_collection_history(limit=60),
            }

        if action == "wikiran_sync_archives":
            target_slug = str(payload.get("target", "both")).strip() or "both"
            result = sync_wikiran_structured_archives(repo, target=target_slug)
            return {
                **result,
                "storage_volume": compute_storage_volume(paths, repo),
                "wikiran_docs_summary": get_wikiran_documents_summary(repo.conn, repo.get_settings()),
                "jobs": repo.list_collection_jobs(),
                "history": repo.list_collection_history(limit=60),
            }

        if action == "watchlist_template":
            fmt = str(payload.get("format", "xlsx")).strip().lower()
            out_path = (
                generate_watchlist_template_csv(paths.exports_dir)
                if fmt == "csv"
                else generate_watchlist_template_xlsx(paths.exports_dir)
            )
            return {
                "ok": True,
                "path": str(out_path),
                "filename": out_path.name,
            }

        if action == "watchlist_screen":
            result = run_batch_watchlist_screening(
                repo,
                paths.exports_dir,
                file_b64=payload.get("file_b64") or None,
                filename=str(payload.get("filename") or ""),
                raw_text=payload.get("raw_text"),
                include_live_wikiran=bool(payload.get("include_live_wikiran", True)),
                max_live_queries=int(payload.get("max_live_queries", 80)),
            )
            return {
                **result,
                "storage_volume": compute_storage_volume(paths, repo),
                "wikiran_docs_summary": get_wikiran_documents_summary(repo.conn, repo.get_settings()),
            }

        if action == "leaks_catalog":
            refresh_flag = bool(payload.get("refresh", False))
            catalog = get_leak_collections_catalog(repo, refresh_remote=refresh_flag)
            return {
                **catalog,
                "storage_volume": compute_storage_volume(paths, repo),
                "wikiran_docs_summary": get_wikiran_documents_summary(repo.conn, repo.get_settings()),
            }

        if action == "leaks_download":
            slugs_val = payload.get("slugs") or []
            if isinstance(slugs_val, str):
                slugs_val = [s.strip() for s in slugs_val.split(",") if s.strip()]
            result = download_targeted_leaks(
                repo,
                list(slugs_val),
                max_pages_per_leak=int(payload.get("max_pages_per_leak", 10)),
                keyword=str(payload.get("keyword") or ""),
                start_from_page_1=bool(payload.get("start_from_page_1", False)),
            )
            return {
                **result,
                "storage_volume": compute_storage_volume(paths, repo),
                "wikiran_docs_summary": get_wikiran_documents_summary(repo.conn, repo.get_settings()),
                "jobs": repo.list_collection_jobs(),
                "history": repo.list_collection_history(limit=60),
            }

        if action == "stop_crawl":
            repo.set_setting("stop_crawl_requested", "true")
            # Also mark any currently RUNNING job as INTERRUPTED if its process already exited
            running_row = repo.conn.execute(
                "SELECT id FROM collection_jobs WHERE status = 'RUNNING' ORDER BY id DESC LIMIT 1;"
            ).fetchone()
            return {
                "ok": True,
                "stopped": True,
                "running_job_id": int(running_row[0]) if running_row else None,
                "jobs": repo.list_collection_jobs(),
            }

        if action == "resume_job":
            job_id = int(payload["job_id"])
            engine = CollectionEngine(repo)
            summary = engine.resume_job(job_id)
            ArchiveSearchEngine(repo.conn)._ensure_views_and_fts_synced()
            return {
                "ok": True,
                "job": summary,
                "stats": repo.get_dashboard_stats(),
                "trends": repo.get_collection_trends(),
                "jobs": repo.list_collection_jobs(),
                "history": repo.list_collection_history(limit=60),
            }

        if action == "reconnaissance":
            finding = run_reconnaissance()
            md = generate_reconnaissance_markdown(finding)
            return {"ok": True, "finding": asdict(finding), "markdown": md}

        if action == "export":
            fmt = payload.get("format", "xlsx").lower()
            entities = payload.get("entities")
            date_from = payload.get("date_from")
            date_to = payload.get("date_to")
            controller = DesktopController(paths)
            try:
                return controller.run_clerk_export(
                    fmt, entities=entities, date_from=date_from, date_to=date_to
                )
            finally:
                controller.close()

        if action == "backup_create":
            backup_mgr = BackupManager(paths.db_path, paths.backups_dir)
            info = backup_mgr.create_backup()
            return {
                "ok": True,
                "clerk_message": friendly_clerk_message("BACKUP_SUCCESS", lang),
                "backup": info,
                "backups": backup_mgr.list_backups(),
            }

        if action == "backup_full_create":
            backup_mgr = BackupManager(paths.db_path, paths.backups_dir)
            info = backup_mgr.create_full_portable_backup(exports_dir=paths.exports_dir)
            return {
                "ok": True,
                "clerk_message": friendly_clerk_message("BACKUP_SUCCESS", lang),
                "backup": info,
                "backups": backup_mgr.list_backups(),
                "storage_volume": compute_storage_volume(paths, repo),
            }

        if action == "backup_restore":
            backup_mgr = BackupManager(paths.db_path, paths.backups_dir)
            backup_path = str(payload.get("path") or "")
            confirmed = bool(payload.get("confirmed", False))
            if backup_path.lower().endswith(".zip"):
                res = backup_mgr.restore_full_portable_backup(
                    backup_path, exports_dir=paths.exports_dir, confirmed=confirmed
                )
            else:
                res = backup_mgr.restore_backup(backup_path, confirmed=confirmed)
            return {
                "ok": True,
                "clerk_message": friendly_clerk_message("BACKUP_RESTORE_SUCCESS", lang),
                "restore": res,
                "backups": backup_mgr.list_backups(),
                "storage_volume": compute_storage_volume(paths, repo),
            }

        if action == "backup_full_restore":
            backup_mgr = BackupManager(paths.db_path, paths.backups_dir)
            backup_path = str(payload.get("path") or "")
            confirmed = bool(payload.get("confirmed", False))
            res = backup_mgr.restore_full_portable_backup(
                backup_path, exports_dir=paths.exports_dir, confirmed=confirmed
            )
            return {
                "ok": True,
                "clerk_message": friendly_clerk_message("BACKUP_RESTORE_SUCCESS", lang),
                "restore": res,
                "backups": backup_mgr.list_backups(),
                "storage_volume": compute_storage_volume(paths, repo),
            }

        if action == "integrity_check":
            ok, msg = verify_database_integrity(paths.db_path)
            return {"ok": True, "verified": ok, "message": msg}

        if action == "windows_portable_zip":
            from .packaging.windows_bundle import build_windows_portable_zip

            project_root = Path(__file__).resolve().parent.parent
            zip_path = build_windows_portable_zip(project_root, paths, repo, include_database=True)
            return {
                "ok": True,
                "path": str(zip_path),
                "filename": zip_path.name,
                "size_bytes": zip_path.stat().st_size,
            }

        if action == "windows_portable_lite_zip":
            from .packaging.windows_bundle import build_windows_portable_lite_zip

            project_root = Path(__file__).resolve().parent.parent
            zip_path = build_windows_portable_lite_zip(project_root, paths, repo)
            return {
                "ok": True,
                "path": str(zip_path),
                "filename": zip_path.name,
                "size_bytes": zip_path.stat().st_size,
            }

        if action == "windows_package":
            from .packaging.windows_bundle import build_windows11_clerk_zip

            project_root = Path(__file__).resolve().parent.parent
            zip_path = build_windows11_clerk_zip(project_root, paths, repo)
            return {
                "ok": True,
                "path": str(zip_path),
                "filename": zip_path.name,
                "size_bytes": zip_path.stat().st_size,
            }

        if action in ("windows_installer_exe", "windows_installer_bat"):
            from .packaging.windows_bundle import build_windows11_setup_exe

            project_root = Path(__file__).resolve().parent.parent
            exe_path = build_windows11_setup_exe(project_root, paths, repo)
            return {
                "ok": True,
                "path": str(exe_path),
                "filename": exe_path.name,
                "size_bytes": exe_path.stat().st_size,
            }

        if action == "windows_app_html":
            from .packaging.windows_bundle import write_standalone_ready_html_file

            project_root = Path(__file__).resolve().parent.parent
            html_path = write_standalone_ready_html_file(paths, repo, project_root=project_root)
            return {
                "ok": True,
                "path": str(html_path),
                "filename": html_path.name,
                "size_bytes": html_path.stat().st_size,
            }

        return {"ok": False, "error": f"Unknown action: {action}"}
    finally:
        repo.conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WikIran Archive — Windows 11 Desktop Application")
    parser.add_argument("--gui", action="store_true", help="Launch PySide6 Desktop GUI")
    parser.add_argument("--init-db", action="store_true", help="Initialize and seed SQLite database")
    parser.add_argument("--recon", action="store_true", help="Run website reconnaissance")
    parser.add_argument("--api", type=str, help="Execute JSON API action for local bridge")
    parser.add_argument("--payload", type=str, default="{}", help="JSON payload for --api")
    parser.add_argument("--payload-file", type=str, default=None, help="Path to JSON payload file for --api")
    parser.add_argument("--data-dir", type=str, default=None, help="Custom data directory override")
    args = parser.parse_args(argv)

    if args.api:
        raw_payload = args.payload
        if args.payload_file:
            raw_payload = Path(args.payload_file).read_text(encoding="utf-8")
        result = handle_api_command(args.api, raw_payload, args.data_dir)
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if args.init_db:
        paths, repo = ensure_initialized(args.data_dir)
        stats = repo.get_dashboard_stats()
        repo.conn.close()
        print(json.dumps({"db_path": str(paths.db_path), "stats": stats}, indent=2))
        return 0

    if args.recon:
        finding = run_reconnaissance()
        print(generate_reconnaissance_markdown(finding))
        return 0

    paths, repo = ensure_initialized(args.data_dir)
    repo.conn.close()
    return launch_pyside6_gui(paths)


if __name__ == "__main__":
    sys.exit(main())
