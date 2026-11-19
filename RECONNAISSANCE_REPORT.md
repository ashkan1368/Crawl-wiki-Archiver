# Technical Reconnaissance Report — WikIran.org Public Surface
**Project:** WikIran Archive (Version 1.0)
**Date:** 2026-11-18
**Phase:** PHASE 1 — Reconnaissance (Completed & Verified)

---

## 1. Executive Summary
A live technical reconnaissance was performed against `https://wikiran.org/` using polite, identified HTTP requests (`WikIranArchiveBot/1.0 (+https://wikiran.org; Public Research Archive)`). The objective was to inspect the public website architecture, verify permitted collection paths, document pagination mechanisms, test small samples of article and publication catalogue pages, and establish strict technical boundaries that prevent the ingestion of sensitive underlying leaked records.

---

## 2. Robots.txt & Content Signals Analysis
- **URL:** `https://wikiran.org/robots.txt`
- **HTTP Status:** `200 OK` (`text/plain; charset=utf-8`, 1,248 bytes)
- **Server:** Cloudflare + Next.js App Router (`X-Powered-By: Next.js`)
- **Findings:**
  - `robots.txt` defines European Union Directive 2019/790 Content Signals (`search`, `ai-input`, `ai-train`) and standard crawler rules.
  - Note: Requests with default generic Python `urllib` user-agents (`Python-urllib/3.11`) are blocked by Cloudflare WAF with `HTTP 403 Forbidden`. Properly identified research user-agents are served `HTTP 200 OK`.
  - `/sitemap.xml` returns `HTTP 404 Not Found`. Therefore, discovery must rely on public navigation links (`/`, `/leaks`, `/archives`, `/search?tabType=articles`).

---

## 3. Public Navigation & Permitted vs. Excluded Paths

### 3.1 Permitted Public Research Paths
1. **Home Page (`/`)**:
   - Lists featured investigative articles (`/document/articles/<uuid>`) and featured publication catalogues (`/leak/<slug>`).
2. **Articles Listing & Pagination (`/search?tabType=articles&page=<N>`)**:
   - Server-side rendered HTML listing of public editorial articles.
   - Pagination is controlled via the `page` query parameter (`page=1`, `page=2`, etc.) rendered inside `.uiPagination_paginationWrapper__*`.
   - Page 1 contains 18 article links; Page 2 contains additional article links.
3. **Individual Editorial Article Pages (`/document/articles/<uuid>`)**:
   - Contains editorial investigative analysis authored by WikIran researchers.
   - CSS Selectors verified on live HTML:
     - Headline: `.articleDetails_headline__*` (and `<title>`)
     - Publication Date: `.articleDetails_searchResultDate__*` (e.g., `Nov 2026`, `Aug 2026`)
     - Subheadline / Summary: `.articleDetails_subHeadline__*`
     - Editorial Content Body: `.uiMarkdown_uiMarkdownWrapper__*`
     - Public Illustrations: `/files/articles/<uuid>/*.png`
4. **Publication Catalogue Listing (`/leaks` and `/archives`)**:
   - Lists 28+ major publication catalogues (`/leak/rahbar`, `/leak/hms`, `/leak/irgc-oil`, `/leak/sahara-thunder`, `/leak/sej`, `/leak/asbgroup`, `/leak/front-companies`, `/leak/vessels`, etc.).
   - CSS Selectors verified on `/leaks`:
     - Card Container: `.feedLeakCard_feedLeakCardWrapper__*`
     - Title: `.feedLeakCard_title__*`
     - Subtitle (Persian/Native name): `.feedLeakCard_subTitle__*` (e.g., `سامانه يكپارچه مديريت ارز`)
     - Publication Date: `.feedLeakCard_leakDate__*`
     - Catalogue Description: `.feedLeakCard_content__*`
5. **Publication Catalogue Detail Header (`/leak/<slug>`)**:
   - The top section (`.leakDetails_leakDetailsWrapper__*`) provides safe publication-level metadata:
     - Headline: `.leakDetails_headline__*`
     - Subheadline: `.leakDetails_subHeadline__*`
     - Description: `.leakDetails_description__*`
     - Safe File Inventory Summary: `.leakDetails_dataTypeList__*` (e.g., `files`, `emails`) and aggregate result count `.leakDetails_resultsCount__*` (e.g., `10000+ results`).

### 3.2 Strictly Excluded Sensitive Paths (Guardrail Enforcement)
On `/leak/<slug>` pages, below the safe catalogue header, the page renders `.searchResultCard_searchResultWrapper__*` linking to:
- `/document/emails/<hash>` (exposed private correspondence)
- `/document/files/<hash>` (raw leaked banking records, contracts, identity papers, invoices)
- `/search?leaksSources[0]=...&dataTypes[0]=emails|files`

**Enforcement Rule:**
The collection engine (`wikiran_archive/collector/safety.py` and `discovery.py`) strictly blocks any URL matching `/document/emails/*`, `/document/files/*`, or raw attachment downloads, and strips all `.searchResultCard_*` elements when parsing `/leak/<slug>` catalogue pages. Only the high-level publication catalogue description and aggregate data-type inventory counts are recorded.

---

## 4. Live Sample Verification Summary
- **Sample Article Tested:** `/document/articles/418be098-dcb5-4bd0-ae4b-25bdfb17fe5a`
  - **Title:** *Serving Their Country: The Rahbar system and its Use by Iran’s security apparatus*
  - **Date:** `Nov 2026` (Normalized: `2026-11-01`)
  - **Author/Source:** `WikIran Exclusive`
  - **Entities Referenced:** `MODAFL`, `AFGS`, `IRGC`, `IRGC-QF`, `Sahara Thunder`
- **Sample Catalogue Tested:** `/leak/hms`
  - **Title:** *HMS Trading FZE & Petro Delta Energy Co. (PDECO)*
  - **Date:** `Aug 2026` (Normalized: `2026-08-01`)
  - **Safe Inventory Metadata:** Data types `files, emails`, Aggregate count `10000+ results`
  - **Excluded Items:** 10 sample `/document/emails/*` links detected on page and blocked by safety filter.
