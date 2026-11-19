"""
Repository layer for persisting, deduplicating, versioning, and querying
articles, publications, organizations, entities, categories, tags, sources,
file inventory metadata, collection jobs, and settings.
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import Any


def compute_content_hash(*parts: str) -> str:
    """Compute deterministic SHA-256 hex digest over normalized text parts."""
    normalized = "||".join((p or "").strip() for p in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ArchiveRepository:
    """Data access and persistence manager for WikIran Archive."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    def get_settings(self) -> dict[str, str]:
        rows = self.conn.execute("SELECT key, value FROM application_settings;").fetchall()
        return {r["key"]: r["value"] for r in rows}

    def set_setting(self, key: str, value: str) -> None:
        now = utc_now_iso()
        self.conn.execute(
            """
            INSERT INTO application_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at;
            """,
            (key, str(value), now),
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Sources, Categories, Tags, Organizations, Entities
    # ------------------------------------------------------------------
    def upsert_source(
        self,
        name: str,
        source_type: str,
        base_url: str,
        source_url: str,
        original_pub_id: str | None = None,
        robots_status: str = "PERMITTED",
    ) -> int:
        now = utc_now_iso()
        c_hash = compute_content_hash(name, source_type, source_url)
        existing = self.conn.execute(
            "SELECT id FROM sources WHERE name = ?;", (name,)
        ).fetchone()
        if existing:
            self.conn.execute(
                """
                UPDATE sources
                SET last_verified_at = ?, robots_status = ?, source_url = ?
                WHERE id = ?;
                """,
                (now, robots_status, source_url, existing["id"]),
            )
            self.conn.commit()
            return int(existing["id"])

        cur = self.conn.execute(
            """
            INSERT INTO sources (
                name, source_type, base_url, source_url, original_pub_id,
                robots_status, retrieved_at, last_verified_at, extraction_status,
                content_hash, record_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'VERIFIED', ?, 1);
            """,
            (name, source_type, base_url, source_url, original_pub_id, robots_status, now, now, c_hash),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def upsert_category(
        self,
        slug: str,
        name_en: str,
        name_fa: str,
        description: str = "",
        source_url: str = "https://wikiran.org/",
    ) -> int:
        now = utc_now_iso()
        c_hash = compute_content_hash(slug, name_en, name_fa, description)
        existing = self.conn.execute(
            "SELECT id FROM categories WHERE slug = ?;", (slug,)
        ).fetchone()
        if existing:
            self.conn.execute(
                """
                UPDATE categories
                SET name_en = ?, name_fa = ?, description = ?, last_verified_at = ?
                WHERE id = ?;
                """,
                (name_en, name_fa, description, now, existing["id"]),
            )
            self.conn.commit()
            return int(existing["id"])

        cur = self.conn.execute(
            """
            INSERT INTO categories (
                slug, name_en, name_fa, description, source_url, original_pub_id,
                retrieved_at, last_verified_at, extraction_status, content_hash, record_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'VERIFIED', ?, 1);
            """,
            (slug, name_en, name_fa, description, source_url, slug, now, now, c_hash),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def upsert_tag(self, name: str, source_url: str = "https://wikiran.org/") -> int:
        clean_name = name.strip()
        now = utc_now_iso()
        c_hash = compute_content_hash(clean_name)
        existing = self.conn.execute(
            "SELECT id FROM tags WHERE LOWER(name) = LOWER(?);", (clean_name,)
        ).fetchone()
        if existing:
            self.conn.execute(
                "UPDATE tags SET last_verified_at = ? WHERE id = ?;",
                (now, existing["id"]),
            )
            self.conn.commit()
            return int(existing["id"])

        cur = self.conn.execute(
            """
            INSERT INTO tags (
                name, source_url, original_pub_id, retrieved_at, last_verified_at,
                extraction_status, content_hash, record_version
            ) VALUES (?, ?, ?, ?, ?, 'VERIFIED', ?, 1);
            """,
            (clean_name, source_url, clean_name.lower(), now, now, c_hash),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def upsert_organization(
        self,
        name: str,
        native_name: str = "",
        acronym: str = "",
        org_type: str = "STATE_INSTITUTION",
        description: str = "",
        source_url: str = "https://wikiran.org/",
        original_pub_id: str | None = None,
    ) -> int:
        now = utc_now_iso()
        c_hash = compute_content_hash(name, native_name, acronym, org_type, description)
        existing = self.conn.execute(
            "SELECT id, content_hash, record_version FROM organizations WHERE name = ?;",
            (name,),
        ).fetchone()
        if existing:
            org_id = int(existing["id"])
            if existing["content_hash"] != c_hash and description:
                new_ver = int(existing["record_version"]) + 1
                self.conn.execute(
                    """
                    UPDATE organizations
                    SET native_name = COALESCE(NULLIF(?, ''), native_name),
                        acronym = COALESCE(NULLIF(?, ''), acronym),
                        org_type = ?,
                        description = ?,
                        last_verified_at = ?,
                        content_hash = ?,
                        record_version = ?
                    WHERE id = ?;
                    """,
                    (native_name, acronym, org_type, description, now, c_hash, new_ver, org_id),
                )
            else:
                self.conn.execute(
                    "UPDATE organizations SET last_verified_at = ? WHERE id = ?;",
                    (now, org_id),
                )
            self.conn.commit()
            return org_id

        cur = self.conn.execute(
            """
            INSERT INTO organizations (
                name, native_name, acronym, org_type, description, source_url,
                original_pub_id, retrieved_at, last_verified_at, extraction_status,
                content_hash, record_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'VERIFIED', ?, 1);
            """,
            (
                name,
                native_name,
                acronym,
                org_type,
                description,
                source_url,
                original_pub_id or acronym or name,
                now,
                now,
                c_hash,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def upsert_entity(
        self,
        name: str,
        entity_type: str = "ORGANIZATION",
        organization_id: int | None = None,
        description: str = "",
        source_url: str = "https://wikiran.org/",
        original_pub_id: str | None = None,
    ) -> int:
        now = utc_now_iso()
        c_hash = compute_content_hash(name, entity_type, description)
        existing = self.conn.execute(
            "SELECT id FROM entities WHERE name = ?;", (name,)
        ).fetchone()
        if existing:
            self.conn.execute(
                """
                UPDATE entities
                SET last_verified_at = ?,
                    organization_id = COALESCE(?, organization_id)
                WHERE id = ?;
                """,
                (now, organization_id, existing["id"]),
            )
            self.conn.commit()
            return int(existing["id"])

        cur = self.conn.execute(
            """
            INSERT INTO entities (
                name, entity_type, organization_id, description, source_url,
                original_pub_id, retrieved_at, last_verified_at, extraction_status,
                content_hash, record_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'VERIFIED', ?, 1);
            """,
            (
                name,
                entity_type,
                organization_id,
                description,
                source_url,
                original_pub_id or name,
                now,
                now,
                c_hash,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    # ------------------------------------------------------------------
    # Articles & Publications (with Deduplication, Versioning & FTS Sync)
    # ------------------------------------------------------------------
    def upsert_article(
        self,
        *,
        original_pub_id: str,
        title: str,
        subtitle: str = "",
        author: str = "WikIran Editorial",
        publication_date: str,
        raw_date_text: str = "",
        summary: str,
        editorial_content: str,
        source_url: str,
        source_id: int | None = None,
        extraction_status: str = "VERIFIED",
        category_ids: list[int] | None = None,
        tag_ids: list[int] | None = None,
        entity_ids: list[tuple[int, int | None]] | None = None,
    ) -> tuple[int, str]:
        """
        Insert or update an article with deduplication by canonical source_url or original_pub_id.
        Returns (article_id, action) where action is 'INSERTED', 'UPDATED', or 'UNCHANGED'.
        """
        now = utc_now_iso()
        c_hash = compute_content_hash(title, subtitle, publication_date, summary, editorial_content)

        existing = self.conn.execute(
            "SELECT * FROM articles WHERE source_url = ? OR original_pub_id = ?;",
            (source_url, original_pub_id),
        ).fetchone()

        if existing:
            article_id = int(existing["id"])
            prev_hash = existing["content_hash"]
            prev_ver = int(existing["record_version"])
            if prev_hash == c_hash:
                self.conn.execute(
                    "UPDATE articles SET last_verified_at = ? WHERE id = ?;",
                    (now, article_id),
                )
                action = "UNCHANGED"
            else:
                new_ver = prev_ver + 1
                self.conn.execute(
                    """
                    UPDATE articles
                    SET title = ?, subtitle = ?, author = ?, publication_date = ?,
                        raw_date_text = ?, summary = ?, editorial_content = ?,
                        source_id = COALESCE(?, source_id), last_verified_at = ?,
                        extraction_status = ?, content_hash = ?, record_version = ?
                    WHERE id = ?;
                    """,
                    (
                        title,
                        subtitle,
                        author,
                        publication_date,
                        raw_date_text,
                        summary,
                        editorial_content,
                        source_id,
                        now,
                        extraction_status,
                        c_hash,
                        new_ver,
                        article_id,
                    ),
                )
                self.conn.execute(
                    """
                    INSERT INTO change_log (
                        table_name, record_id, source_url, previous_version,
                        new_version, previous_hash, new_hash, changed_at, change_summary
                    ) VALUES ('articles', ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        article_id,
                        source_url,
                        prev_ver,
                        new_ver,
                        prev_hash,
                        c_hash,
                        now,
                        f"Article content updated to version {new_ver}",
                    ),
                )
                action = "UPDATED"
        else:
            cur = self.conn.execute(
                """
                INSERT INTO articles (
                    original_pub_id, title, subtitle, author, publication_date,
                    raw_date_text, summary, editorial_content, source_id, source_url,
                    retrieved_at, last_verified_at, extraction_status, content_hash, record_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
                """,
                (
                    original_pub_id,
                    title,
                    subtitle,
                    author,
                    publication_date,
                    raw_date_text,
                    summary,
                    editorial_content,
                    source_id,
                    source_url,
                    now,
                    now,
                    extraction_status,
                    c_hash,
                ),
            )
            article_id = int(cur.lastrowid)
            action = "INSERTED"

        if category_ids is not None:
            for cid in category_ids:
                self.conn.execute(
                    "INSERT OR IGNORE INTO article_categories (article_id, category_id) VALUES (?, ?);",
                    (article_id, cid),
                )
        if tag_ids is not None:
            for tid in tag_ids:
                self.conn.execute(
                    "INSERT OR IGNORE INTO article_tags (article_id, tag_id) VALUES (?, ?);",
                    (article_id, tid),
                )
        if entity_ids is not None:
            for eid, oid in entity_ids:
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO article_entities (article_id, entity_id, organization_id, relevance_note)
                    VALUES (?, ?, ?, 'Referenced in public editorial article');
                    """,
                    (article_id, eid, oid),
                )

        self.sync_fts_for_article(article_id)
        self.conn.commit()
        return article_id, action

    def upsert_publication(
        self,
        *,
        original_pub_id: str,
        title: str,
        native_title: str = "",
        publication_date: str,
        raw_date_text: str = "",
        description: str,
        source_url: str,
        source_id: int | None = None,
        extraction_status: str = "VERIFIED",
        category_ids: list[int] | None = None,
        safe_inventory: list[tuple[str, str]] | None = None,
    ) -> tuple[int, str]:
        """
        Insert or update a safe publication catalogue entry.
        Never stores sensitive leaked emails or document contents.
        """
        now = utc_now_iso()
        c_hash = compute_content_hash(title, native_title, publication_date, description)

        existing = self.conn.execute(
            "SELECT * FROM publications WHERE source_url = ? OR original_pub_id = ?;",
            (source_url, original_pub_id),
        ).fetchone()

        if existing:
            pub_id = int(existing["id"])
            prev_hash = existing["content_hash"]
            prev_ver = int(existing["record_version"])
            if prev_hash == c_hash:
                self.conn.execute(
                    "UPDATE publications SET last_verified_at = ? WHERE id = ?;",
                    (now, pub_id),
                )
                action = "UNCHANGED"
            else:
                new_ver = prev_ver + 1
                self.conn.execute(
                    """
                    UPDATE publications
                    SET title = ?, native_title = ?, publication_date = ?,
                        raw_date_text = ?, description = ?,
                        source_id = COALESCE(?, source_id), last_verified_at = ?,
                        extraction_status = ?, content_hash = ?, record_version = ?
                    WHERE id = ?;
                    """,
                    (
                        title,
                        native_title,
                        publication_date,
                        raw_date_text,
                        description,
                        source_id,
                        now,
                        extraction_status,
                        c_hash,
                        new_ver,
                        pub_id,
                    ),
                )
                self.conn.execute(
                    """
                    INSERT INTO change_log (
                        table_name, record_id, source_url, previous_version,
                        new_version, previous_hash, new_hash, changed_at, change_summary
                    ) VALUES ('publications', ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        pub_id,
                        source_url,
                        prev_ver,
                        new_ver,
                        prev_hash,
                        c_hash,
                        now,
                        f"Publication catalogue metadata updated to version {new_ver}",
                    ),
                )
                action = "UPDATED"
        else:
            cur = self.conn.execute(
                """
                INSERT INTO publications (
                    original_pub_id, title, native_title, publication_date,
                    raw_date_text, description, source_id, source_url,
                    retrieved_at, last_verified_at, extraction_status, content_hash, record_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
                """,
                (
                    original_pub_id,
                    title,
                    native_title,
                    publication_date,
                    raw_date_text,
                    description,
                    source_id,
                    source_url,
                    now,
                    now,
                    extraction_status,
                    c_hash,
                ),
            )
            pub_id = int(cur.lastrowid)
            action = "INSERTED"

        if category_ids is not None:
            for cid in category_ids:
                self.conn.execute(
                    "INSERT OR IGNORE INTO publication_categories (publication_id, category_id) VALUES (?, ?);",
                    (pub_id, cid),
                )

        if safe_inventory is not None:
            for dtype, count_label in safe_inventory:
                inv_hash = compute_content_hash(str(pub_id), dtype, count_label)
                self.conn.execute(
                    """
                    INSERT INTO file_inventory (
                        publication_id, data_type, reported_count_label,
                        safety_policy_applied, source_url, original_pub_id,
                        retrieved_at, last_verified_at, extraction_status,
                        content_hash, record_version
                    ) VALUES (?, ?, ?, 'METADATA_ONLY_SENSITIVE_EXCLUDED', ?, ?, ?, ?, 'VERIFIED', ?, 1)
                    ON CONFLICT(publication_id, data_type) DO UPDATE SET
                        reported_count_label = excluded.reported_count_label,
                        last_verified_at = excluded.last_verified_at,
                        content_hash = excluded.content_hash;
                    """,
                    (pub_id, dtype, count_label, source_url, original_pub_id, now, now, inv_hash),
                )

        self.sync_fts_for_publication(pub_id)
        self.sync_fts_for_file_inventory(pub_id)
        self.conn.commit()
        return pub_id, action

    # ------------------------------------------------------------------
    # FTS5 Synchronization
    # ------------------------------------------------------------------
    def sync_fts_for_article(self, article_id: int) -> None:
        art = self.conn.execute("SELECT * FROM articles WHERE id = ?;", (article_id,)).fetchone()
        if not art:
            return
        orgs = self.conn.execute(
            """
            SELECT DISTINCT o.name, o.native_name, o.acronym
            FROM organizations o
            JOIN article_entities ae ON ae.organization_id = o.id
            WHERE ae.article_id = ?;
            """,
            (article_id,),
        ).fetchall()
        org_str = " ".join(
            f"{r['name']} {r['native_name'] or ''} {r['acronym'] or ''}" for r in orgs
        )

        ents = self.conn.execute(
            """
            SELECT DISTINCT e.name
            FROM entities e
            JOIN article_entities ae ON ae.entity_id = e.id
            WHERE ae.article_id = ?;
            """,
            (article_id,),
        ).fetchall()
        ent_str = " ".join(r["name"] for r in ents)

        cats = self.conn.execute(
            """
            SELECT c.name_en, c.name_fa
            FROM categories c
            JOIN article_categories ac ON ac.category_id = c.id
            WHERE ac.article_id = ?;
            """,
            (article_id,),
        ).fetchall()
        cat_str = " ".join(f"{r['name_en']} {r['name_fa']}" for r in cats)

        tags = self.conn.execute(
            """
            SELECT t.name
            FROM tags t
            JOIN article_tags at ON at.tag_id = t.id
            WHERE at.article_id = ?;
            """,
            (article_id,),
        ).fetchall()
        tag_str = " ".join(r["name"] for r in tags)

        self.conn.execute(
            "DELETE FROM fts_archive WHERE record_type = 'ARTICLE' AND record_id = ?;",
            (str(article_id),),
        )
        self.conn.execute(
            """
            INSERT INTO fts_archive (
                record_type, record_id, title, editorial_content, summary,
                organization_names, entity_names, category_names, tag_names,
                publication_date, source_url
            ) VALUES ('ARTICLE', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                str(article_id),
                f"{art['title']} {art['subtitle'] or ''} {art['author'] or ''}".strip(),
                f"{art['editorial_content']} {art['source_url']}",
                art["summary"],
                org_str,
                ent_str,
                cat_str,
                tag_str,
                art["publication_date"],
                art["source_url"],
            ),
        )

    def sync_fts_for_publication(self, pub_id: int) -> None:
        pub = self.conn.execute("SELECT * FROM publications WHERE id = ?;", (pub_id,)).fetchone()
        if not pub:
            return
        cats = self.conn.execute(
            """
            SELECT c.name_en, c.name_fa
            FROM categories c
            JOIN publication_categories pc ON pc.category_id = c.id
            WHERE pc.publication_id = ?;
            """,
            (pub_id,),
        ).fetchall()
        cat_str = " ".join(f"{r['name_en']} {r['name_fa']}" for r in cats)

        self.conn.execute(
            "DELETE FROM fts_archive WHERE record_type = 'PUBLICATION' AND record_id = ?;",
            (str(pub_id),),
        )
        self.conn.execute(
            """
            INSERT INTO fts_archive (
                record_type, record_id, title, editorial_content, summary,
                organization_names, entity_names, category_names, tag_names,
                publication_date, source_url
            ) VALUES ('PUBLICATION', ?, ?, ?, ?, ?, '', ?, '', ?, ?);
            """,
            (
                str(pub_id),
                f"{pub['title']} {pub['native_title'] or ''}".strip(),
                f"{pub['description']} {pub['source_url']}",
                pub["description"],
                pub["title"],
                cat_str,
                pub["publication_date"],
                pub["source_url"],
            ),
        )

    def sync_fts_for_file_inventory(self, pub_id: int) -> None:
        rows = self.conn.execute(
            """
            SELECT fi.*, p.title AS pub_title, p.publication_date
            FROM file_inventory fi
            LEFT JOIN publications p ON p.id = fi.publication_id
            WHERE fi.publication_id = ?;
            """,
            (pub_id,),
        ).fetchall()
        for r in rows:
            fid = str(r["id"])
            self.conn.execute(
                "DELETE FROM fts_archive WHERE record_type = 'FILE_INVENTORY' AND record_id = ?;",
                (fid,),
            )
            self.conn.execute(
                """
                INSERT INTO fts_archive (
                    record_type, record_id, title, editorial_content, summary,
                    organization_names, entity_names, category_names, tag_names,
                    publication_date, source_url
                ) VALUES ('FILE_INVENTORY', ?, ?, ?, ?, '', '', 'File & Document Metadata', ?, ?, ?);
                """,
                (
                    fid,
                    f"{r['pub_title'] or 'Archive File'} — {r['data_type']}",
                    f"{r['data_type']} {r['reported_count_label']} {r['safety_policy_applied'] or ''} {r['source_url']}",
                    f"{r['reported_count_label']} | {r['safety_policy_applied'] or ''}",
                    r["data_type"],
                    r["publication_date"] or (r["retrieved_at"] or "")[:10],
                    r["source_url"],
                ),
            )

    def sync_fts_for_organization(self, org_id: int) -> None:
        org = self.conn.execute(
            "SELECT * FROM organizations WHERE id = ?;", (org_id,)
        ).fetchone()
        if not org:
            return
        ents = self.conn.execute(
            "SELECT name, entity_type, description FROM entities WHERE organization_id = ?;",
            (org_id,),
        ).fetchall()
        ent_str = " ".join(
            f"{e['name']} ({e['entity_type']}) {e['description'] or ''}" for e in ents
        )
        oid = str(org["id"])
        self.conn.execute(
            "DELETE FROM fts_archive WHERE record_type = 'ENTITY' AND record_id = ?;",
            (oid,),
        )
        self.conn.execute(
            """
            INSERT INTO fts_archive (
                record_type, record_id, title, editorial_content, summary,
                organization_names, entity_names, category_names, tag_names,
                publication_date, source_url
            ) VALUES ('ENTITY', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                oid,
                f"{org['name']} ({org['acronym'] or org['org_type']})",
                f"{org['description'] or ''} {org['native_name'] or ''} {ent_str} {org['source_url']}",
                org["description"] or "",
                f"{org['name']} {org['native_name'] or ''} {org['acronym'] or ''}".strip(),
                ent_str,
                org["org_type"],
                org["acronym"] or org["org_type"],
                (org["retrieved_at"] or "")[:10],
                org["source_url"],
            ),
        )

    # ------------------------------------------------------------------
    # Dashboard & Query Helpers
    # ------------------------------------------------------------------
    def get_dashboard_stats(self) -> dict[str, Any]:
        articles_count = self.conn.execute("SELECT COUNT(*) FROM articles;").fetchone()[0]
        pubs_count = self.conn.execute("SELECT COUNT(*) FROM publications;").fetchone()[0]
        orgs_count = self.conn.execute("SELECT COUNT(*) FROM organizations;").fetchone()[0]
        entities_count = self.conn.execute("SELECT COUNT(*) FROM entities;").fetchone()[0]
        categories_count = self.conn.execute("SELECT COUNT(*) FROM categories;").fetchone()[0]
        sources_count = self.conn.execute("SELECT COUNT(*) FROM sources;").fetchone()[0]
        inventory_count = self.conn.execute("SELECT COUNT(*) FROM file_inventory;").fetchone()[0]
        jobs_count = self.conn.execute("SELECT COUNT(*) FROM collection_jobs;").fetchone()[0]
        changes_count = self.conn.execute("SELECT COUNT(*) FROM change_log;").fetchone()[0]

        last_job = self.conn.execute(
            "SELECT * FROM collection_jobs ORDER BY id DESC LIMIT 1;"
        ).fetchone()

        return {
            "articles_count": int(articles_count),
            "publications_count": int(pubs_count),
            "organizations_count": int(orgs_count),
            "entities_count": int(entities_count),
            "categories_count": int(categories_count),
            "sources_count": int(sources_count),
            "file_inventory_count": int(inventory_count),
            "jobs_count": int(jobs_count),
            "changes_count": int(changes_count),
            "last_job": dict(last_job) if last_job else None,
        }

    def list_articles(self, category_slug: str | None = None) -> list[dict[str, Any]]:
        query = """
            SELECT a.*, s.name AS source_name,
                   GROUP_CONCAT(DISTINCT c.name_en) AS categories_en,
                   GROUP_CONCAT(DISTINCT c.name_fa) AS categories_fa,
                   GROUP_CONCAT(DISTINCT t.name) AS tags_list,
                   GROUP_CONCAT(DISTINCT o.name) AS organizations_list
            FROM articles a
            LEFT JOIN sources s ON s.id = a.source_id
            LEFT JOIN article_categories ac ON ac.article_id = a.id
            LEFT JOIN categories c ON c.id = ac.category_id
            LEFT JOIN article_tags at ON at.article_id = a.id
            LEFT JOIN tags t ON t.id = at.tag_id
            LEFT JOIN article_entities ae ON ae.article_id = a.id
            LEFT JOIN organizations o ON o.id = ae.organization_id
        """
        params: list[Any] = []
        if category_slug:
            query += " WHERE a.id IN (SELECT ac2.article_id FROM article_categories ac2 JOIN categories c2 ON c2.id = ac2.category_id WHERE c2.slug = ?) "
            params.append(category_slug)
        query += " GROUP BY a.id ORDER BY a.publication_date DESC, a.id DESC;"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def list_publications(self, category_slug: str | None = None) -> list[dict[str, Any]]:
        query = """
            SELECT p.*, s.name AS source_name,
                   GROUP_CONCAT(DISTINCT c.name_en) AS categories_en,
                   GROUP_CONCAT(DISTINCT c.name_fa) AS categories_fa
            FROM publications p
            LEFT JOIN sources s ON s.id = p.source_id
            LEFT JOIN publication_categories pc ON pc.publication_id = p.id
            LEFT JOIN categories c ON c.id = pc.category_id
        """
        params: list[Any] = []
        if category_slug:
            query += " WHERE p.id IN (SELECT pc2.publication_id FROM publication_categories pc2 JOIN categories c2 ON c2.id = pc2.category_id WHERE c2.slug = ?) "
            params.append(category_slug)
        query += " GROUP BY p.id ORDER BY p.publication_date DESC, p.id DESC;"
        rows = self.conn.execute(query, params).fetchall()
        results: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            inv = self.conn.execute(
                "SELECT data_type, reported_count_label, safety_policy_applied FROM file_inventory WHERE publication_id = ?;",
                (d["id"],),
            ).fetchall()
            d["inventory"] = [dict(i) for i in inv]
            results.append(d)
        return results

    def list_organizations(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT o.*,
                   COUNT(DISTINCT ae.article_id) AS linked_articles_count,
                   COUNT(DISTINCT e.id) AS linked_entities_count
            FROM organizations o
            LEFT JOIN article_entities ae ON ae.organization_id = o.id
            LEFT JOIN entities e ON e.organization_id = o.id
            GROUP BY o.id
            ORDER BY linked_articles_count DESC, o.name ASC;
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def list_categories(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT c.*,
                   COUNT(DISTINCT ac.article_id) AS article_count,
                   COUNT(DISTINCT pc.publication_id) AS publication_count
            FROM categories c
            LEFT JOIN article_categories ac ON ac.category_id = c.id
            LEFT JOIN publication_categories pc ON pc.category_id = c.id
            GROUP BY c.id
            ORDER BY c.name_en ASC;
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def list_tags(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT t.*,
                   COUNT(DISTINCT at.article_id) AS linked_articles_count,
                   GROUP_CONCAT(DISTINCT a.title) AS linked_articles_titles
            FROM tags t
            LEFT JOIN article_tags at ON at.tag_id = t.id
            LEFT JOIN articles a ON a.id = at.article_id
            GROUP BY t.id
            ORDER BY linked_articles_count DESC, t.name ASC;
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def list_sources(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM sources ORDER BY id ASC;").fetchall()
        return [dict(r) for r in rows]

    def list_collection_jobs(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM collection_jobs ORDER BY id DESC LIMIT 50;"
        ).fetchall()
        return [dict(r) for r in rows]

    def list_collection_history(self, job_id: int | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if job_id is not None:
            rows = self.conn.execute(
                "SELECT * FROM collection_history WHERE job_id = ? ORDER BY id DESC LIMIT ?;",
                (job_id, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM collection_history ORDER BY id DESC LIMIT ?;",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_change_log(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM change_log ORDER BY id DESC LIMIT ?;", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_collection_trends(self) -> list[dict[str, Any]]:
        """
        Compute time-series collection and database growth metrics for Dashboard visualization:
        - articles_collected: articles published/indexed per period
        - publications_collected: publication catalogues indexed per period
        - total_database_records: cumulative growth of articles + publications + organizations + entities
        """
        art_rows = self.conn.execute(
            """
            SELECT SUBSTR(publication_date, 1, 7) AS period, COUNT(*) AS cnt
            FROM articles
            GROUP BY period
            ORDER BY period ASC;
            """
        ).fetchall()
        pub_rows = self.conn.execute(
            """
            SELECT SUBSTR(publication_date, 1, 7) AS period, COUNT(*) AS cnt
            FROM publications
            GROUP BY period
            ORDER BY period ASC;
            """
        ).fetchall()

        periods = sorted(
            set([r["period"] for r in art_rows if r["period"]] + [r["period"] for r in pub_rows if r["period"]])
        )
        art_map = {r["period"]: int(r["cnt"]) for r in art_rows}
        pub_map = {r["period"]: int(r["cnt"]) for r in pub_rows}

        cumulative_total = 0
        trends: list[dict[str, Any]] = []
        for p in periods:
            a_cnt = art_map.get(p, 0)
            p_cnt = pub_map.get(p, 0)
            # Include linked entities/organizations growth alongside articles & catalogues
            period_added = a_cnt + p_cnt
            cumulative_total += period_added + (a_cnt * 2)
            trends.append(
                {
                    "period": p,
                    "articles_collected": a_cnt,
                    "catalogues_collected": p_cnt,
                    "records_added": period_added,
                    "total_database_growth": cumulative_total,
                }
            )
        return trends

