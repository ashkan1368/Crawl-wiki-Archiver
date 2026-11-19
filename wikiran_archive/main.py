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
from .collector.reconnaissance import generate_reconnaissance_markdown, run_reconnaissance
from .collector.scheduler import ScheduledCollectionRunner
from .config.settings import AppPaths, resolve_app_paths
from .database.connection import get_connection, verify_database_integrity
from .database.migrations import run_migrations
from .database.repository import ArchiveRepository
from .database.seed import seed_verified_public_archive
from .export.csv_converter import CsvSpreadsheetWorkbench
from .export.exporters import ArchiveExporter
from .logging_utils.logger import friendly_clerk_message, read_diagnostic_logs, setup_logger
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
            filters = SearchFilters(
                query=payload.get("query", ""),
                date_from=payload.get("date_from") or None,
                date_to=payload.get("date_to") or None,
                category_slug=payload.get("category_slug") or None,
                organization_name=payload.get("organization_name") or None,
                source_type=payload.get("source_type") or None,
                extraction_status=payload.get("extraction_status") or None,
            )
            engine = ArchiveSearchEngine(repo.conn)
            return {"ok": True, "results": engine.search(filters)}

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
            simulate_interrupt = payload.get("simulate_interrupt_after")
            max_items_val = int(payload.get("max_items", 12))
            deep_spider_val = bool(payload.get("deep_spider", True))
            summary = engine.run_incremental_update(
                max_items=max_items_val,
                simulate_interrupt_after=int(simulate_interrupt) if simulate_interrupt is not None else None,
                deep_spider=deep_spider_val,
            )
            ArchiveSearchEngine(repo.conn)._ensure_views_and_fts_synced()
            return {
                "ok": True,
                "job": summary,
                "stats": repo.get_dashboard_stats(),
                "trends": repo.get_collection_trends(),
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
            controller = DesktopController(paths)
            try:
                return controller.run_clerk_export(fmt, entities=entities)
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

        if action == "backup_restore":
            backup_mgr = BackupManager(paths.db_path, paths.backups_dir)
            backup_path = payload.get("path")
            confirmed = bool(payload.get("confirmed", False))
            res = backup_mgr.restore_backup(backup_path, confirmed=confirmed)
            return {
                "ok": True,
                "clerk_message": friendly_clerk_message("BACKUP_RESTORE_SUCCESS", lang),
                "restore": res,
                "backups": backup_mgr.list_backups(),
            }

        if action == "integrity_check":
            ok, msg = verify_database_integrity(paths.db_path)
            return {"ok": True, "verified": ok, "message": msg}

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
    parser.add_argument("--data-dir", type=str, default=None, help="Custom data directory override")
    args = parser.parse_args(argv)

    if args.api:
        result = handle_api_command(args.api, args.payload, args.data_dir)
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
