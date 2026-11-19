"""
Offline universal full-text search powered by a single SQLite FTS5 JOIN query across all tables:
articles, publications, csv_row_content (imported_csv_rows + imported_csv_datasets),
file_metadata (file_inventory + publications), and organizations/entities.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Any


@dataclass
class SearchFilters:
    """Optional filters for narrowing offline full-text search results."""

    query: str = ""
    date_from: str | None = None
    date_to: str | None = None
    category_slug: str | None = None
    organization_name: str | None = None
    source_type: str | None = None  # 'ARTICLE', 'PUBLICATION', 'CSV_ROW', 'FILE_INVENTORY', 'ENTITY', or None for all
    extraction_status: str | None = None


def _build_safe_fts_query(raw_query: str) -> str:
    """Sanitize user input into a safe FTS5 prefix/token query."""
    tokens = re.findall(r"[\w\u0600-\u06FF]+", raw_query, flags=re.UNICODE)
    if not tokens:
        return ""
    return " AND ".join(f'"{t}"*' for t in tokens)


UNIFIED_FTS5_JOIN_SQL = """
WITH unified_joined_records AS (
    SELECT
        fts_archive.record_type AS record_type,
        CAST(fts_archive.record_id AS INTEGER) AS id,
        {rank_expr} AS fts_rank,
        CASE
            WHEN fts_archive.record_type = 'ARTICLE' THEN a.title
            WHEN fts_archive.record_type = 'PUBLICATION' THEN p.title
            WHEN fts_archive.record_type = 'CSV_ROW' THEN '[' || csv_row_content.dataset_name || ' — Row #' || csv_row_content.row_number || ']'
            WHEN fts_archive.record_type = 'FILE_INVENTORY' THEN COALESCE(file_metadata.publication_title, 'Archive File') || ' — ' || file_metadata.data_type
            WHEN fts_archive.record_type = 'ENTITY' THEN o.name || ' (' || COALESCE(NULLIF(o.acronym, ''), o.org_type) || ')'
            ELSE fts_archive.title
        END AS title,
        CASE
            WHEN fts_archive.record_type = 'PUBLICATION' THEN COALESCE(p.native_title, '')
            WHEN fts_archive.record_type = 'ENTITY' THEN COALESCE(o.native_name, '')
            ELSE ''
        END AS native_title,
        CASE
            WHEN fts_archive.record_type = 'ARTICLE' THEN a.summary
            WHEN fts_archive.record_type = 'PUBLICATION' THEN p.description
            WHEN fts_archive.record_type = 'CSV_ROW' THEN csv_row_content.searchable_text
            WHEN fts_archive.record_type = 'FILE_INVENTORY' THEN file_metadata.reported_count_label || ' | ' || COALESCE(file_metadata.safety_policy_applied, '')
            WHEN fts_archive.record_type = 'ENTITY' THEN COALESCE(o.description, fts_archive.summary)
            ELSE fts_archive.summary
        END AS short_description,
        CASE
            WHEN fts_archive.record_type = 'ARTICLE' THEN a.editorial_content
            WHEN fts_archive.record_type = 'PUBLICATION' THEN p.description
            WHEN fts_archive.record_type = 'CSV_ROW' THEN csv_row_content.searchable_text
            WHEN fts_archive.record_type = 'FILE_INVENTORY' THEN 'Inventory Type: ' || file_metadata.data_type || char(10) || 'Details: ' || file_metadata.reported_count_label || char(10) || 'Note: ' || COALESCE(file_metadata.safety_policy_applied, '')
            WHEN fts_archive.record_type = 'ENTITY' THEN COALESCE(o.description, '') || char(10) || 'Linked Entities: ' || COALESCE(fts_archive.entity_names, 'N/A')
            ELSE fts_archive.editorial_content
        END AS editorial_content,
        CASE
            WHEN fts_archive.record_type = 'ARTICLE' THEN a.publication_date
            WHEN fts_archive.record_type = 'PUBLICATION' THEN p.publication_date
            WHEN fts_archive.record_type = 'CSV_ROW' THEN SUBSTR(csv_row_content.retrieved_at, 1, 10)
            WHEN fts_archive.record_type = 'FILE_INVENTORY' THEN COALESCE(file_metadata.publication_date, SUBSTR(file_metadata.retrieved_at, 1, 10))
            WHEN fts_archive.record_type = 'ENTITY' THEN SUBSTR(o.retrieved_at, 1, 10)
            ELSE fts_archive.publication_date
        END AS publication_date,
        CASE
            WHEN fts_archive.record_type = 'ARTICLE' THEN COALESCE((
                SELECT GROUP_CONCAT(DISTINCT cat.name_en)
                FROM article_categories ac
                JOIN categories cat ON cat.id = ac.category_id
                WHERE ac.article_id = a.id
            ), 'General Research')
            WHEN fts_archive.record_type = 'PUBLICATION' THEN COALESCE((
                SELECT GROUP_CONCAT(DISTINCT cat.name_en)
                FROM publication_categories pc
                JOIN categories cat ON cat.id = pc.category_id
                WHERE pc.publication_id = p.id
            ), 'Publication Catalogue')
            WHEN fts_archive.record_type = 'CSV_ROW' THEN 'CSV Excel Table (' || csv_row_content.original_filename || ')'
            WHEN fts_archive.record_type = 'FILE_INVENTORY' THEN 'File & Document Inventory'
            WHEN fts_archive.record_type = 'ENTITY' THEN 'Organization / ' || o.org_type
            ELSE 'General Research'
        END AS category_en,
        CASE
            WHEN fts_archive.record_type = 'ARTICLE' THEN COALESCE((
                SELECT GROUP_CONCAT(DISTINCT cat.name_fa)
                FROM article_categories ac
                JOIN categories cat ON cat.id = ac.category_id
                WHERE ac.article_id = a.id
            ), 'پژوهش عمومی')
            WHEN fts_archive.record_type = 'PUBLICATION' THEN COALESCE((
                SELECT GROUP_CONCAT(DISTINCT cat.name_fa)
                FROM publication_categories pc
                JOIN categories cat ON cat.id = pc.category_id
                WHERE pc.publication_id = p.id
            ), 'فهرست انتشارات')
            WHEN fts_archive.record_type = 'CSV_ROW' THEN 'جدول اکسل CSV (' || csv_row_content.original_filename || ')'
            WHEN fts_archive.record_type = 'FILE_INVENTORY' THEN 'فهرست فایل‌ها و اسناد'
            WHEN fts_archive.record_type = 'ENTITY' THEN 'سازمان و نهاد (' || COALESCE(NULLIF(o.native_name, ''), o.org_type) || ')'
            ELSE 'پژوهش عمومی'
        END AS category_fa,
        CASE
            WHEN fts_archive.record_type = 'ARTICLE' THEN COALESCE((
                SELECT GROUP_CONCAT(DISTINCT cat.slug)
                FROM article_categories ac
                JOIN categories cat ON cat.id = ac.category_id
                WHERE ac.article_id = a.id
            ), '')
            WHEN fts_archive.record_type = 'PUBLICATION' THEN COALESCE((
                SELECT GROUP_CONCAT(DISTINCT cat.slug)
                FROM publication_categories pc
                JOIN categories cat ON cat.id = pc.category_id
                WHERE pc.publication_id = p.id
            ), '')
            ELSE ''
        END AS category_slugs,
        CASE
            WHEN fts_archive.record_type = 'ARTICLE' THEN COALESCE((
                SELECT GROUP_CONCAT(DISTINCT org.name)
                FROM article_entities ae
                JOIN organizations org ON org.id = ae.organization_id
                WHERE ae.article_id = a.id
            ), '')
            WHEN fts_archive.record_type = 'ENTITY' THEN o.name
            ELSE ''
        END AS organizations,
        CASE
            WHEN fts_archive.record_type = 'ARTICLE' THEN COALESCE((
                SELECT GROUP_CONCAT(DISTINCT tg.name)
                FROM article_tags atg
                JOIN tags tg ON tg.id = atg.tag_id
                WHERE atg.article_id = a.id
            ), '')
            WHEN fts_archive.record_type = 'PUBLICATION' THEN 'Catalogue Metadata'
            WHEN fts_archive.record_type = 'CSV_ROW' THEN 'CSV Excel Table'
            WHEN fts_archive.record_type = 'FILE_INVENTORY' THEN file_metadata.data_type
            WHEN fts_archive.record_type = 'ENTITY' THEN COALESCE(NULLIF(o.acronym, ''), o.org_type)
            ELSE fts_archive.tag_names
        END AS tags,
        CASE
            WHEN fts_archive.record_type = 'ARTICLE' THEN COALESCE(sa.name, 'WikIran Public Articles')
            WHEN fts_archive.record_type = 'PUBLICATION' THEN COALESCE(sp.name, 'WikIran Publication Catalogue')
            WHEN fts_archive.record_type = 'CSV_ROW' THEN csv_row_content.dataset_name
            WHEN fts_archive.record_type = 'FILE_INVENTORY' THEN COALESCE(file_metadata.publication_title, 'File Inventory')
            WHEN fts_archive.record_type = 'ENTITY' THEN 'WikIran Organizations & Entities'
            ELSE 'WikIran Archive'
        END AS source_name,
        COALESCE(
            a.source_url,
            p.source_url,
            csv_row_content.source_url,
            file_metadata.source_url,
            o.source_url,
            fts_archive.source_url
        ) AS source_url,
        COALESCE(
            a.extraction_status,
            p.extraction_status,
            csv_row_content.extraction_status,
            file_metadata.extraction_status,
            o.extraction_status,
            'VERIFIED'
        ) AS extraction_status,
        COALESCE(
            a.retrieved_at,
            p.retrieved_at,
            csv_row_content.retrieved_at,
            file_metadata.retrieved_at,
            o.retrieved_at,
            ''
        ) AS retrieved_at,
        COALESCE(
            a.record_version,
            p.record_version,
            csv_row_content.record_version,
            file_metadata.record_version,
            o.record_version,
            1
        ) AS record_version
    FROM fts_archive
    LEFT JOIN articles a
        ON fts_archive.record_type = 'ARTICLE' AND a.id = CAST(fts_archive.record_id AS INTEGER)
    LEFT JOIN sources sa
        ON sa.id = a.source_id
    LEFT JOIN publications p
        ON fts_archive.record_type = 'PUBLICATION' AND p.id = CAST(fts_archive.record_id AS INTEGER)
    LEFT JOIN sources sp
        ON sp.id = p.source_id
    LEFT JOIN csv_row_content
        ON fts_archive.record_type = 'CSV_ROW' AND csv_row_content.id = CAST(fts_archive.record_id AS INTEGER)
    LEFT JOIN file_metadata
        ON fts_archive.record_type = 'FILE_INVENTORY' AND file_metadata.id = CAST(fts_archive.record_id AS INTEGER)
    LEFT JOIN organizations o
        ON fts_archive.record_type = 'ENTITY' AND o.id = CAST(fts_archive.record_id AS INTEGER)
    WHERE {fts_where_clause}
      AND (
          :source_type IS NULL
          OR :source_type = ''
          OR :source_type = 'ALL'
          OR fts_archive.record_type = :source_type
      )
      AND (
          :has_fts = 1
          OR :source_type IS NOT NULL
          OR fts_archive.record_type IN ('ARTICLE', 'PUBLICATION')
      )
)
SELECT *
FROM unified_joined_records
WHERE title IS NOT NULL
  AND (:date_from IS NULL OR :date_from = '' OR publication_date >= :date_from)
  AND (:date_to IS NULL OR :date_to = '' OR publication_date <= :date_to)
  AND (
      :extraction_status IS NULL
      OR :extraction_status = ''
      OR :extraction_status = 'ALL'
      OR extraction_status = :extraction_status
  )
  AND (
      :category_slug IS NULL
      OR :category_slug = ''
      OR :category_slug = 'ALL'
      OR (',' || category_slugs || ',') LIKE '%,' || :category_slug || ',%'
  )
  AND (
      :organization_name IS NULL
      OR :organization_name = ''
      OR :organization_name = 'ALL'
      OR LOWER(organizations) LIKE '%' || LOWER(:organization_name) || '%'
  )
