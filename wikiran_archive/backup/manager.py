"""
SQLite-safe backup and restore manager.
Supports:
- Online atomic backups using sqlite3.Connection.backup()
- Automatic daily backup with 14-day retention rotation
- Pre-backup and pre-restore PRAGMA integrity_check verification
- Protection against overwriting the only valid backup
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..database.connection import get_connection, verify_database_integrity
from ..database.migrations import run_migrations


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

    def create_full_portable_backup(
        self,
        exports_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        """
        Build a complete, portable `.zip` backup package containing:
          1. Online-consistent snapshot of `data/wikiran_archive.db` (WikIran + OFAC + OpenSanctions + FTS5 + CSV + settings)
          2. Raw downloaded OFAC CSVs (`exports/ofac_raw/*`) and OpenSanctions CSVs (`exports/opensanctions_raw/*`)
          3. `manifest.json` with SHA-256 checksum & exact record counts
        Designed so 1 PC downloads once and the other 4 PCs restore everything offline with zero re-downloading.
        """
        is_valid, msg = verify_database_integrity(self.db_path)
        if not is_valid:
            raise RuntimeError(f"Source database failed integrity check before full backup: {msg}")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        zip_name = f"WikIran_Full_Portable_Backup_{timestamp}.zip"
        zip_path = self.backups_dir / zip_name

        with tempfile.TemporaryDirectory(prefix="wikiran_full_bkp_") as tmp_dir:
            tmp_db = Path(tmp_dir) / "wikiran_archive.db"
            src_conn = get_connection(self.db_path)
            dst_conn = sqlite3.connect(str(tmp_db))
            try:
                with dst_conn:
                    src_conn.backup(dst_conn)
            finally:
                dst_conn.close()
                src_conn.close()

            snap_ok, snap_msg = verify_database_integrity(tmp_db)
            if not snap_ok:
                raise RuntimeError(f"Snapshot database failed integrity check: {snap_msg}")

            # Compute SHA-256 and exact record counts from snapshot
            sha256_h = hashlib.sha256()
            with tmp_db.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    sha256_h.update(chunk)
            db_sha256 = sha256_h.hexdigest()

            counts: dict[str, int] = {}
            c_conn = sqlite3.connect(str(tmp_db))
            try:
                for tbl in (
                    "articles",
                    "publications",
                    "organizations",
                    "ofac_entities",
                    "opensanctions_entities",
                    "imported_csv_rows",
                    "crawl_frontier",
                ):
                    try:
                        counts[tbl] = int(c_conn.execute(f"SELECT COUNT(*) FROM {tbl};").fetchone()[0])
                    except Exception:
                        counts[tbl] = 0
            finally:
                c_conn.close()

            included_raw_files: list[str] = []
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                zf.write(tmp_db, "data/wikiran_archive.db")

                if exports_dir is not None:
                    exp_root = Path(exports_dir)
                    for sub_name in ("ofac_raw", "opensanctions_raw"):
                        sub_dir = exp_root / sub_name
                        if sub_dir.exists() and sub_dir.is_dir():
                            for item in sorted(sub_dir.rglob("*")):
                                if item.is_file():
                                    arc_name = f"exports/{sub_name}/{item.relative_to(sub_dir).as_posix()}"
                                    zf.write(item, arc_name)
                                    included_raw_files.append(arc_name)

                manifest = {
                    "format": "WikIranArchive-FullPortableBackup",
                    "format_version": 2,
                    "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "db_sha256": db_sha256,
                    "db_size_bytes": tmp_db.stat().st_size,
                    "counts": counts,
                    "included_raw_files": included_raw_files,
                }
                zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        return {
            "filename": zip_name,
            "path": str(zip_path),
            "size_bytes": zip_path.stat().st_size,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "integrity_verified": True,
            "counts": counts,
            "included_raw_files_count": len(included_raw_files),
            "db_sha256": db_sha256,
        }

    def restore_full_portable_backup(
        self,
        zip_file_path: str | Path,
        exports_dir: str | Path | None = None,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """
        Restore a complete portable `.zip` backup (or a single `.db` backup) onto this PC:
        - Extracts and verifies SQLite `PRAGMA integrity_check` and optional SHA-256 from `manifest.json`
        - Creates an automatic pre-restore safety snapshot first
        - Restores the full database (WikIran + OFAC + OpenSanctions + FTS5 + settings) and raw CSV folders
        """
        if not confirmed:
            raise PermissionError("Explicit user confirmation is required before restoring a full backup.")

        src_path = Path(zip_file_path)
        if not src_path.exists():
            raise FileNotFoundError(f"Backup archive not found: {src_path}")

        if src_path.suffix.lower() == ".db":
            return self.restore_backup(src_path, confirmed=True)

        if not zipfile.is_zipfile(src_path):
            raise ValueError("Uploaded file is not a valid WikIran Full Backup (.zip) or SQLite (.db) file.")

        with tempfile.TemporaryDirectory(prefix="wikiran_restore_") as tmp_dir:
            tmp_root = Path(tmp_dir)
            with zipfile.ZipFile(src_path, "r") as zf:
                names = zf.namelist()
                db_member = next(
                    (n for n in names if n == "data/wikiran_archive.db" or n.endswith(".db")),
                    None,
                )
                if not db_member:
                    raise ValueError("Backup ZIP does not contain a valid SQLite database (.db).")

                extracted_db = tmp_root / "restored.db"
                with zf.open(db_member) as src_f, extracted_db.open("wb") as dst_f:
                    shutil.copyfileobj(src_f, dst_f)

                manifest: dict[str, Any] = {}
                if "manifest.json" in names:
                    try:
                        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
                    except Exception:
                        manifest = {}

                # Verify SHA-256 if recorded in manifest
                expected_sha = str(manifest.get("db_sha256") or "").strip()
                if expected_sha:
                    actual_h = hashlib.sha256()
                    with extracted_db.open("rb") as f:
                        for chunk in iter(lambda: f.read(1024 * 1024), b""):
                            actual_h.update(chunk)
                    if actual_h.hexdigest() != expected_sha:
                        raise ValueError("Backup database SHA-256 checksum mismatch; archive may be corrupted.")

                ok, msg = verify_database_integrity(extracted_db)
                if not ok:
                    raise ValueError(f"Backup database failed SQLite integrity check: {msg}")

                # Take safety snapshot of current DB first
                if self.db_path.exists():
                    curr_ok, _ = verify_database_integrity(self.db_path)
                    if curr_ok:
                        self.create_backup(prefix="pre_restore_safety")

                # Perform online SQLite backup copy into active DB path
                src_conn = sqlite3.connect(str(extracted_db))
                dst_conn = sqlite3.connect(str(self.db_path))
                try:
                    with dst_conn:
                        src_conn.backup(dst_conn)
                finally:
                    dst_conn.close()
                    src_conn.close()

                # Ensure idempotent migrations on restored DB
                mig_conn = get_connection(self.db_path)
                try:
                    run_migrations(mig_conn)
                finally:
                    mig_conn.close()

                # Restore raw OFAC / OpenSanctions files if present in ZIP
                restored_raw_count = 0
                if exports_dir is not None:
                    exp_root = Path(exports_dir)
                    for member in names:
                        if member.startswith("exports/ofac_raw/") or member.startswith("exports/opensanctions_raw/"):
                            if member.endswith("/"):
                                continue
                            rel = Path(member).relative_to("exports")
                            # Prevent path traversal
                            if ".." in rel.parts:
                                continue
                            dest_file = exp_root / rel
                            dest_file.parent.mkdir(parents=True, exist_ok=True)
                            with zf.open(member) as src_f, dest_file.open("wb") as dst_f:
                                shutil.copyfileobj(src_f, dst_f)
                            restored_raw_count += 1

        final_ok, final_msg = verify_database_integrity(self.db_path)
        if not final_ok:
            raise RuntimeError(f"Database failed integrity check after full restore: {final_msg}")

        return {
            "restored_from": src_path.name,
            "restored_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "integrity_verified": True,
            "restored_raw_files": restored_raw_count,
            "manifest": manifest,
            "message": final_msg,
        }

    def list_backups(self) -> list[dict[str, Any]]:
        """List all available backup files (.zip full backups and .db snapshots) sorted newest first."""
        files = sorted(
            list(self.backups_dir.glob("*.zip")) + list(self.backups_dir.glob("*.db")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        items: list[dict[str, Any]] = []
        for f in files:
            is_zip = f.suffix.lower() == ".zip"
            ok = zipfile.is_zipfile(f) if is_zip else verify_database_integrity(f)[0]
            dt = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            items.append(
                {
                    "filename": f.name,
                    "path": str(f),
                    "backup_type": "FULL_PORTABLE_ZIP" if is_zip else "SQLITE_SNAPSHOT",
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
