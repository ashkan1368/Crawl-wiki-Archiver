# Database Schema Specification — WikIran Archive
**Database Engine:** SQLite 3 with FTS5 (`ENABLE_FTS5`)
**Journal Mode:** `WAL` (Write-Ahead Logging)
**Foreign Keys:** `PRAGMA foreign_keys = ON;`

---

## 1. Audit & Provenance Columns
Every primary collected record (`articles`, `publications`, `organizations`, `entities`, `sources`, `file_inventory`) retains:
- `source_url` (`TEXT NOT NULL`) — Canonical original URL on `https://wikiran.org/`.
- `original_pub_id` (`TEXT`) — Upstream UUID or slug identifier.
- `retrieved_at` (`TEXT NOT NULL`) — ISO-8601 UTC timestamp of initial retrieval.
- `last_verified_at` (`TEXT NOT NULL`) — ISO-8601 UTC timestamp of latest verification.
- `extraction_status` (`TEXT NOT NULL`) — `VERIFIED`, `PARTIAL`, or `FAILED`.
- `content_hash` (`TEXT NOT NULL`) — SHA-256 hex digest of normalized content.
- `record_version` (`INTEGER NOT NULL DEFAULT 1`) — Incremented whenever upstream content changes.

---

## 2. Normalized Tables (15 Required Core Tables + FTS5)

### 2.1 `sources`
Stores upstream discovery endpoints and feed sources.
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `name` TEXT NOT NULL UNIQUE
- `source_type` TEXT NOT NULL (`ARTICLE_FEED`, `CATALOGUE_FEED`, `ARCHIVE_INDEX`)
- `base_url` TEXT NOT NULL
- `source_url` TEXT NOT NULL
- `original_pub_id` TEXT
- `robots_status` TEXT NOT NULL DEFAULT 'PERMITTED'
- `retrieved_at` TEXT NOT NULL
- `last_verified_at` TEXT NOT NULL
- `extraction_status` TEXT NOT NULL DEFAULT 'VERIFIED'
- `content_hash` TEXT NOT NULL
- `record_version` INTEGER NOT NULL DEFAULT 1

### 2.2 `articles`
Stores publicly published investigative and editorial articles.
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `original_pub_id` TEXT UNIQUE
- `title` TEXT NOT NULL
- `subtitle` TEXT
- `author` TEXT NOT NULL DEFAULT 'WikIran Editorial'
- `publication_date` TEXT NOT NULL (Normalized `YYYY-MM-DD`)
- `raw_date_text` TEXT
- `summary` TEXT NOT NULL
- `editorial_content` TEXT NOT NULL
- `source_id` INTEGER REFERENCES `sources(id)` ON DELETE SET NULL
- `source_url` TEXT NOT NULL UNIQUE
- `retrieved_at` TEXT NOT NULL
- `last_verified_at` TEXT NOT NULL
- `extraction_status` TEXT NOT NULL DEFAULT 'VERIFIED'
- `content_hash` TEXT NOT NULL
- `record_version` INTEGER NOT NULL DEFAULT 1

### 2.3 `publications`
Stores publication-level catalogue metadata (`/leak/<slug>`) without sensitive underlying leaked records.
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `original_pub_id` TEXT NOT NULL UNIQUE
- `title` TEXT NOT NULL
- `native_title` TEXT
- `publication_date` TEXT NOT NULL
- `raw_date_text` TEXT
- `description` TEXT NOT NULL
- `source_id` INTEGER REFERENCES `sources(id)` ON DELETE SET NULL
- `source_url` TEXT NOT NULL UNIQUE
- `retrieved_at` TEXT NOT NULL
- `last_verified_at` TEXT NOT NULL
- `extraction_status` TEXT NOT NULL DEFAULT 'VERIFIED'
- `content_hash` TEXT NOT NULL
- `record_version` INTEGER NOT NULL DEFAULT 1

### 2.4 `organizations`
Stores public institutional or corporate organizations referenced in articles and publication catalogues.
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `name` TEXT NOT NULL UNIQUE
- `native_name` TEXT
- `acronym` TEXT
- `org_type` TEXT NOT NULL (`STATE_INSTITUTION`, `BANKING_NETWORK`, `FRONT_COMPANY`, `COMMERCIAL_ENTITY`)
- `description` TEXT
- `source_url` TEXT NOT NULL
- `original_pub_id` TEXT
- `retrieved_at` TEXT NOT NULL
- `last_verified_at` TEXT NOT NULL
- `extraction_status` TEXT NOT NULL DEFAULT 'VERIFIED'
- `content_hash` TEXT NOT NULL
- `record_version` INTEGER NOT NULL DEFAULT 1

### 2.5 `entities`
Stores public non-private entities (e.g. vessels, industrial programs, sanction evasion systems, institutional bodies). Private personal identifiers are strictly prohibited.
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `name` TEXT NOT NULL UNIQUE
- `entity_type` TEXT NOT NULL (`ORGANIZATION`, `SYSTEM_NETWORK`, `VESSEL_ASSET`, `INSTITUTION`)
- `organization_id` INTEGER REFERENCES `organizations(id)` ON DELETE SET NULL
- `description` TEXT
- `source_url` TEXT NOT NULL
- `original_pub_id` TEXT
- `retrieved_at` TEXT NOT NULL
- `last_verified_at` TEXT NOT NULL
- `extraction_status` TEXT NOT NULL DEFAULT 'VERIFIED'
- `content_hash` TEXT NOT NULL
- `record_version` INTEGER NOT NULL DEFAULT 1

