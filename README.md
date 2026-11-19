# WikIran Archive — Windows 11 Desktop Research Application

**WikIran Archive** is a bilingual (Persian RTL / English LTR) desktop research archive and publication-catalogue manager designed for non-technical office clerks and system administrators.

It organizes publicly published editorial articles (`/document/articles/<uuid>`) and safe publication-catalogue metadata (`/leaks`, `/archives`, `/leak/<slug>`) from `https://wikiran.org/` into a normalized local SQLite database with offline SQLite FTS5 full-text search, multi-sheet Excel (`.xlsx`), CSV, and JSON exports, checkpointed incremental updates, and automated 14-day SQLite backups.

---

## Key Capabilities & Safety Scope
1. **Strict Scope & Safety Guardrails (`wikiran_archive/collector/safety.py`)**:
   - Collects **only** permitted public editorial articles and high-level publication catalogue summaries.
   - **Never** downloads, indexes, or stores exposed private correspondence (`/document/emails/*`), banking records, identity documents, confidential contracts (`/document/files/*`), or personal identifiers.
2. **Programmatic Reconnaissance (`wikiran_archive/collector/reconnaissance.py`)**:
   - Inspects `robots.txt`, public navigation paths, and pagination patterns (`/search?tabType=articles&page=N`), and produces `RECONNAISSANCE_REPORT.md`.
3. **Normalized 15-Table SQLite Schema + FTS5 (`wikiran_archive/database/`)**:
   - Versioned migrations creating `articles`, `publications`, `organizations`, `entities`, `categories`, `tags`, `article_entities`, `article_categories`, `publication_categories`, `sources`, `file_inventory`, `collection_jobs`, `collection_history`, `change_log`, `application_settings`, and `fts_archive`.
4. **Bilingual Desktop UI (`wikiran_archive/ui/main_window.py`)**:
   - Native PySide6 Windows 11 desktop interface with 10 primary navigation sections, Clerk Quick Actions, Administrator diagnostics, and full Persian (RTL) and English (LTR) support.

---

## Quick Start (Development & Testing)

```bash
# Run the automated 12-test verification suite
python3 -m unittest discover -s tests -v

# Run programmatic website reconnaissance
python3 -m wikiran_archive.main --recon

# Initialize and seed the local SQLite database
python3 -m wikiran_archive.main --init-db

# Launch the native PySide6 desktop GUI on Windows 11
python -m wikiran_archive.main --gui
```

---

## Repository Deliverables
- `wikiran_archive/` — Modular Python 3 desktop application source code
- `tests/test_wikiran_archive.py` — Automated verification test suite
- `RECONNAISSANCE_REPORT.md` — Technical reconnaissance report on `https://wikiran.org/`
- `ARCHITECTURE.md` — Layered architecture and data flow specification
- `DATABASE_SCHEMA.md` — Normalized 15-table SQLite + FTS5 schema documentation
- `OPERATOR_MANUAL_FA.md` — Persian operator manual for clerks
- `OPERATOR_MANUAL_EN.md` — English operator & administrator manual
- `PROJECT_STATUS.md` — Phase-by-phase engineering status ledger
- `requirements.txt` — Python dependencies
- `scripts/build_windows.bat` — Windows 11 PyInstaller build script
- `installer/wikiran_archive_setup.iss` — Inno Setup Windows 11 installer configuration
- `samples/wikiran_sample_sanitized.db` — Pre-seeded sanitized sample SQLite database
- `samples/wikiran_export_template.xlsx` — Multi-sheet Excel export template
