"""Versioned SQLite database migrations including all 15 normalized tables and FTS5 index."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from ..config.settings import DEFAULT_SETTINGS

MIGRATIONS: list[tuple[int, str, str]] = [
    (
        1,
        "initial_normalized_schema_v1",
        """
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            source_type TEXT NOT NULL,
            base_url TEXT NOT NULL,
            source_url TEXT NOT NULL,
            original_pub_id TEXT,
            robots_status TEXT NOT NULL DEFAULT 'PERMITTED',
            retrieved_at TEXT NOT NULL,
            last_verified_at TEXT NOT NULL,
            extraction_status TEXT NOT NULL DEFAULT 'VERIFIED',
            content_hash TEXT NOT NULL,
            record_version INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_pub_id TEXT UNIQUE,
            title TEXT NOT NULL,
            subtitle TEXT,
            author TEXT NOT NULL DEFAULT 'WikIran Editorial',
            publication_date TEXT NOT NULL,
            raw_date_text TEXT,
            summary TEXT NOT NULL,
            editorial_content TEXT NOT NULL,
            source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
            source_url TEXT NOT NULL UNIQUE,
            retrieved_at TEXT NOT NULL,
            last_verified_at TEXT NOT NULL,
            extraction_status TEXT NOT NULL DEFAULT 'VERIFIED',
            content_hash TEXT NOT NULL,
            record_version INTEGER NOT NULL DEFAULT 1
        );

        CREATE INDEX IF NOT EXISTS idx_articles_pub_date ON articles(publication_date);
        CREATE INDEX IF NOT EXISTS idx_articles_source_id ON articles(source_id);
        CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(extraction_status);

        CREATE TABLE IF NOT EXISTS publications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_pub_id TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            native_title TEXT,
            publication_date TEXT NOT NULL,
            raw_date_text TEXT,
            description TEXT NOT NULL,
            source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
            source_url TEXT NOT NULL UNIQUE,
            retrieved_at TEXT NOT NULL,
            last_verified_at TEXT NOT NULL,
            extraction_status TEXT NOT NULL DEFAULT 'VERIFIED',
            content_hash TEXT NOT NULL,
            record_version INTEGER NOT NULL DEFAULT 1
        );

        CREATE INDEX IF NOT EXISTS idx_publications_pub_date ON publications(publication_date);
        CREATE INDEX IF NOT EXISTS idx_publications_source_id ON publications(source_id);

        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            native_name TEXT,
            acronym TEXT,
            org_type TEXT NOT NULL DEFAULT 'STATE_INSTITUTION',
            description TEXT,
            source_url TEXT NOT NULL,
            original_pub_id TEXT,
            retrieved_at TEXT NOT NULL,
            last_verified_at TEXT NOT NULL,
            extraction_status TEXT NOT NULL DEFAULT 'VERIFIED',
            content_hash TEXT NOT NULL,
            record_version INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            entity_type TEXT NOT NULL DEFAULT 'ORGANIZATION',
            organization_id INTEGER REFERENCES organizations(id) ON DELETE SET NULL,
            description TEXT,
            source_url TEXT NOT NULL,
            original_pub_id TEXT,
            retrieved_at TEXT NOT NULL,
            last_verified_at TEXT NOT NULL,
            extraction_status TEXT NOT NULL DEFAULT 'VERIFIED',
            content_hash TEXT NOT NULL,
            record_version INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE,
            name_en TEXT NOT NULL,
            name_fa TEXT NOT NULL,
            description TEXT,
            source_url TEXT NOT NULL DEFAULT 'https://wikiran.org/',
            original_pub_id TEXT,
            retrieved_at TEXT NOT NULL,
            last_verified_at TEXT NOT NULL,
            extraction_status TEXT NOT NULL DEFAULT 'VERIFIED',
            content_hash TEXT NOT NULL,
            record_version INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            source_url TEXT NOT NULL DEFAULT 'https://wikiran.org/',
            original_pub_id TEXT,
            retrieved_at TEXT NOT NULL,
            last_verified_at TEXT NOT NULL,
            extraction_status TEXT NOT NULL DEFAULT 'VERIFIED',
            content_hash TEXT NOT NULL DEFAULT '',
            record_version INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS article_entities (
            article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
            entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            organization_id INTEGER REFERENCES organizations(id) ON DELETE SET NULL,
            relevance_note TEXT,
            PRIMARY KEY (article_id, entity_id)
        );

        CREATE TABLE IF NOT EXISTS article_categories (
            article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
            category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            PRIMARY KEY (article_id, category_id)
        );

        CREATE TABLE IF NOT EXISTS publication_categories (
            publication_id INTEGER NOT NULL REFERENCES publications(id) ON DELETE CASCADE,
            category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            PRIMARY KEY (publication_id, category_id)
        );

        CREATE TABLE IF NOT EXISTS article_tags (
            article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
            tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY (article_id, tag_id)
        );

        CREATE TABLE IF NOT EXISTS file_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            publication_id INTEGER NOT NULL REFERENCES publications(id) ON DELETE CASCADE,
            data_type TEXT NOT NULL,
            reported_count_label TEXT NOT NULL,
            safety_policy_applied TEXT NOT NULL DEFAULT 'METADATA_ONLY_SENSITIVE_EXCLUDED',
            source_url TEXT NOT NULL,
            original_pub_id TEXT,
            retrieved_at TEXT NOT NULL,
            last_verified_at TEXT NOT NULL,
            extraction_status TEXT NOT NULL DEFAULT 'VERIFIED',
            content_hash TEXT NOT NULL,
            record_version INTEGER NOT NULL DEFAULT 1,
            UNIQUE(publication_id, data_type)
        );

        CREATE TABLE IF NOT EXISTS collection_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_uuid TEXT NOT NULL UNIQUE,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            total_discovered INTEGER NOT NULL DEFAULT 0,
            processed_count INTEGER NOT NULL DEFAULT 0,
            new_records_count INTEGER NOT NULL DEFAULT 0,
            updated_records_count INTEGER NOT NULL DEFAULT 0,
            skipped_unchanged_count INTEGER NOT NULL DEFAULT 0,
            blocked_sensitive_count INTEGER NOT NULL DEFAULT 0,
            failed_count INTEGER NOT NULL DEFAULT 0,
            checkpoint_data TEXT NOT NULL DEFAULT '{}',
            error_summary TEXT
        );

        CREATE TABLE IF NOT EXISTS collection_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL REFERENCES collection_jobs(id) ON DELETE CASCADE,
            target_url TEXT NOT NULL,
            record_type TEXT NOT NULL,
            http_status INTEGER,
            action_taken TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            message TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_collection_history_job_id ON collection_history(job_id);

        CREATE TABLE IF NOT EXISTS change_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            source_url TEXT NOT NULL,
            previous_version INTEGER NOT NULL,
            new_version INTEGER NOT NULL,
            previous_hash TEXT NOT NULL,
            new_hash TEXT NOT NULL,
            changed_at TEXT NOT NULL,
            change_summary TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS application_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """,
    ),
    (
        2,
        "fts5_full_text_search_index_v2",
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS fts_archive USING fts5(
            record_type,
            record_id UNINDEXED,
            title,
            editorial_content,
            summary,
            organization_names,
            entity_names,
            category_names,
            tag_names,
            publication_date,
            source_url UNINDEXED,
            tokenize='unicode61 remove_diacritics 2'
        );
        """,
    ),
    (
        3,
        "csv_spreadsheet_workbench_v3",
        """
        CREATE TABLE IF NOT EXISTS imported_csv_datasets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_name TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            headers_json TEXT NOT NULL,
            row_count INTEGER NOT NULL DEFAULT 0,
            xlsx_export_path TEXT,
            source_url TEXT NOT NULL DEFAULT 'local://csv-import',
            retrieved_at TEXT NOT NULL,
            last_verified_at TEXT NOT NULL,
            extraction_status TEXT NOT NULL DEFAULT 'VERIFIED',
            content_hash TEXT NOT NULL,
            record_version INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS imported_csv_rows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER NOT NULL REFERENCES imported_csv_datasets(id) ON DELETE CASCADE,
            row_number INTEGER NOT NULL,
            row_json TEXT NOT NULL,
            searchable_text TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_imported_csv_rows_dataset ON imported_csv_rows(dataset_id);

        CREATE VIEW IF NOT EXISTS csv_row_content AS
        SELECT
            r.id,
            r.dataset_id,
            r.row_number,
            r.row_json,
            r.searchable_text,
            d.dataset_name,
            d.original_filename,
            d.xlsx_export_path,
            d.source_url,
            d.retrieved_at,
            d.extraction_status,
            d.record_version
        FROM imported_csv_rows r
        JOIN imported_csv_datasets d ON d.id = r.dataset_id;

        CREATE VIEW IF NOT EXISTS file_metadata AS
        SELECT
            fi.id,
            fi.publication_id,
            fi.data_type,
            fi.reported_count_label,
            fi.safety_policy_applied,
            fi.source_url,
            fi.original_pub_id,
            fi.retrieved_at,
            fi.last_verified_at,
            fi.extraction_status,
            fi.content_hash,
            fi.record_version,
            p.title AS publication_title,
            p.publication_date AS publication_date
        FROM file_inventory fi
        LEFT JOIN publications p ON p.id = fi.publication_id;
        """,
    ),
]


