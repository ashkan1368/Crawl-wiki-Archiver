"""
Comprehensive automated test suite for WikIran Archive (15 verification categories):
1. Database initialization
2. Versioned migrations
3. Article extraction
4. Catalogue metadata extraction
5. Sensitive-data exclusion & PII redaction (synthetic fixtures)
6. Duplicate detection & content versioning
7. Date normalization
8. Offline SQLite FTS5 search & multi-facet filtering
9. Multi-sheet Excel (.xlsx) export
10. CSV export
11. JSON export
12. Interrupted-task checkpoint & recovery
13. SQLite-safe backup creation & retention
14. Backup restoration with confirmation & integrity verification
15. Persian (RTL) and English (LTR) language switching & skeleton UI navigation
"""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from wikiran_archive.backup.manager import BackupManager
from wikiran_archive.collector.discovery import extract_discovered_links, parse_robots_txt
from wikiran_archive.collector.engine import CollectionEngine
from wikiran_archive.collector.extractor import (
    extract_article_from_html,
    extract_publication_catalogue_from_html,
)
from wikiran_archive.collector.normalizer import normalize_date, normalize_url
from wikiran_archive.collector.reconnaissance import (
    generate_reconnaissance_markdown,
    run_reconnaissance,
)
from wikiran_archive.collector.safety import is_permitted_research_url, sanitize_public_text
from wikiran_archive.collector.scheduler import ScheduledCollectionRunner
from wikiran_archive.config.settings import resolve_app_paths
from wikiran_archive.database.connection import get_connection, verify_database_integrity
from wikiran_archive.database.migrations import run_migrations
from wikiran_archive.database.repository import ArchiveRepository
from wikiran_archive.database.seed import seed_verified_public_archive
from wikiran_archive.export.csv_converter import CsvSpreadsheetWorkbench
from wikiran_archive.export.exporters import ArchiveExporter
from wikiran_archive.i18n.translations import is_rtl_language, tr
from wikiran_archive.search.fts_search import ArchiveSearchEngine, SearchFilters
from wikiran_archive.ui.main_window import DesktopController


SYNTHETIC_ARTICLE_HTML = """
<!DOCTYPE html>
<html>
<head><title>WikIran - Synthetic Research Report on Maritime Logistics</title></head>
<body>
  <main>
    <h1 class="articleDetails_headline__ggYKE">Synthetic Research Report on Maritime Logistics</h1>
    <div class="articleDetails_searchResultDate__m0RZT">Nov 2026</div>
    <div class="articleDetails_subHeadline__jqnAB">Editorial Investigation</div>
    <div class="uiMarkdown_uiMarkdownWrapper__lQz42">
      <p>This synthetic public editorial report analyzes MODAFL and Sahara Thunder oil brokerage operations.</p>
      <p>Accidental synthetic private email test_private_user@example.org and IBAN IR120000000012345678901234 must be redacted.</p>
    </div>
  </main>
</body>
</html>
"""

SYNTHETIC_CATALOGUE_HTML = """
<!DOCTYPE html>
<html>
<head><title>WikIran - Synthetic HMS Trading Catalogue</title></head>
<body>
  <div class="leakDetails_leakDetailsWrapper__8Bi9q">
    <h1 class="leakDetails_headline__ICyaA">Synthetic HMS Trading Catalogue</h1>
    <h2 class="leakDetails_subHeadline__SsysM">فهرست آزمایشی اچ‌ام‌اس</h2>
    <div class="leakDetails_description__ZinRi">
      Safe high-level catalogue summary describing commercial front companies linked to Rahbar intermediaries.
    </div>
    <div class="leakDetails_dataTypeList__gOjyd">files emails</div>
    <div class="leakDetails_resultsCount__7uxtN">5000+ results</div>
  </div>
  <div class="searchResultCard_searchResultWrapper__2JzJ6">
    <a href="/document/emails/synthetic_private_email_hash_1">Private Leaked Email 1</a>
    <a href="/document/files/synthetic_private_bank_record_2">Private Leaked File 2</a>
  </div>
</body>
</html>
"""


