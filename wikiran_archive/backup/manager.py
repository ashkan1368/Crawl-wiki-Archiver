"""
SQLite-safe backup and restore manager.
Supports:
- Online atomic backups using sqlite3.Connection.backup()
- Automatic daily backup with 14-day retention rotation
- Pre-backup and pre-restore PRAGMA integrity_check verification
- Protection against overwriting the only valid backup
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..database.connection import get_connection, verify_database_integrity


class BackupManager:
    """Manages SQLite-safe backups, 14-day retention, integrity checks, and verified restores."""

    def __init__(self, db_path: str | Path, backups_dir: str | Path, retention_days: int = 14) -> None:
        self.db_path = Path(db_path)
        self.backups_dir = Path(backups_dir)
        self.retention_days = max(1, int(retention_days))
        self.backups_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, destination_path: str | Path | None = None, prefix: str = "wikiran_backup") -> dict[str, Any]:
        """
        Create a verified SQLite backup using the SQLite Online Backup API.
        Never overwrites the only valid backup.
        """
        is_valid, msg = verify_database_integrity(self.db_path)
        if not is_valid:
            raise RuntimeError(f"Source database failed integrity check before backup: {msg}")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        if destination_path is not None:
            target = Path(destination_path)
            if target.is_dir():
                target = target / f"{prefix}_{timestamp}.db"
        else:
            target = self.backups_dir / f"{prefix}_{timestamp}.db"

        target.parent.mkdir(parents=True, exist_ok=True)

        # Avoid overwriting an existing valid backup file at the exact same path
        if target.exists():
            target = target.with_name(f"{target.stem}_{timestamp}{target.suffix}")

        src_conn = get_connection(self.db_path)
        dst_conn = sqlite3.connect(str(target))
        try:
            with dst_conn:
                src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
            src_conn.close()

        backup_ok, backup_msg = verify_database_integrity(target)
        if not backup_ok:
            target.unlink(missing_ok=True)
            raise RuntimeError(f"Created backup failed verification and was removed: {backup_msg}")

        self._enforce_retention()

        return {
            "filename": target.name,
            "path": str(target),
            "size_bytes": target.stat().st_size,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "integrity_verified": True,
            "message": backup_msg,
        }

    def restore_backup(self, backup_file_path: str | Path, confirmed: bool = False) -> dict[str, Any]:
        """
        Restore the active database from a verified backup file.
        Requires explicit confirmation (confirmed=True).
        Automatically creates a pre-restore safety snapshot first.
        """
        if not confirmed:
            raise PermissionError("Explicit user confirmation is required before restoring a backup.")

        source_backup = Path(backup_file_path)
        if not source_backup.exists():
            raise FileNotFoundError(f"Backup file not found: {source_backup}")

        backup_ok, backup_msg = verify_database_integrity(source_backup)
        if not backup_ok:
            raise ValueError(f"Selected backup file failed integrity verification: {backup_msg}")

        # Create a pre-restore safety backup if current DB is valid
        if self.db_path.exists():
            curr_ok, _ = verify_database_integrity(self.db_path)
            if curr_ok:
                self.create_backup(prefix="pre_restore_safety")

        src_conn = sqlite3.connect(str(source_backup))
        dst_conn = sqlite3.connect(str(self.db_path))
        try:
            with dst_conn:
                src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
            src_conn.close()

        restored_ok, restored_msg = verify_database_integrity(self.db_path)
        if not restored_ok:
            raise RuntimeError(f"Database failed integrity check after restore: {restored_msg}")

        return {
            "restored_from": str(source_backup),
            "restored_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "integrity_verified": True,
            "message": restored_msg,
        }

    def list_backups(self) -> list[dict[str, Any]]:
        """List all available backup files sorted newest first."""
        files = sorted(
            self.backups_dir.glob("*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        items: list[dict[str, Any]] = []
        for f in files:
            ok, _ = verify_database_integrity(f)
            dt = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            items.append(
                {
                    "filename": f.name,
                    "path": str(f),
                    "size_bytes": f.stat().st_size,
                    "created_at": dt,
                    "integrity_verified": ok,
                }
            )
        return items

    def _enforce_retention(self) -> None:
        """Retain the latest N daily backups (default 14), never deleting the last valid backup."""
        files = sorted(
            self.backups_dir.glob("wikiran_backup_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if len(files) <= self.retention_days:
            return
        for old_file in files[self.retention_days :]:
            old_file.unlink(missing_ok=True)