def run_migrations(conn: sqlite3.Connection) -> list[int]:
    """
    Execute all pending versioned migrations in order and initialize default settings.
    Returns list of newly applied migration version numbers.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        );
        """
    )
    applied_rows = conn.execute("SELECT version FROM schema_migrations;").fetchall()
    applied_versions = {int(r["version"]) for r in applied_rows}

    newly_applied: list[int] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for version, name, sql_script in MIGRATIONS:
        if version not in applied_versions:
            conn.executescript(sql_script)
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute(
                "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?);",
                (version, name, now_iso),
            )
            newly_applied.append(version)

    # Ensure unified FTS5 JOIN views exist even on previously migrated databases
    conn.executescript(
        """
        CREATE VIEW IF NOT EXISTS csv_row_content AS
        SELECT
            r.id,
            r.dataset_id,
            r.row_number,
            r.row_json,
            r.searchable_text,
            d.dataset_name,
            d.original_filename,
            d.xlsx_export_path,
            d.source_url,
            d.retrieved_at,
            d.extraction_status,
            d.record_version
        FROM imported_csv_rows r
        JOIN imported_csv_datasets d ON d.id = r.dataset_id;

        CREATE VIEW IF NOT EXISTS file_metadata AS
        SELECT
            fi.id,
            fi.publication_id,
            fi.data_type,
            fi.reported_count_label,
            fi.safety_policy_applied,
            fi.source_url,
            fi.original_pub_id,
            fi.retrieved_at,
            fi.last_verified_at,
            fi.extraction_status,
            fi.content_hash,
            fi.record_version,
            p.title AS publication_title,
            p.publication_date AS publication_date
        FROM file_inventory fi
        LEFT JOIN publications p ON p.id = fi.publication_id;
        """
    )
    conn.execute("PRAGMA foreign_keys = ON;")

    for key, val in DEFAULT_SETTINGS.items():
        conn.execute(
            """
            INSERT OR IGNORE INTO application_settings (key, value, updated_at)
            VALUES (?, ?, ?);
            """,
            (key, val, now_iso),
        )

    conn.commit()
    return newly_applied