### 2.6 `categories`
Stores normalized thematic research categories.
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `slug` TEXT NOT NULL UNIQUE
- `name_en` TEXT NOT NULL
- `name_fa` TEXT NOT NULL
- `description` TEXT
- `source_url` TEXT NOT NULL DEFAULT 'https://wikiran.org/'
- `retrieved_at` TEXT NOT NULL
- `last_verified_at` TEXT NOT NULL
- `extraction_status` TEXT NOT NULL DEFAULT 'VERIFIED'
- `content_hash` TEXT NOT NULL
- `record_version` INTEGER NOT NULL DEFAULT 1

### 2.7 `tags`
Stores normalized keyword tags.
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `name` TEXT NOT NULL UNIQUE
- `retrieved_at` TEXT NOT NULL

### 2.8 `article_entities`
Many-to-many join between `articles` and `entities` / `organizations`.
- `article_id` INTEGER NOT NULL REFERENCES `articles(id)` ON DELETE CASCADE
- `entity_id` INTEGER NOT NULL REFERENCES `entities(id)` ON DELETE CASCADE
- `organization_id` INTEGER REFERENCES `organizations(id)` ON DELETE SET NULL
- `relevance_note` TEXT
- PRIMARY KEY (`article_id`, `entity_id`)

### 2.9 `article_categories`
Many-to-many join between `articles` and `categories`.
- `article_id` INTEGER NOT NULL REFERENCES `articles(id)` ON DELETE CASCADE
- `category_id` INTEGER NOT NULL REFERENCES `categories(id)` ON DELETE CASCADE
- PRIMARY KEY (`article_id`, `category_id`)

### 2.10 `publication_categories`
Many-to-many join between `publications` and `categories`.
- `publication_id` INTEGER NOT NULL REFERENCES `publications(id)` ON DELETE CASCADE
- `category_id` INTEGER NOT NULL REFERENCES `categories(id)` ON DELETE CASCADE
- PRIMARY KEY (`publication_id`, `category_id`)

### 2.11 `file_inventory`
Stores safe, high-level aggregate inventory metadata for a publication catalogue (never individual private files or contents).
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `publication_id` INTEGER NOT NULL REFERENCES `publications(id)` ON DELETE CASCADE
- `data_type` TEXT NOT NULL (`emails_aggregate`, `files_aggregate`, `structured_catalogue`)
- `reported_count_label` TEXT NOT NULL (e.g., `10000+ results`, `Catalogue Summary Only`)
- `safety_policy_applied` TEXT NOT NULL DEFAULT 'METADATA_ONLY_SENSITIVE_EXCLUDED'
- `source_url` TEXT NOT NULL
- `original_pub_id` TEXT
- `retrieved_at` TEXT NOT NULL
- `last_verified_at` TEXT NOT NULL
- `extraction_status` TEXT NOT NULL DEFAULT 'VERIFIED'
- `content_hash` TEXT NOT NULL
- `record_version` INTEGER NOT NULL DEFAULT 1

### 2.12 `collection_jobs`
Tracks active, interrupted, and completed collection jobs with checkpoint recovery data.
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `job_uuid` TEXT NOT NULL UNIQUE
- `job_type` TEXT NOT NULL (`FULL_DISCOVERY`, `INCREMENTAL_UPDATE`, `RESUME_RECOVERY`)
- `status` TEXT NOT NULL (`RUNNING`, `INTERRUPTED`, `COMPLETED`, `FAILED`, `SUSPENDED`)
- `started_at` TEXT NOT NULL
- `finished_at` TEXT
- `total_discovered` INTEGER NOT NULL DEFAULT 0
- `processed_count` INTEGER NOT NULL DEFAULT 0
- `new_records_count` INTEGER NOT NULL DEFAULT 0
- `updated_records_count` INTEGER NOT NULL DEFAULT 0
- `skipped_unchanged_count` INTEGER NOT NULL DEFAULT 0
- `blocked_sensitive_count` INTEGER NOT NULL DEFAULT 0
- `failed_count` INTEGER NOT NULL DEFAULT 0
- `checkpoint_data` TEXT NOT NULL DEFAULT '{}'
- `error_summary` TEXT

### 2.13 `collection_history`
Granular per-URL audit log for every collection run.
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `job_id` INTEGER NOT NULL REFERENCES `collection_jobs(id)` ON DELETE CASCADE
- `target_url` TEXT NOT NULL
- `record_type` TEXT NOT NULL (`ARTICLE`, `PUBLICATION`, `DISCOVERY_PAGE`, `BLOCKED_SENSITIVE`)
- `http_status` INTEGER
- `action_taken` TEXT NOT NULL (`INSERTED`, `UPDATED`, `UNCHANGED`, `EXCLUDED_POLICY`, `FAILED`)
- `timestamp` TEXT NOT NULL
- `message` TEXT

### 2.14 `change_log`
Tracks version history and content diffs when an existing record changes upstream.
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `table_name` TEXT NOT NULL
- `record_id` INTEGER NOT NULL
- `source_url` TEXT NOT NULL
- `previous_version` INTEGER NOT NULL
- `new_version` INTEGER NOT NULL
- `previous_hash` TEXT NOT NULL
- `new_hash` TEXT NOT NULL
- `changed_at` TEXT NOT NULL
- `change_summary` TEXT NOT NULL

### 2.15 `application_settings`
Key-value store for persistent user and administrator configuration.
- `key` TEXT PRIMARY KEY
- `value` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

---

## 3. Full-Text Search Virtual Table (`fts_archive`)
Implemented via SQLite FTS5 (`USING fts5`) indexing across:
- `record_type` (`ARTICLE` or `PUBLICATION`)
- `record_id` (UNINDEXED)
- `title`
- `editorial_content`
- `summary`
- `organization_names`
- `entity_names`
- `category_names`
- `tag_names`
- `publication_date`
- `source_url` (UNINDEXED)
