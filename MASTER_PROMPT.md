# MASTER PROMPT — WIKIRAN ARCHIVE
## Version 1.0 | Windows Desktop Application

### 1. ROLE & OBJECTIVE
Design, implement, test, and package a professional Windows 11 desktop application named **WikIran Archive** intended for a non-technical office clerk, with a separate diagnostic and configuration view for administrators.

The application creates a local research archive for organizing publicly published editorial articles and publication-catalogue metadata from `https://wikiran.org/`.

### 2. SCOPE & ETHICAL / SAFETY RESTRICTIONS
- Discover permitted publicly accessible article (`/document/articles/<uuid>`) and publication-catalogue (`/leaks`, `/archives`, `/leak/<slug>`) pages.
- Collect article titles, publication dates, authors, descriptions, editorial content, categories, tags, public organizations/entities, and original source references.
- Catalogue publication-level descriptions and safe file inventory metadata (aggregate counts and data type labels only).
- **STRICT EXCLUSION**: Never bulk-download, mirror, index, or extract the contents of exposed private correspondence (`/document/emails/*`), banking records, identity documents, account information, confidential contracts (`/document/files/*`), or personal identifiers of private individuals.
- Respect `robots.txt`, conservative rate limits, exponential backoff, timeouts, and stop controls.

### 3. TARGET ENVIRONMENT & STACK
- **OS**: Windows 11 (single-computer deployment, offline local search, online incremental updates).
- **Languages**: Bilingual Persian (`fa` - RTL) and English (`en` - LTR) with persistent language preference.
- **Stack**: Python 3, PySide6 (Qt6 desktop GUI), SQLite + SQLite FTS5 (full-text search), HTTPX, BeautifulSoup4, Playwright (optional fallback), OpenPyXL, Pandas, PyInstaller, Inno Setup.

### 4. NAVIGATION & USER EXPERIENCE
1. Dashboard
2. Search Archive
3. Articles
4. Publication Catalogue
5. Organizations
6. Categories
7. Export Reports
8. Collection History
9. Settings (Clerk preferences + Administrator section)
10. Help

**Clerk Quick Actions**:
- Search Archive
- Browse Articles
- Browse Catalogue
- Update Archive
- Export to Excel
- Create Backup
- Help

### 5. NORMALIZED SQLITE DATABASE TABLES
1. `articles`
2. `publications`
3. `organizations`
4. `entities`
5. `categories`
6. `tags`
7. `article_entities`
8. `article_categories`
9. `publication_categories`
10. `sources`
11. `file_inventory`
12. `collection_jobs`
13. `collection_history`
14. `change_log`
15. `application_settings`
Plus `schema_migrations`, `article_tags`, and `fts_archive` (SQLite FTS5 virtual table).
