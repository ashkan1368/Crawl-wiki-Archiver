"""SQLite connection factory with WAL mode and foreign key enforcement."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Create a configured SQLite connection with foreign keys and Row factory."""
    path_str = str(db_path)
    conn = sqlite3.connect(path_str, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    if path_str != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def verify_database_integrity(db_path: str | Path) -> tuple[bool, str]:
    """Run PRAGMA integrity_check and foreign_key_check on a SQLite database."""
    try:
        conn = get_connection(db_path)
        try:
            row = conn.execute("PRAGMA integrity_check;").fetchone()
            integrity_msg = row[0] if row else "unknown"
            fk_violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
            if integrity_msg == "ok" and not fk_violations:
                return True, "Database integrity and foreign keys verified (ok)."
            return False, f"Integrity: {integrity_msg}, FK violations: {len(fk_violations)}"
        finally:
            conn.close()
    except Exception as exc:
        return False, f"Integrity check error: {exc}"
