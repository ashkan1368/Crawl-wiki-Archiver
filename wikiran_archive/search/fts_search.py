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
    exact_match: bool = False


def parse_exact_query(raw_query: str, exact_flag: bool = False) -> tuple[str, bool]:
    """
    Detect explicit exact-phrase mode either from the UI toggle (`exact_flag=True`)
    or when the user wraps their query in double quotes (e.g. `"Bank Sepah"`).
    Returns `(cleaned_query, effective_exact_mode)`.
    """
    q = (raw_query or "").strip()
    if len(q) >= 2 and q[0] == '"' and q[-1] == '"':
        inner = q[1:-1].strip()
        if inner:
            return inner, True
    return q, bool(exact_flag)


def _build_safe_fts_query(raw_query: str, *, exact_match: bool = False) -> str:
    """
    Sanitize user input into a safe FTS5 query.
    - When `exact_match=False`: prefix-wildcard AND query (`"tok1"* AND "tok2"*`).
    - When `exact_match=True`: exact FTS5 phrase query (`"tok1 tok2"`) with NO `*` prefix wildcard.
    """
    tokens = re.findall(r"[\w\u0600-\u06FF]+", raw_query, flags=re.UNICODE)
    if not tokens:
        return ""
    if exact_match:
        phrase = " ".join(tokens)
        return f'"{phrase}"'
    return " AND ".join(f'"{t}"*' for t in tokens)


