# Architecture Specification — WikIran Archive
**Version:** 1.0.0
**Target Platform:** Windows 11 Desktop (Python 3 + PySide6) & Local Web Companion Bridge

---

## 1. Architectural Overview

**WikIran Archive** follows a strict layered architecture with clear separation of concerns so that UI logic, network collection, HTML parsing, sensitive-data filtering, persistence, search, exports, and backups operate as independent, testable Python modules.

```
wikiran_archive/
├── __init__.py
├── main.py                      # Application entry point (PySide6 Desktop GUI + CLI runner)
├── config/
│   ├── __init__.py
│   └── settings.py              # AppData directory management, default polite collection config
├── logging_utils/
│   ├── __init__.py
│   └── logger.py                # Rotating technical diagnostic log vs. friendly clerk messages
├── database/
│   ├── __init__.py
│   ├── connection.py            # SQLite connection factory (WAL mode, foreign keys)
│   ├── migrations.py            # Versioned SQLite schema migrations & FTS5 triggers
│   ├── repository.py            # CRUD, deduplication, version bumps, change_log recording
│   └── seed.py                  # Verified real public metadata + synthetic test fixture seeder
├── collector/
│   ├── __init__.py
│   ├── safety.py                # Strict URL & PII/sensitive-content exclusion guardrails
│   ├── normalizer.py            # Date, category, URL, and text normalization + SHA-256 hashing
│   ├── discovery.py             # robots.txt inspector, public navigation & pagination discovery
│   ├── extractor.py             # Article & publication-catalogue safe HTML parser
│   └── engine.py                # Polite HTTPX engine, checkpoints, recovery, incremental sync
├── search/
│   ├── __init__.py
│   └── fts_search.py            # Offline SQLite FTS5 full-text search with multi-facet filters
├── export/
│   ├── __init__.py
│   └── exporters.py             # Multi-sheet OpenPyXL/XML Excel (.xlsx), CSV, and JSON exporters
├── backup/
│   ├── __init__.py
│   └── manager.py               # SQLite online backup API, 14-day rotation, integrity verify & restore
├── i18n/
│   ├── __init__.py
│   └── translations.py          # Complete Persian (FA - RTL) & English (EN - LTR) dictionary
└── ui/
    ├── __init__.py
    └── main_window.py           # PySide6 MainWindow with 10 views, Clerk/Admin modes, RTL/LTR layout
```

---

## 2. Data Storage Location (Outside Installation Directory)
Per Windows 11 desktop engineering rules, application data is never stored inside `C:\Program Files\WikIran Archive`. Instead, `wikiran_archive/config/settings.py` resolves:
- **Windows:** `%LOCALAPPDATA%\WikIranArchive\`
  - `data/wikiran_archive.db` (SQLite database)
  - `backups/` (Daily automated and manual SQLite backups)
  - `exports/` (Default export output directory)
  - `logs/diagnostic.log` (Administrator technical log)
- **Linux / Portable / Test Override:** Configurable via `WIKIRAN_DATA_DIR` environment variable or constructor path.

---

## 3. Safety & Ethical Filtering Architecture (`collector/safety.py`)
Every discovered URL and extracted record passes through three mandatory gates before reaching the database:
1. **URL Path Gate**:
   - Explicitly permits: `/`, `/leaks`, `/archives`, `/about`, `/search?tabType=articles*`, `/document/articles/<uuid>`, `/leak/<slug>`.
   - Explicitly blocks: `/document/emails/*`, `/document/files/*`, `/files/leaks/*`, and any raw document extensions (`.pst`, `.eml`, `.msg`, `.pdf`, `.xlsx`, `.zip`, `.rar`).
2. **DOM Strip Gate**:
   - On `/leak/<slug>` catalogue pages, strips all `.searchResultCard_*` nodes (which preview individual leaked emails/files) prior to extracting the publication header description.
3. **Content Redaction Gate**:
   - Scans text fields for private email addresses, IBAN/account numbers, national ID patterns, and phone numbers, replacing any accidental match with `[REDACTED-SENSITIVE]` while preserving public organizational and institutional names (e.g., `MODAFL`, `IRGC`, `Bank Sepah`, `Sahara Thunder`).

---

## 4. Checkpoints, Recovery & Incremental Collection (`collector/engine.py`)
- Each collection run creates a row in `collection_jobs` and `collection_history`.
- Discovered URLs are queued in `checkpoint_state` (JSON serialized inside `collection_jobs.checkpoint_data`).
- After each URL is processed, the checkpoint is updated atomically.
- If a collection job is interrupted (network drop, user stop, or process termination), calling `resume_job(job_id)` reloads `checkpoint_data`, skips already-verified URLs in that job, and completes remaining items.
- Incremental updates compare the newly computed `content_hash` (SHA-256 of normalized title + content) against `articles.content_hash` or `publications.content_hash`. Unchanged records only have `last_verified_at` updated; modified records increment `record_version` and append an audit entry to `change_log`.