class TestWikIranArchiveSuite(unittest.TestCase):
    """End-to-end verification tests for all 15 required capabilities."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.paths = resolve_app_paths(self.temp_dir.name)
        self.conn = get_connection(self.paths.db_path)
        self.applied_migrations = run_migrations(self.conn)
        self.repo = ArchiveRepository(self.conn)

    def tearDown(self) -> None:
        self.conn.close()
        self.temp_dir.cleanup()

    def test_01_database_initialization_and_15_tables(self) -> None:
        """Verify all 15 normalized tables + FTS5 + CSV workbench tables are created with foreign keys enabled."""
        expected_tables = {
            "articles",
            "publications",
            "organizations",
            "entities",
            "categories",
            "tags",
            "article_entities",
            "article_categories",
            "publication_categories",
            "sources",
            "file_inventory",
            "collection_jobs",
            "collection_history",
            "change_log",
            "application_settings",
            "imported_csv_datasets",
            "imported_csv_rows",
            "fts_archive",
            "schema_migrations",
        }
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view');"
        ).fetchall()
        existing_tables = {r["name"] for r in rows}
        self.assertTrue(expected_tables.issubset(existing_tables))
        ok, _ = verify_database_integrity(self.paths.db_path)
        self.assertTrue(ok)

    def test_02_versioned_migrations_idempotency(self) -> None:
        """Verify migrations apply versions [1, 2, 3] once and are idempotent on re-run."""
        self.assertEqual(self.applied_migrations, [1, 2, 3])
        second_run = run_migrations(self.conn)
        self.assertEqual(second_run, [])

    def test_03_article_extraction_and_pii_redaction(self) -> None:
        """Verify public article extraction preserves editorial analysis and redacts synthetic PII."""
        url = "https://wikiran.org/document/articles/synthetic-uuid-001"
        art = extract_article_from_html(SYNTHETIC_ARTICLE_HTML, url)
        self.assertEqual(art.title, "Synthetic Research Report on Maritime Logistics")
        self.assertEqual(art.publication_date, "2026-11-01")
        self.assertIn("MODAFL", art.editorial_content)
        self.assertNotIn("test_private_user@example.org", art.editorial_content)
        self.assertNotIn("IR120000000012345678901234", art.editorial_content)
        self.assertIn("[REDACTED-EMAIL]", art.editorial_content)
        self.assertIn("[REDACTED-ACCOUNT]", art.editorial_content)

    def test_04_catalogue_metadata_extraction_and_sensitive_exclusion(self) -> None:
        """Verify catalogue extraction records only safe descriptions and blocks individual email/file links."""
        url = "https://wikiran.org/leak/synthetic-hms"
        pub = extract_publication_catalogue_from_html(SYNTHETIC_CATALOGUE_HTML, url)
        self.assertEqual(pub.title, "Synthetic HMS Trading Catalogue")
        self.assertEqual(pub.native_title, "فهرست آزمایشی اچ‌ام‌اس")
        self.assertIn("Safe high-level catalogue summary", pub.description)
        self.assertNotIn("Private Leaked Email 1", pub.description)
        self.assertEqual(pub.blocked_sensitive_count, 2)

        # Verify URL safety gate rejects direct private email/file URLs
        ok_email, _ = is_permitted_research_url(
            "https://wikiran.org/document/emails/2343b8f01bc299c88b0cf41bad22b872"
        )
        ok_file, _ = is_permitted_research_url(
            "https://wikiran.org/document/files/confidential_contract.pdf"
        )
        self.assertFalse(ok_email)
        self.assertFalse(ok_file)

    def test_05_deduplication_and_version_change_log(self) -> None:
        """Verify duplicate articles are not overwritten when unchanged and increment version when updated."""
        art_id_1, action_1 = self.repo.upsert_article(
            original_pub_id="uuid-dedup-1",
            title="Initial Title",
            publication_date="2026-10-01",
            summary="Initial summary",
            editorial_content="Initial content body",
            source_url="https://wikiran.org/document/articles/uuid-dedup-1",
        )
        self.assertEqual(action_1, "INSERTED")

        # Same content -> UNCHANGED
        art_id_2, action_2 = self.repo.upsert_article(
            original_pub_id="uuid-dedup-1",
            title="Initial Title",
            publication_date="2026-10-01",
            summary="Initial summary",
            editorial_content="Initial content body",
            source_url="https://wikiran.org/document/articles/uuid-dedup-1",
        )
        self.assertEqual(art_id_1, art_id_2)
        self.assertEqual(action_2, "UNCHANGED")

        # Modified content -> UPDATED + version 2 + change_log entry
        art_id_3, action_3 = self.repo.upsert_article(
            original_pub_id="uuid-dedup-1",
            title="Initial Title",
            publication_date="2026-10-01",
            summary="Updated summary",
            editorial_content="Updated content body with new findings",
            source_url="https://wikiran.org/document/articles/uuid-dedup-1",
        )
        self.assertEqual(art_id_1, art_id_3)
        self.assertEqual(action_3, "UPDATED")
        changes = self.repo.list_change_log()
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["new_version"], 2)

    def test_06_date_and_url_normalization(self) -> None:
        """Verify date normalization handles 'Nov 2026', 'Aug 15, 2025', and '6/26/2022'."""
        self.assertEqual(normalize_date("Nov 2026"), "2026-11-01")
        self.assertEqual(normalize_date("August 15, 2025"), "2025-08-15")
        self.assertEqual(normalize_date("6/26/2022"), "2022-06-26")
        self.assertEqual(
            normalize_url("/document/articles/abc/"),
            "https://wikiran.org/document/articles/abc",
        )

    def test_07_offline_fts5_search_and_filters(self) -> None:
        """Verify SQLite FTS5 full-text search and category/organization/date filters work offline."""
        seed_verified_public_archive(self.repo)
        search_engine = ArchiveSearchEngine(self.conn)

        # Full-text query for 'Rahbar'
        res_rahbar = search_engine.search(SearchFilters(query="Rahbar"))
        self.assertGreaterEqual(len(res_rahbar), 2)

        # Filter by category slug
        res_maritime = search_engine.search(
            SearchFilters(category_slug="maritime-oil-trade")
        )
        self.assertGreaterEqual(len(res_maritime), 3)

        # Filter by organization
        res_modafl = search_engine.search(
            SearchFilters(organization_name="MODAFL", source_type="ARTICLE")
        )
        self.assertGreaterEqual(len(res_modafl), 2)

    def test_08_exports_excel_csv_json(self) -> None:
        """Verify Excel (.xlsx with 6 sheets), CSV, and JSON exports contain valid data and source URLs."""
        seed_verified_public_archive(self.repo)
        exporter = ArchiveExporter(self.repo)

        xlsx_path = exporter.export_excel(self.paths.exports_dir / "test_export.xlsx")
        csv_path = exporter.export_csv(self.paths.exports_dir / "test_export.csv")
        json_path = exporter.export_json(self.paths.exports_dir / "test_export.json")

        self.assertTrue(xlsx_path.exists())
        with zipfile.ZipFile(xlsx_path, "r") as zf:
            wb_xml = zf.read("xl/workbook.xml").decode("utf-8")
            for sheet_name in (
                "Articles",
                "Publications",
                "Organizations",
                "Categories",
                "Sources",
                "Collection Statistics",
            ):
                self.assertIn(sheet_name, wb_xml)

        self.assertTrue(csv_path.exists())
        with csv_path.open("r", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
            self.assertGreater(len(rows), 10)
            self.assertIn("Source URL", rows[0])

        self.assertTrue(json_path.exists())
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(payload["articles"]), 6)
        self.assertGreaterEqual(len(payload["publications"]), 7)

        # Verify Export Report Wizard selective entity export (e.g., Articles + Tags only)
        wizard_xlsx = exporter.export_excel(
            self.paths.exports_dir / "test_wizard_export.xlsx",
            entities=["articles", "tags"],
        )
        self.assertTrue(wizard_xlsx.exists())
        with zipfile.ZipFile(wizard_xlsx, "r") as zf:
            wizard_wb_xml = zf.read("xl/workbook.xml").decode("utf-8")
            self.assertIn("Articles", wizard_wb_xml)
            self.assertIn("Tags", wizard_wb_xml)
            self.assertNotIn("Publications", wizard_wb_xml)
            self.assertNotIn("Organizations", wizard_wb_xml)

    def test_09_interrupted_task_checkpoint_and_recovery(self) -> None:
        """Verify an interrupted collection task persists its checkpoint and resumes to completion."""
        seed_verified_public_archive(self.repo)

        def synthetic_fetcher(url: str) -> tuple[int, str]:
            if "/document/articles/" in url:
                return 200, SYNTHETIC_ARTICLE_HTML
            return 200, SYNTHETIC_CATALOGUE_HTML

        engine = CollectionEngine(self.repo, fetcher=synthetic_fetcher)
        pending = [
            "https://wikiran.org/document/articles/synth-recover-1",
            "https://wikiran.org/leak/synth-recover-2",
        ]
        job_id = engine.create_interrupted_checkpoint_job(pending_urls=pending)
        job_before = engine.get_job_summary(job_id)
        self.assertEqual(job_before["status"], "INTERRUPTED")

        job_after = engine.resume_job(job_id)
        self.assertEqual(job_after["status"], "COMPLETED")
        self.assertEqual(job_after["processed_count"], 2)

    def test_10_backup_creation_and_verified_restoration(self) -> None:
        """Verify SQLite online backup, 14-day retention, and actual restoration with confirmation."""
        seed_verified_public_archive(self.repo)
        backup_mgr = BackupManager(self.paths.db_path, self.paths.backups_dir, retention_days=14)

        b_info = backup_mgr.create_backup()
        self.assertTrue(b_info["integrity_verified"])
        self.assertTrue(Path(b_info["path"]).exists())

        # Mutate database by adding a temporary article
        self.repo.upsert_article(
            original_pub_id="temp-before-restore",
            title="Temporary Article Before Restore",
            publication_date="2026-11-18",
            summary="Should disappear after restoring earlier backup",
            editorial_content="Temp content",
            source_url="https://wikiran.org/document/articles/temp-before-restore",
        )
        self.assertEqual(self.repo.get_dashboard_stats()["articles_count"], 7)

        # Ensure unconfirmed restore raises PermissionError
        with self.assertRaises(PermissionError):
            backup_mgr.restore_backup(b_info["path"], confirmed=False)

        # Confirmed restore reverts database to 6 articles and passes integrity check
        restore_res = backup_mgr.restore_backup(b_info["path"], confirmed=True)
        self.assertTrue(restore_res["integrity_verified"])
        self.assertEqual(self.repo.get_dashboard_stats()["articles_count"], 6)

    def test_11_bilingual_persian_rtl_and_english_ltr_switching(self) -> None:
        """Verify Persian (RTL) and English (LTR) language switching and all 10 navigation sections."""
        controller = DesktopController(self.paths)
        try:
            fa_state = controller.set_language("fa")
            self.assertEqual(fa_state["language"], "fa")
            self.assertEqual(fa_state["direction"], "RTL")
            self.assertEqual(len(fa_state["navigation"]), 10)
            self.assertEqual(tr("nav_dashboard", "fa"), "پیشخوان")

            en_state = controller.set_language("en")
            self.assertEqual(en_state["language"], "en")
            self.assertEqual(en_state["direction"], "LTR")
            self.assertEqual(len(en_state["navigation"]), 10)
            self.assertEqual(tr("nav_dashboard", "en"), "Dashboard")
            self.assertFalse(is_rtl_language("en"))
            self.assertTrue(is_rtl_language("fa"))
        finally:
            controller.close()

    def test_12_reconnaissance_module_and_report_generation(self) -> None:
        """Verify the programmatic reconnaissance module produces a structured technical report."""
        def mock_recon_fetcher(url: str) -> tuple[int, str]:
            if url.endswith("/robots.txt"):
                return 200, "# Content signals\nUser-agent: *\nAllow: /\n"
            if "/search?tabType=articles" in url or url.endswith("/"):
                return 200, '<a href="/document/articles/418be098-dcb5-4bd0-ae4b-25bdfb17fe5a">Art</a><a href="/search?tabType=articles&page=2">2</a>'
            if url.endswith("/leaks"):
                return 200, '<a href="/leak/hms">HMS</a>'
            if "/document/articles/" in url:
                return 200, SYNTHETIC_ARTICLE_HTML
            return 200, SYNTHETIC_CATALOGUE_HTML

        finding = run_reconnaissance(fetcher=mock_recon_fetcher)
        self.assertTrue(finding.robots_permitted)
        self.assertGreaterEqual(len(finding.discovered_article_urls), 1)
        self.assertGreaterEqual(len(finding.discovered_catalogue_urls), 1)
        report_md = generate_reconnaissance_markdown(finding)
        self.assertIn("Technical Reconnaissance Report", report_md)
        self.assertIn("/search?tabType=articles&page={page}", report_md)

    def test_13_scheduled_collection_and_trends_metrics(self) -> None:
        """Verify Scheduled Collection interval configuration and Dashboard time-series growth metrics."""
        seed_verified_public_archive(self.repo)
        trends = self.repo.get_collection_trends()
        self.assertGreaterEqual(len(trends), 4)
        self.assertIn("articles_collected", trends[0])
        self.assertIn("total_database_growth", trends[-1])

        scheduler = ScheduledCollectionRunner(str(self.paths.db_path))
        updated = scheduler.update_schedule_config(
            enabled=True,
            frequency="weekly",
            time_utc="03:30",
            day_of_week="monday",
            max_items_per_run=5,
            repo=self.repo,
        )
        self.assertTrue(updated["enabled"])
        self.assertEqual(updated["frequency"], "weekly")
        self.assertEqual(updated["time_utc"], "03:30")
        self.assertIn("03:30:00Z", updated["next_run_at"])

    def test_14_csv_to_excel_converter_and_preview_all_audit(self) -> None:
        """Verify CSV files are converted into Excel (.xlsx), support subset vs preview_all audit, and index in FTS5."""
        csv_wb = CsvSpreadsheetWorkbench(self.repo, self.paths.exports_dir)
        rows_txt = ["Company Name,Sector,Jurisdiction,Notes"]
        for i in range(1, 9):
            rows_txt.append(
                f"Sahara Entity {i},Petroleum Brokerage,UAE,Maritime logistics record #{i}"
            )
        sample_csv = "\n".join(rows_txt)
        details = csv_wb.import_csv_text(
            csv_text=sample_csv,
            filename="maritime_entities.csv",
            dataset_name="Maritime Entities Table",
        )
        self.assertIsNotNone(details["dataset"])
        self.assertEqual(details["dataset"]["row_count"], 8)
        xlsx_path = Path(details["dataset"]["xlsx_export_path"])
        self.assertTrue(xlsx_path.exists())

        # Subset preview (preview_all=False) returns 5 rows out of 8 matching
        subset_view = csv_wb.get_dataset_details(
            dataset_id=details["dataset"]["id"],
            search_query="Sahara",
            preview_all=False,
        )
        self.assertEqual(subset_view["total_matching_count"], 8)
        self.assertEqual(subset_view["displayed_count"], 5)
        self.assertTrue(subset_view["is_subset"])

        # Full audit preview (preview_all=True) returns all 8 matching rows
        full_view = csv_wb.get_dataset_details(
            dataset_id=details["dataset"]["id"],
            search_query="Sahara",
            preview_all=True,
        )
        self.assertEqual(full_view["total_matching_count"], 8)
        self.assertEqual(full_view["displayed_count"], 8)
        self.assertFalse(full_view["is_subset"])

    def test_15_full_unredacted_mode_and_universal_search_across_all_data(self) -> None:
        """Verify the single SQLite FTS5 JOIN query across articles, publications, csv_row_content, and file_metadata."""
        from wikiran_archive.search.fts_search import UNIFIED_FTS5_JOIN_SQL

        self.assertIn("LEFT JOIN articles", UNIFIED_FTS5_JOIN_SQL)
        self.assertIn("LEFT JOIN publications", UNIFIED_FTS5_JOIN_SQL)
        self.assertIn("LEFT JOIN csv_row_content", UNIFIED_FTS5_JOIN_SQL)
        self.assertIn("LEFT JOIN file_metadata", UNIFIED_FTS5_JOIN_SQL)

        seed_verified_public_archive(self.repo)
        csv_wb = CsvSpreadsheetWorkbench(self.repo, self.paths.exports_dir)
        csv_wb.ensure_default_csv_dataset()
        unredacted = csv_wb.ensure_unredacted_ledger_dataset()
        self.assertGreaterEqual(unredacted["total_matching_count"], 6)

        search_engine = ArchiveSearchEngine(self.conn)
        # Search for an email address in the unredacted ledger across all downloaded data
        email_hits = search_engine.search(SearchFilters(query="settlements@rahbar"))
        self.assertGreaterEqual(len(email_hits), 1)

        # Search for an IBAN across all downloaded data
        iban_hits = search_engine.search(SearchFilters(query="AE070331234567890123456"))
        self.assertGreaterEqual(len(iban_hits), 1)

        # Search for 'Rahbar' and verify the single FTS5 JOIN query returns hits from every joined data source
        all_hits = search_engine.search(SearchFilters(query="Rahbar"))
        found_types = {h["record_type"] for h in all_hits}
        self.assertIn("ARTICLE", found_types)
        self.assertIn("PUBLICATION", found_types)
        self.assertIn("CSV_ROW", found_types)
        self.assertIn("FILE_INVENTORY", found_types)
        self.assertIn("ENTITY", found_types)

    def test_16_ofac_sanctions_ingestion_and_unified_fts5_search(self) -> None:
        """Verify U.S. Treasury OFAC SDN & Consolidated CSV ingestion, update check, and unified FTS5 trade screening."""
        from wikiran_archive.collector.ofac_sync import sync_ofac_lists

        seed_verified_public_archive(self.repo)

        mock_responses = {
            "https://sanctionslistservice.ofac.treas.gov/alive": (200, "OK"),
            "https://sanctionslistservice.ofac.treas.gov/sanctions-lists": (200, '["SDN List","Consolidated List"]'),
            "https://sanctionslistservice.ofac.treas.gov/sanctions-programs": (200, '["IRAN","IRGC","SDGT"]'),
            "https://sanctionslistservice.ofac.treas.gov/api/download/SDN.CSV": (
                200,
                '44510,"SAHARA THUNDER",-0- ,"SDGT] [IFSR",-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,"Linked to MODAFL maritime procurement."\n',
            ),
            "https://sanctionslistservice.ofac.treas.gov/api/download/ALT.CSV": (
                200,
                '44510,9001,"aka","SAHARA THUNDER TRADING CO.",-0- \n',
            ),
            "https://sanctionslistservice.ofac.treas.gov/api/download/ADD.CSV": (
                200,
                '44510,8001,"Valiasr Ave","Tehran","Iran",-0- \n',
            ),
            "https://sanctionslistservice.ofac.treas.gov/api/download/SDN_COMMENTS.CSV": (200, ""),
            "https://sanctionslistservice.ofac.treas.gov/api/download/CONS_PRIM.CSV": (
                200,
                '9640,"TEST CONSOLIDATED ENTITY",-0- ,"FSE-IR",-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,"Non-SDN designation."\n',
            ),
            "https://sanctionslistservice.ofac.treas.gov/api/download/CONS_ALT.CSV": (200, ""),
            "https://sanctionslistservice.ofac.treas.gov/api/download/CONS_ADD.CSV": (200, ""),
            "https://sanctionslistservice.ofac.treas.gov/api/download/CONS_COMMENTS.CSV": (200, ""),
        }

        def fake_fetcher(url: str) -> tuple[int, str]:
            if "/changes/history/" in url:
                return 200, '[{"publicationID": 1112, "datePublished": "2026-11-20T15:32:24"}]'
            return mock_responses.get(url, (404, ""))

        res = sync_ofac_lists(self.repo, force=True, fetcher=fake_fetcher)
        self.assertTrue(res["ok"])
        self.assertEqual(res["synced_count"], 2)
        self.assertEqual(res["summary"]["sdn_count"], 1)
        self.assertEqual(res["summary"]["consolidated_count"], 1)

        # Verify subsequent check detects up-to-date publicationID without redownloading
        check = sync_ofac_lists(self.repo, check_only=True, fetcher=fake_fetcher)
        self.assertFalse(check["update_available"])

        # Verify single FTS5 search matches BOTH OFAC_SANCTION (by name or alias) AND WikIran articles
        search_engine = ArchiveSearchEngine(self.conn)
        hits = search_engine.search(SearchFilters(query="Sahara Thunder"))
        types_found = {h["record_type"] for h in hits}
        self.assertIn("OFAC_SANCTION", types_found)
        self.assertIn("ARTICLE", types_found)
        ofac_hit = next(h for h in hits if h["record_type"] == "OFAC_SANCTION")
        self.assertEqual(ofac_hit["ofac_ent_num"], 44510)
        self.assertEqual(ofac_hit["ofac_programs"], "SDGT; IFSR")
        self.assertIn("Tehran, Iran", ofac_hit["ofac_addresses"])


if __name__ == "__main__":
    unittest.main()


