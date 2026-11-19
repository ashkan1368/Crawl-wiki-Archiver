"""Configuration and external application data directory resolution."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    """Application paths stored strictly outside the installation directory."""

    base_dir: Path
    data_dir: Path
    db_path: Path
    backups_dir: Path
    exports_dir: Path
    logs_dir: Path


def resolve_app_paths(custom_base_dir: str | Path | None = None) -> AppPaths:
    """
    Resolve application data directories outside the installation folder.
    On Windows 11, uses %LOCALAPPDATA%\\WikIranArchive.
    Supports override via WIKIRAN_DATA_DIR environment variable or explicit path.
    """
    env_override = os.environ.get("WIKIRAN_DATA_DIR")
    if custom_base_dir is not None:
        base = Path(custom_base_dir).expanduser().resolve()
    elif env_override:
        base = Path(env_override).expanduser().resolve()
    elif platform.system() == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base = Path(local_app_data) / "WikIranArchive"
        else:
            base = Path.home() / "AppData" / "Local" / "WikIranArchive"
    else:
        base = Path.home() / ".local" / "share" / "WikIranArchive"

    data_dir = base / "data"
    backups_dir = base / "backups"
    exports_dir = base / "exports"
    logs_dir = base / "logs"

    for folder in (base, data_dir, backups_dir, exports_dir, logs_dir):
        folder.mkdir(parents=True, exist_ok=True)

    return AppPaths(
        base_dir=base,
        data_dir=data_dir,
        db_path=data_dir / "wikiran_archive.db",
        backups_dir=backups_dir,
        exports_dir=exports_dir,
        logs_dir=logs_dir,
    )


DEFAULT_SETTINGS: dict[str, str] = {
    "ui_language": "en",
    "default_view_mode": "clerk",
    "source_base_url": "https://wikiran.org",
    "user_agent": "WikIranArchiveBot/1.0 (+https://wikiran.org; Public Research Archive)",
    "request_delay_seconds": "1.5",
    "request_timeout_seconds": "15",
    "max_retries": "3",
    "backoff_factor": "2.0",
    "respect_robots_txt": "true",
    "auto_daily_backup": "true",
    "backup_retention_days": "14",
    "max_pages_per_run": "10",
    "strict_sensitive_exclusion": "false",
    "custom_storage_path": r"C:\WikIranArchive",
    "schedule_enabled": "true",
    "schedule_frequency": "daily",
    "schedule_time_utc": "02:00",
    "schedule_day_of_week": "sunday",
    "schedule_max_items": "6",
    "schedule_last_run_at": "2026-11-18T02:00:00Z",
}
