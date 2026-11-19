# Project Status & Verification Ledger — WikIran Archive
**Version:** 1.0.0
**Last Updated:** 2026-11-18

---

## Stage & Feature Verification Matrix

| Phase / Module | Status | Automated Test Coverage | Verification Evidence |
| :--- | :--- | :--- | :--- |
| **PHASE 1 — Website Reconnaissance** | **Verified** | `test_12_reconnaissance_module_and_report_generation` | Live inspection of `https://wikiran.org/robots.txt`, `/leaks`, `/archives`, `/search?tabType=articles&page=1..2`, and sample article/catalogue pages documented in `RECONNAISSANCE_REPORT.md` and `wikiran_archive/collector/reconnaissance.py`. |
| **PHASE 2 — Normalized SQLite Schema (15 Tables) & Migrations** | **Verified** | `test_01_database_initialization_and_15_tables`, `test_02_versioned_migrations_idempotency` | All 15 normalized tables (`articles`, `publications`, `organizations`, `entities`, `categories`, `tags`, `article_entities`, `article_categories`, `publication_categories`, `sources`, `file_inventory`, `collection_jobs`, `collection_history`, `change_log`, `application_settings`) + `fts_archive` created and verified with `PRAGMA integrity_check`. |
| **PHASE 3 — Collection Engine, Safety Guardrails & Recovery** | **Verified** | `test_03_article_extraction_and_pii_redaction`, `test_04_catalogue_metadata_extraction_and_sensitive_exclusion`, `test_05_deduplication_and_version_change_log`, `test_06_date_and_url_normalization`, `test_09_interrupted_task_checkpoint_and_recovery` | Blocks `/document/emails/*` and `/document/files/*`, redacts synthetic PII, deduplicates via SHA-256 content hashes, logs version bumps in `change_log`, and recovers interrupted jobs from JSON checkpoints. |
| **PHASE 4 — Offline SQLite FTS5 Search & Exports (Excel/CSV/JSON)** | **Verified** | `test_07_offline_fts5_search_and_filters`, `test_08_exports_excel_csv_json` | Offline FTS5 search with date, category, organization, source type, and status filters; multi-sheet `.xlsx` (6 sheets), `.csv`, and `.json` exports verified. |
| **PHASE 5 — Bilingual Desktop UI (PySide6 + Interactive Workbench)** | **Verified** | `test_11_bilingual_persian_rtl_and_english_ltr_switching` | 10 primary navigation sections, Clerk Quick Actions, Administrator console, and Persian (RTL) / English (LTR) switching with persistent language setting. |
| **PHASE 6 — Backup, Restore & Quality Assurance** | **Verified** | `test_10_backup_creation_and_verified_restoration` | Online SQLite backup API, 14-day retention, pre-restore safety snapshot, explicit confirmation check, and 12/12 unit & integration tests passing. |
| **PHASE 7 — Windows 11 Packaging & Delivery Artifacts** | **Verified** | `scripts/build_windows.bat`, `installer/wikiran_archive_setup.iss` | Complete source code, documentation, build scripts, Inno Setup script, pre-seeded sanitized sample database (`samples/wikiran_sample_sanitized.db`), and Excel export template (`samples/wikiran_export_template.xlsx`) generated and verified. |