def matches_exact_word_or_phrase(record: dict[str, Any], raw_query: str) -> bool:
    """
    Strict whole-word / exact-phrase verifier (Unicode-aware, supports English & Persian).
    Ensures e.g. `"Sepah"` matches `"Bank Sepah"` and NEVER matches `"Sepahan"`,
    and `"Bank Sepah"` matches the consecutive phrase `"Bank Sepah"` only.
    """
    clean_q, _ = parse_exact_query(raw_query, exact_flag=True)
    if not clean_q:
        return True

    # Normalize internal whitespace in query so multi-word phrases match across single/multi spaces or newlines
    parts = [re.escape(p) for p in re.split(r"\s+", clean_q) if p]
    if not parts:
        return True
    phrase_pattern = r"\s+".join(parts)

    # Apply word boundaries on ends that start/end with a word character (\w covers Latin, digits, Arabic/Persian letters)
    prefix_boundary = r"(?<!\w)" if re.match(r"^\w", clean_q, flags=re.UNICODE) else ""
    suffix_boundary = r"(?!\w)" if re.search(r"\w$", clean_q, flags=re.UNICODE) else ""
    regex = re.compile(
        f"{prefix_boundary}{phrase_pattern}{suffix_boundary}",
        flags=re.IGNORECASE | re.UNICODE,
    )

    haystack_fields = (
        record.get("title"),
        record.get("native_title"),
        record.get("short_description"),
        record.get("editorial_content"),
        record.get("organizations"),
        record.get("tags"),
        record.get("source_name"),
        record.get("ofac_programs"),
        record.get("ofac_aliases"),
        record.get("ofac_addresses"),
        record.get("ofac_countries"),
        record.get("os_datasets"),
        record.get("os_identifiers"),
        record.get("source_url"),
    )
    for field_val in haystack_fields:
        if field_val and regex.search(str(field_val)):
            return True
    return False


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
            WHEN fts_archive.record_type = 'OFAC_SANCTION' THEN ofac.sdn_name
            WHEN fts_archive.record_type = 'OPENSANCTIONS' THEN os_ent.name
            WHEN fts_archive.record_type = 'WIKIRAN_DOC' THEN wdoc.title
            ELSE fts_archive.title
        END AS title,
        CASE
            WHEN fts_archive.record_type = 'PUBLICATION' THEN COALESCE(p.native_title, '')
            WHEN fts_archive.record_type = 'ENTITY' THEN COALESCE(o.native_name, '')
            WHEN fts_archive.record_type = 'OFAC_SANCTION' THEN COALESCE(ofac.aliases_text, '')
            WHEN fts_archive.record_type = 'OPENSANCTIONS' THEN COALESCE(os_ent.aliases, '')
            WHEN fts_archive.record_type = 'WIKIRAN_DOC' THEN COALESCE(wdoc.identifier_or_imo, '')
            ELSE ''
        END AS native_title,
        CASE
            WHEN fts_archive.record_type = 'ARTICLE' THEN a.summary
            WHEN fts_archive.record_type = 'PUBLICATION' THEN p.description
            WHEN fts_archive.record_type = 'CSV_ROW' THEN csv_row_content.searchable_text
            WHEN fts_archive.record_type = 'FILE_INVENTORY' THEN file_metadata.reported_count_label || ' | ' || COALESCE(file_metadata.safety_policy_applied, '')
            WHEN fts_archive.record_type = 'ENTITY' THEN COALESCE(o.description, fts_archive.summary)
            WHEN fts_archive.record_type = 'OFAC_SANCTION' THEN
                'OFAC ' || ofac.list_source || ' (' || COALESCE(NULLIF(ofac.sdn_type, ''), 'entity') || ')'
                || CASE WHEN ofac.programs != '' THEN ' · Programs: ' || ofac.programs ELSE '' END
                || CASE WHEN ofac.countries_text != '' THEN ' · Countries: ' || ofac.countries_text ELSE '' END
            WHEN fts_archive.record_type = 'OPENSANCTIONS' THEN
                'OpenSanctions ' || COALESCE(NULLIF(os_ent.schema_type, ''), 'Entity')
                || CASE WHEN os_ent.countries != '' THEN ' · Countries: ' || os_ent.countries ELSE '' END
                || CASE WHEN os_ent.datasets != '' THEN ' · Lists: ' || os_ent.datasets ELSE '' END
            WHEN fts_archive.record_type = 'WIKIRAN_DOC' THEN COALESCE(NULLIF(wdoc.snippet, ''), wdoc.title)
            ELSE fts_archive.summary
        END AS short_description,
        CASE
            WHEN fts_archive.record_type = 'ARTICLE' THEN a.editorial_content
            WHEN fts_archive.record_type = 'PUBLICATION' THEN p.description
            WHEN fts_archive.record_type = 'CSV_ROW' THEN csv_row_content.searchable_text
            WHEN fts_archive.record_type = 'FILE_INVENTORY' THEN 'Inventory Type: ' || file_metadata.data_type || char(10) || 'Details: ' || file_metadata.reported_count_label || char(10) || 'Note: ' || COALESCE(file_metadata.safety_policy_applied, '')
            WHEN fts_archive.record_type = 'ENTITY' THEN COALESCE(o.description, '') || char(10) || 'Linked Entities: ' || COALESCE(fts_archive.entity_names, 'N/A')
            WHEN fts_archive.record_type = 'OFAC_SANCTION' THEN
                TRIM(
                    CASE WHEN ofac.aliases_text != '' THEN 'Aliases (AKA): ' || ofac.aliases_text || char(10) ELSE '' END
                    || CASE WHEN ofac.addresses_text != '' THEN 'Addresses: ' || ofac.addresses_text || char(10) ELSE '' END
                    || CASE WHEN ofac.remarks != '' THEN 'Remarks: ' || ofac.remarks ELSE '' END
                )
            WHEN fts_archive.record_type = 'OPENSANCTIONS' THEN
                TRIM(
                    CASE WHEN os_ent.aliases != '' THEN 'Aliases: ' || os_ent.aliases || char(10) ELSE '' END
                    || CASE WHEN os_ent.identifiers != '' THEN 'Identifiers: ' || os_ent.identifiers || char(10) ELSE '' END
                    || CASE WHEN os_ent.addresses != '' THEN 'Addresses: ' || os_ent.addresses || char(10) ELSE '' END
                    || CASE WHEN os_ent.sanctions != '' THEN 'Sanctions Details: ' || os_ent.sanctions || char(10) ELSE '' END
                    || CASE WHEN os_ent.program_ids != '' THEN 'Programs: ' || os_ent.program_ids ELSE '' END
                )
            WHEN fts_archive.record_type = 'WIKIRAN_DOC' THEN
                TRIM(
                    'Document Type: ' || wdoc.doc_type || char(10)
                    || CASE WHEN wdoc.leak_sources != '' THEN 'Source Leak: ' || wdoc.leak_sources || char(10) ELSE '' END
                    || CASE WHEN wdoc.country_or_flag != '' THEN 'Jurisdiction / Flag: ' || wdoc.country_or_flag || char(10) ELSE '' END
                    || CASE WHEN wdoc.bank_or_operator != '' THEN 'Bank / Operator: ' || wdoc.bank_or_operator || char(10) ELSE '' END
                    || CASE WHEN wdoc.identifier_or_imo != '' THEN 'Account / IMO / Ref: ' || wdoc.identifier_or_imo || char(10) ELSE '' END
                    || 'Details: ' || wdoc.snippet
                )
            ELSE fts_archive.editorial_content
        END AS editorial_content,
        CASE
            WHEN fts_archive.record_type = 'ARTICLE' THEN a.publication_date
            WHEN fts_archive.record_type = 'PUBLICATION' THEN p.publication_date
            WHEN fts_archive.record_type = 'CSV_ROW' THEN SUBSTR(csv_row_content.retrieved_at, 1, 10)
            WHEN fts_archive.record_type = 'FILE_INVENTORY' THEN COALESCE(file_metadata.publication_date, SUBSTR(file_metadata.retrieved_at, 1, 10))
            WHEN fts_archive.record_type = 'ENTITY' THEN SUBSTR(o.retrieved_at, 1, 10)
            WHEN fts_archive.record_type = 'OFAC_SANCTION' THEN COALESCE(NULLIF(ofac.date_published, ''), SUBSTR(ofac.retrieved_at, 1, 10))
            WHEN fts_archive.record_type = 'OPENSANCTIONS' THEN SUBSTR(COALESCE(NULLIF(os_ent.last_change, ''), NULLIF(os_ent.last_seen, ''), os_ent.retrieved_at), 1, 10)
            WHEN fts_archive.record_type = 'WIKIRAN_DOC' THEN COALESCE(NULLIF(wdoc.document_date, ''), SUBSTR(wdoc.retrieved_at, 1, 10))
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
            WHEN fts_archive.record_type = 'OFAC_SANCTION' THEN 'OFAC ' || ofac.list_source || ' (' || COALESCE(NULLIF(ofac.programs, ''), 'SANCTIONS') || ')'
            WHEN fts_archive.record_type = 'OPENSANCTIONS' THEN 'OpenSanctions ' || COALESCE(NULLIF(os_ent.schema_type, ''), 'Entity') || ' (' || COALESCE(NULLIF(os_ent.datasets, ''), 'sanctions') || ')'
            WHEN fts_archive.record_type = 'WIKIRAN_DOC' THEN 'WikIran ' || REPLACE(wdoc.doc_type, '_', ' ') || CASE WHEN wdoc.leak_sources != '' THEN ' (' || wdoc.leak_sources || ')' ELSE '' END
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
            WHEN fts_archive.record_type = 'OFAC_SANCTION' THEN 'تحریم اوفک OFAC ' || ofac.list_source || ' (' || COALESCE(NULLIF(ofac.programs, ''), 'تحریم') || ')'
            WHEN fts_archive.record_type = 'OPENSANCTIONS' THEN 'تحریم جهانی OpenSanctions (' || COALESCE(NULLIF(os_ent.datasets, ''), 'sanctions') || ')'
            WHEN fts_archive.record_type = 'WIKIRAN_DOC' THEN 'آرشیو ویکی‌ایران (' || COALESCE(NULLIF(wdoc.leak_sources, ''), wdoc.doc_type) || ')'
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
            WHEN fts_archive.record_type = 'OFAC_SANCTION' THEN COALESCE(NULLIF(ofac.countries_text, ''), ofac.sdn_type)
            WHEN fts_archive.record_type = 'OPENSANCTIONS' THEN COALESCE(NULLIF(os_ent.countries, ''), os_ent.schema_type)
            WHEN fts_archive.record_type = 'WIKIRAN_DOC' THEN
                TRIM(
                    COALESCE(wdoc.bank_or_operator, '')
                    || CASE WHEN wdoc.bank_or_operator != '' AND wdoc.country_or_flag != '' THEN ' · ' ELSE '' END
                    || COALESCE(wdoc.country_or_flag, '')
                )
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
            WHEN fts_archive.record_type = 'OFAC_SANCTION' THEN ofac.programs
            WHEN fts_archive.record_type = 'OPENSANCTIONS' THEN COALESCE(NULLIF(os_ent.program_ids, ''), os_ent.datasets)
            WHEN fts_archive.record_type = 'WIKIRAN_DOC' THEN COALESCE(NULLIF(wdoc.leak_sources, ''), wdoc.doc_type)
            ELSE fts_archive.tag_names
        END AS tags,
        CASE
            WHEN fts_archive.record_type = 'ARTICLE' THEN COALESCE(sa.name, 'WikIran Public Articles')
            WHEN fts_archive.record_type = 'PUBLICATION' THEN COALESCE(sp.name, 'WikIran Publication Catalogue')
            WHEN fts_archive.record_type = 'CSV_ROW' THEN csv_row_content.dataset_name
            WHEN fts_archive.record_type = 'FILE_INVENTORY' THEN COALESCE(file_metadata.publication_title, 'File Inventory')
            WHEN fts_archive.record_type = 'ENTITY' THEN 'WikIran Organizations & Entities'
            WHEN fts_archive.record_type = 'OFAC_SANCTION' THEN 'U.S. Treasury OFAC ' || ofac.list_source || ' List'
            WHEN fts_archive.record_type = 'OPENSANCTIONS' THEN 'OpenSanctions Global (' || COALESCE(NULLIF(os_ent.schema_type, ''), 'Sanctions') || ')'
            WHEN fts_archive.record_type = 'WIKIRAN_DOC' THEN 'WikIran Archive — ' || COALESCE(NULLIF(wdoc.leak_sources, ''), wdoc.doc_type)
            ELSE 'WikIran Archive'
        END AS source_name,
        COALESCE(
            a.source_url,
            p.source_url,
            csv_row_content.source_url,
            file_metadata.source_url,
            o.source_url,
            ofac.source_url,
            os_ent.source_url,
            wdoc.source_url,
            fts_archive.source_url
        ) AS source_url,
        COALESCE(
            a.extraction_status,
            p.extraction_status,
            csv_row_content.extraction_status,
            file_metadata.extraction_status,
            o.extraction_status,
            CASE WHEN fts_archive.record_type = 'OFAC_SANCTION' THEN 'OFAC_DESIGNATED' ELSE NULL END,
            CASE WHEN fts_archive.record_type = 'OPENSANCTIONS' THEN 'OPENSANCTIONS_LISTED' ELSE NULL END,
            CASE WHEN fts_archive.record_type = 'WIKIRAN_DOC' THEN 'WIKIRAN_ARCHIVED' ELSE NULL END,
            'VERIFIED'
        ) AS extraction_status,
        COALESCE(
            a.retrieved_at,
            p.retrieved_at,
            csv_row_content.retrieved_at,
            file_metadata.retrieved_at,
            o.retrieved_at,
            ofac.retrieved_at,
            os_ent.retrieved_at,
            wdoc.retrieved_at,
            ''
        ) AS retrieved_at,
        COALESCE(
            a.record_version,
            p.record_version,
            csv_row_content.record_version,
            file_metadata.record_version,
            o.record_version,
            1
        ) AS record_version,
        ofac.ent_num AS ofac_ent_num,
        COALESCE(ofac.list_source, '') AS ofac_list_source,
        COALESCE(ofac.sdn_type, '') AS ofac_sdn_type,
        COALESCE(ofac.programs, '') AS ofac_programs,
        COALESCE(ofac.aliases_text, '') AS ofac_aliases,
        COALESCE(ofac.addresses_text, '') AS ofac_addresses,
        COALESCE(ofac.countries_text, '') AS ofac_countries,
        COALESCE(os_ent.os_id, '') AS os_id,
        COALESCE(os_ent.schema_type, '') AS os_schema,
        COALESCE(os_ent.datasets, '') AS os_datasets,
        COALESCE(os_ent.identifiers, '') AS os_identifiers,
        COALESCE(wdoc.doc_type, '') AS wikiran_doc_type
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
    LEFT JOIN ofac_entities ofac
        ON fts_archive.record_type = 'OFAC_SANCTION' AND ofac.id = CAST(fts_archive.record_id AS INTEGER)
    LEFT JOIN opensanctions_entities os_ent
        ON fts_archive.record_type = 'OPENSANCTIONS' AND os_ent.id = CAST(fts_archive.record_id AS INTEGER)
    LEFT JOIN wikiran_documents wdoc
        ON fts_archive.record_type = 'WIKIRAN_DOC' AND wdoc.id = CAST(fts_archive.record_id AS INTEGER)
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
  AND (
      :date_from IS NULL
      OR :date_from = ''
      OR (
          TRIM(COALESCE(publication_date, '')) != ''
          AND SUBSTR(TRIM(publication_date), 1, 10) >= :date_from
      )
  )
  AND (
      :date_to IS NULL
      OR :date_to = ''
      OR (
          TRIM(COALESCE(publication_date, '')) != ''
          AND SUBSTR(TRIM(publication_date), 1, 10) <= :date_to
      )
  )
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
ORDER BY
    CASE
        WHEN record_type = 'OFAC_SANCTION' THEN 0
        WHEN record_type = 'OPENSANCTIONS' THEN 1
        ELSE 2
    END ASC,
    fts_rank ASC,
    publication_date DESC,
    id DESC