ORDER BY publication_date DESC, fts_rank ASC, id DESC;
"""


class ArchiveSearchEngine:
    """Fast local SQLite FTS5 search engine performing a unified JOIN across all tables."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _ensure_views_and_fts_synced(self) -> None:
        """
        Ensure csv_row_content and file_metadata SQLite views exist and that any
        file_inventory or organizations records are indexed in fts_archive.
        """
        self.conn.executescript(
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

        # Backfill any file_inventory rows not yet in fts_archive
        missing_fi = self.conn.execute(
            """
            SELECT fm.*
            FROM file_metadata fm
            WHERE NOT EXISTS (
                SELECT 1 FROM fts_archive f
                WHERE f.record_type = 'FILE_INVENTORY' AND f.record_id = CAST(fm.id AS TEXT)
            );
            """
        ).fetchall()
        for r in missing_fi:
            self.conn.execute(
                """
                INSERT INTO fts_archive (
                    record_type, record_id, title, editorial_content, summary,
                    organization_names, entity_names, category_names, tag_names,
                    publication_date, source_url
                ) VALUES ('FILE_INVENTORY', ?, ?, ?, ?, '', '', 'File & Document Metadata', ?, ?, ?);
                """,
                (
                    str(r["id"]),
                    f"{r['publication_title'] or 'Archive File'} — {r['data_type']}",
                    f"{r['data_type']} {r['reported_count_label']} {r['safety_policy_applied'] or ''} {r['source_url']}",
                    f"{r['reported_count_label']} | {r['safety_policy_applied'] or ''}",
                    r["data_type"],
                    r["publication_date"] or (r["retrieved_at"] or "")[:10],
                    r["source_url"],
                ),
            )

        # Backfill any organizations not yet in fts_archive
        missing_orgs = self.conn.execute(
            """
            SELECT o.*,
                   GROUP_CONCAT(DISTINCT e.name || ' (' || e.entity_type || ')') AS entities_list
            FROM organizations o
            LEFT JOIN entities e ON e.organization_id = o.id
            WHERE NOT EXISTS (
                SELECT 1 FROM fts_archive f
                WHERE f.record_type = 'ENTITY' AND f.record_id = CAST(o.id AS TEXT)
            )
            GROUP BY o.id;
            """
        ).fetchall()
        for r in missing_orgs:
            self.conn.execute(
                """
                INSERT INTO fts_archive (
                    record_type, record_id, title, editorial_content, summary,
                    organization_names, entity_names, category_names, tag_names,
                    publication_date, source_url
                ) VALUES ('ENTITY', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    str(r["id"]),
                    f"{r['name']} ({r['acronym'] or r['org_type']})",
                    f"{r['description'] or ''} {r['native_name'] or ''} {r['entities_list'] or ''} {r['source_url']}",
                    r["description"] or "",
                    f"{r['name']} {r['native_name'] or ''} {r['acronym'] or ''}".strip(),
                    r["entities_list"] or "",
                    r["org_type"],
                    r["acronym"] or r["org_type"],
                    (r["retrieved_at"] or "")[:10],
                    r["source_url"],
                ),
            )
        if missing_fi or missing_orgs:
            self.conn.commit()

    def search(self, filters: SearchFilters) -> list[dict[str, Any]]:
        """
        Execute a single unified SQLite FTS5 query joining `fts_archive` across all tables:
        `articles`, `publications`, `csv_row_content`, `file_metadata`, and `organizations`.
        """
        self._ensure_views_and_fts_synced()
        fts_query = _build_safe_fts_query(filters.query)
        has_fts = 1 if fts_query else 0

        norm_source_type = filters.source_type
        if norm_source_type in ("ALL", ""):
            norm_source_type = None
        elif norm_source_type == "FILE_METADATA":
            norm_source_type = "FILE_INVENTORY"

        sql_query = UNIFIED_FTS5_JOIN_SQL.format(
            rank_expr="bm25(fts_archive)" if has_fts else "0.0",
            fts_where_clause="fts_archive MATCH :fts_query" if has_fts else "1 = 1",
        )

        params = {
            "has_fts": has_fts,
            "fts_query": fts_query,
            "source_type": norm_source_type,
            "date_from": filters.date_from,
            "date_to": filters.date_to,
            "extraction_status": filters.extraction_status,
            "category_slug": filters.category_slug,
            "organization_name": filters.organization_name,
        }

        rows = self.conn.execute(sql_query, params).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "record_type": row["record_type"],
                    "id": int(row["id"]),
                    "title": row["title"],
                    "native_title": row["native_title"] or "",
                    "short_description": row["short_description"] or "",
                    "editorial_content": row["editorial_content"] or "",
                    "publication_date": row["publication_date"] or "",
                    "category_en": row["category_en"],
                    "category_fa": row["category_fa"],
                    "organizations": row["organizations"] or "",
                    "tags": row["tags"] or "",
                    "source_name": row["source_name"],
                    "source_url": row["source_url"] or "",
                    "extraction_status": row["extraction_status"],
                    "retrieved_at": row["retrieved_at"] or "",
                    "record_version": int(row["record_version"] or 1),
                }
            )
        return results
