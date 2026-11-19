# Operator Manual — WikIran Archive
**Version 1.0 — Windows 11 Desktop Edition (Clerk & Administrator Guide)**

---

## 1. Overview
**WikIran Archive** is a local desktop research application designed for non-technical office clerks to search, browse, update, back up, and export publicly published articles and publication-catalogue metadata from `https://wikiran.org/`.

- **Offline Search**: Searching existing articles, organizations, categories, and publication catalogues works 100% offline using SQLite FTS5.
- **Strict Scope Protection**: Private correspondence (`/document/emails/*`), raw banking/contract files (`/document/files/*`), and personal identifiers are automatically excluded.

---

## 2. Launching the Application
1. Double-click the **WikIran Archive** shortcut on your Windows 11 Desktop.
2. Switch between **English (LTR)** and **Persian / فارسی (RTL)** at any time. Your language preference is saved automatically.

---

## 3. Clerk Quick Actions
From the **Dashboard**, click any of the clearly labelled primary actions:
1. **Search Archive**: Search across titles, editorial content, summaries, organizations, entities, categories, tags, and dates. Filter by date range, category, organization, source type, or verification status.
2. **Browse Articles**: Read full public investigative articles and inspect source URLs and retrieval timestamps.
3. **Browse Catalogue**: Inspect publication-level descriptions and safe aggregate file inventory metadata.
4. **Update Archive**: Connect politely to `wikiran.org` to check for new or updated public articles. If interrupted, click **Resume** in Collection History.
5. **Export to Excel**: Generate a multi-sheet `.xlsx` workbook (with separate sheets for Articles, Publications, Organizations, Categories, Sources, and Collection Statistics), or export to CSV and JSON.
6. **Create Backup**: Create an immediate verified SQLite backup. Automatic daily backups retain the most recent 14 copies.
7. **Help**: View built-in clerk instructions and troubleshooting tips.

---

## 4. Administrator Section
Switch to **Administrator Console** inside **Settings** to:
- Configure polite request rate limits, retry counts, and timeout intervals.
- Run **Database Integrity Checks** (`PRAGMA integrity_check` & `foreign_key_check`).
- Restore the archive from a verified backup (requires explicit confirmation).
- Inspect technical diagnostic logs and per-URL collection history.