LIMIT 600;
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
        `articles`, `publications`, `csv_row_content`, `file_metadata`, `organizations`,
        `ofac_entities`, `opensanctions_entities`, and `wikiran_documents`.
        """
        self._ensure_views_and_fts_synced()
        clean_query, effective_exact = parse_exact_query(filters.query, filters.exact_match)
        fts_query = _build_safe_fts_query(clean_query, exact_match=effective_exact)
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
            item = {
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
                "ofac_ent_num": int(row["ofac_ent_num"]) if row["ofac_ent_num"] is not None else None,
                "ofac_list_source": row["ofac_list_source"] or "",
                "ofac_sdn_type": row["ofac_sdn_type"] or "",
                "ofac_programs": row["ofac_programs"] or "",
                "ofac_aliases": row["ofac_aliases"] or "",
                "ofac_addresses": row["ofac_addresses"] or "",
                "ofac_countries": row["ofac_countries"] or "",
                "os_id": row["os_id"] or "",
                "os_schema": row["os_schema"] or "",
                "os_datasets": row["os_datasets"] or "",
                "os_identifiers": row["os_identifiers"] or "",
                "wikiran_doc_type": row["wikiran_doc_type"] or "",
            }
            if effective_exact and clean_query and not matches_exact_word_or_phrase(item, clean_query):
                continue
            results.append(item)
        return results
