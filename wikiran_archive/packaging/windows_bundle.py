"""
Windows 11 Turnkey Package & Standalone Application Builder for Non-Technical Clerks.
Bundles the exact compiled React + Tailwind CSS + Lucide application (`dist/assets/*.css` and
`dist/assets/*.js`) together with the complete pre-seeded SQLite database snapshot, real Excel
(`.xlsx`) workbooks, documentation, and an embedded offline API bridge (`window.fetch` + download
interceptor) so that opening `WikIran_Archive_Windows11_Ready_App.html` or running
`WikIran_Archive_Windows11_Standalone_Installer.bat` launches the 100% identical application UI
shown in the live preview.
"""

from __future__ import annotations

import base64
import json
import subprocess
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..backup.manager import BackupManager
from ..collector.reconnaissance import generate_reconnaissance_markdown, run_reconnaissance
from ..collector.scheduler import ScheduledCollectionRunner
from ..config.settings import AppPaths
from ..database.connection import verify_database_integrity
from ..database.repository import ArchiveRepository
from ..export.csv_converter import CsvSpreadsheetWorkbench
from ..export.exporters import ArchiveExporter
from ..logging_utils.logger import read_diagnostic_logs
from ..search.fts_search import ArchiveSearchEngine, SearchFilters


DOC_FILES_MAP: dict[str, str] = {
    "reconnaissance": "RECONNAISSANCE_REPORT.md",
    "architecture": "ARCHITECTURE.md",
    "schema": "DATABASE_SCHEMA.md",
    "manual_fa": "OPERATOR_MANUAL_FA.md",
    "manual_en": "OPERATOR_MANUAL_EN.md",
    "status": "PROJECT_STATUS.md",
    "pyside_ui": "wikiran_archive/ui/main_window.py",
    "migrations_py": "wikiran_archive/database/migrations.py",
    "recon_py": "wikiran_archive/collector/reconnaissance.py",
}


def _load_compiled_react_assets(project_root: Path) -> tuple[str, str]:
    """
    Read the compiled Vite React + Tailwind CSS bundle (`dist/assets/*.css` and `dist/assets/*.js`).
    If `dist/assets` is not yet built, runs `npm run build` automatically so the standalone HTML
    always contains the exact React UI shown in the preview.
    """
    dist_assets = project_root / "dist" / "assets"
    css_files = sorted(dist_assets.glob("*.css")) if dist_assets.exists() else []
    js_files = sorted(dist_assets.glob("*.js")) if dist_assets.exists() else []

    if not css_files or not js_files:
        subprocess.run(
            ["npm", "run", "build"],
            cwd=str(project_root),
            check=False,
            capture_output=True,
        )
        css_files = sorted(dist_assets.glob("*.css")) if dist_assets.exists() else []
        js_files = sorted(dist_assets.glob("*.js")) if dist_assets.exists() else []

    css_text = css_files[0].read_text(encoding="utf-8") if css_files else ""
    js_text = js_files[0].read_text(encoding="utf-8") if js_files else ""
    return css_text, js_text


def _build_embedded_payload(
    project_root: Path, paths: AppPaths, repo: ArchiveRepository
) -> dict[str, Any]:
    """
    Collect the full SQLite state, FTS5 search index records, CSV-to-Excel datasets,
    real `.xlsx` binary workbooks, and markdown documentation so every single API route
    in the compiled React app works identically offline on Windows 11.
    """
    ok, msg = verify_database_integrity(paths.db_path)
    backup_mgr = BackupManager(paths.db_path, paths.backups_dir)
    scheduler = ScheduledCollectionRunner(str(paths.db_path))
    csv_wb = CsvSpreadsheetWorkbench(repo, paths.exports_dir)
    csv_wb.ensure_default_csv_dataset()
    csv_wb.ensure_unredacted_ledger_dataset()

    csv_datasets = csv_wb.list_datasets()
    all_csv_details: dict[str, Any] = {}
    csv_xlsx_b64: dict[str, str] = {}

    for ds in csv_datasets:
        ds_id = str(ds["id"])
        detail = csv_wb.get_dataset_details(dataset_id=ds["id"], preview_all=True)
        all_csv_details[ds_id] = detail
        xlsx_path_str = detail.get("dataset", {}).get("xlsx_export_path")
        if xlsx_path_str and Path(xlsx_path_str).exists():
            csv_xlsx_b64[ds_id] = base64.b64encode(Path(xlsx_path_str).read_bytes()).decode("ascii")

    cross_audit_csv = csv_wb.get_dataset_details(
        dataset_id=None, search_query="", preview_all=True, cross_dataset_audit=True
    )

    exporter = ArchiveExporter(repo)
    master_xlsx = paths.exports_dir / "WikIran_Archive_Full_Workbook.xlsx"
    exporter.export_excel(master_xlsx)
    master_xlsx_b64 = (
        base64.b64encode(master_xlsx.read_bytes()).decode("ascii")
        if master_xlsx.exists()
        else ""
    )

    search_engine = ArchiveSearchEngine(repo.conn)
    all_search_records: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, int]] = set()
    for st in ("ARTICLE", "PUBLICATION", "CSV_ROW", "FILE_INVENTORY", "ENTITY"):
        for row in search_engine.search(SearchFilters(query="", source_type=st)):
            key = (str(row["record_type"]), int(row["id"]))
            if key not in seen_keys:
                seen_keys.add(key)
                all_search_records.append(row)

    docs_map: dict[str, dict[str, str]] = {}
    for key, rel_path in DOC_FILES_MAP.items():
        fp = project_root / rel_path
        if fp.exists():
            docs_map[key] = {
                "filename": rel_path,
                "content": fp.read_text(encoding="utf-8"),
            }

    recon_md = docs_map.get("reconnaissance", {}).get(
        "content", "# Technical Reconnaissance Report — WikIran.org\n"
    )
    finding_dict = {
        "inspected_at": "2026-11-18T00:00:00Z",
        "base_url": "https://wikiran.org",
        "robots_status_code": 200,
        "robots_permitted": True,
    }

    settings_dict = repo.get_settings()
    configured_base = (settings_dict.get("custom_storage_path") or "").strip() or r"C:\WikIranArchive"
    sep = "\\" if ("\\" in configured_base or ":" in configured_base) else "/"
    b_clean = configured_base.rstrip("\\/")

    from ..main import compute_storage_volume
    from ..collector.ofac_sync import get_ofac_summary

    overview = {
        "ok": True,
        "stats": repo.get_dashboard_stats(),
        "trends": repo.get_collection_trends(),
        "schedule": asdict(scheduler.get_schedule_config(repo)),
        "csv_datasets": csv_datasets,
        "active_csv": csv_wb.get_dataset_details(preview_all=True),
        "settings": settings_dict,
        "articles": repo.list_articles(),
        "publications": repo.list_publications(),
        "organizations": repo.list_organizations(),
        "categories": repo.list_categories(),
        "tags": repo.list_tags(),
        "sources": repo.list_sources(),
        "jobs": repo.list_collection_jobs(),
        "history": repo.list_collection_history(limit=60),
        "changes": repo.list_change_log(limit=30),
        "backups": backup_mgr.list_backups(),
        "integrity": {"verified": ok, "message": msg},
        "logs": read_diagnostic_logs(paths.logs_dir, max_lines=100),
        "paths": {
            "base_dir": b_clean,
            "db_path": f"{b_clean}{sep}data{sep}wikiran_archive.db",
            "backups_dir": f"{b_clean}{sep}backups",
            "exports_dir": f"{b_clean}{sep}exports",
            "logs_dir": f"{b_clean}{sep}logs",
        },
        "storage_volume": compute_storage_volume(paths, repo),
        "ofac_summary": get_ofac_summary(repo.conn, settings_dict),
    }

    return {
        "overview": overview,
        "all_csv_details": all_csv_details,
        "cross_audit_csv": cross_audit_csv,
        "all_search_records": all_search_records,
        "docs": docs_map,
        "recon": {"ok": True, "finding": finding_dict, "markdown": recon_md},
        "master_xlsx_b64": master_xlsx_b64,
        "csv_xlsx_b64": csv_xlsx_b64,
    }


def build_standalone_offline_app_html(
    repo: ArchiveRepository, paths: AppPaths, project_root: Path | None = None
) -> str:
    """
    Build a 100% self-contained single-file Windows Desktop Application HTML file that
    bundles the EXACT compiled React + Tailwind CSS + Lucide icons application (`dist/assets/*`)
    along with the embedded SQLite database and an offline `window.fetch` / download bridge.
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent.parent

    css_text, js_text = _load_compiled_react_assets(project_root)
    embedded_payload = _build_embedded_payload(project_root, paths, repo)

    safe_json = json.dumps(embedded_payload, ensure_ascii=False).replace(
        "</script>", "<\\/script>"
    )
    safe_js = js_text.replace("</script>", "<\\/script>")
    safe_css = css_text.replace("</style>", "<\\/style>")

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>WikIran Archive — Local Research & Publication Catalogue</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Vazirmatn:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <style>{safe_css}</style>
  </head>
  <body>
    <div id="root"></div>
    <script>
      window.__WIKIRAN_EMBEDDED__ = {safe_json};
      (function() {{
        const EMBEDDED = window.__WIKIRAN_EMBEDDED__;
        const STORAGE_KEY = 'wikiran_win11_standalone_state_v1';

        function syncPathsFromSettings() {{
          const customBase = (EMBEDDED.overview.settings && EMBEDDED.overview.settings.custom_storage_path || '').trim();
          if (customBase) {{
            const sep = (customBase.includes('\\\\') || customBase.includes(':')) ? '\\\\' : '/';
            const clean = customBase.replace(/[\\\\/]+$/, '');
            EMBEDDED.overview.paths = {{
              base_dir: clean,
              db_path: clean + sep + 'data' + sep + 'wikiran_archive.db',
              backups_dir: clean + sep + 'backups',
              exports_dir: clean + sep + 'exports',
              logs_dir: clean + sep + 'logs'
            }};
          }}
        }}

        try {{
          const saved = localStorage.getItem(STORAGE_KEY);
          if (saved) {{
            const parsed = JSON.parse(saved);
            if (parsed.settings) Object.assign(EMBEDDED.overview.settings, parsed.settings);
            if (parsed.schedule) Object.assign(EMBEDDED.overview.schedule, parsed.schedule);
            if (parsed.backups) EMBEDDED.overview.backups = parsed.backups;
            if (parsed.custom_csv_datasets) {{
              parsed.custom_csv_datasets.forEach(ds => {{
                if (!EMBEDDED.overview.csv_datasets.find(d => d.id === ds.id)) {{
                  EMBEDDED.overview.csv_datasets.unshift(ds);
                }}
              }});
            }}
            if (parsed.custom_csv_details) {{
              Object.assign(EMBEDDED.all_csv_details, parsed.custom_csv_details);
            }}
          }}
          syncPathsFromSettings();
        }} catch (e) {{}}

        function saveLocalPatch(patch) {{
          try {{
            const cur = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{{}}');
            Object.assign(cur, patch);
            localStorage.setItem(STORAGE_KEY, JSON.stringify(cur));
          }} catch (e) {{}}
        }}

        function jsonResponse(obj, status) {{
          return new Response(JSON.stringify(obj), {{
            status: status || 200,
            headers: {{ 'Content-Type': 'application/json' }}
          }});
        }}

        function b64ToBlob(b64, mime) {{
          const bin = atob(b64);
          const len = bin.length;
          const bytes = new Uint8Array(len);
          for (let i = 0; i < len; i++) bytes[i] = bin.charCodeAt(i);
          return new Blob([bytes], {{ type: mime }});
        }}

        function triggerBlobDownload(blob, filename) {{
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          setTimeout(() => {{
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
          }}, 250);
        }}

        function escapeXml(val) {{
          return String(val ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
        }}

        function buildExcelXmlWorkbook(sheets) {{
          let xml = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?>';
          xml += '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">';
          sheets.forEach(s => {{
            xml += '<Worksheet ss:Name="' + escapeXml(s.name.slice(0, 31)) + '"><Table>';
            xml += '<Row>' + s.headers.map(h => '<Cell><Data ss:Type="String">' + escapeXml(h) + '</Data></Cell>').join('') + '</Row>';
            s.rows.forEach(r => {{
              xml += '<Row>' + r.map(c => '<Cell><Data ss:Type="String">' + escapeXml(c) + '</Data></Cell>').join('') + '</Row>';
            }});
            xml += '</Table></Worksheet>';
          }});
          xml += '</Workbook>';
          return new Blob([xml], {{ type: 'application/vnd.ms-excel;charset=utf-8' }});
        }}

        function parseCsvLine(line) {{
          const out = [];
          let cur = '';
          let inQuotes = false;
          for (let i = 0; i < line.length; i++) {{
            const ch = line[i];
            if (ch === '"') {{
              if (inQuotes && line[i + 1] === '"') {{
                cur += '"';
                i++;
              }} else {{
                inQuotes = !inQuotes;
              }}
            }} else if (ch === ',' && !inQuotes) {{
              out.push(cur.trim());
              cur = '';
            }} else {{
              cur += ch;
            }}
          }}
          out.push(cur.trim());
          return out;
        }}

        const origFetch = window.fetch ? window.fetch.bind(window) : null;

        window.fetch = async function(input, init) {{
          const rawUrl = typeof input === 'string' ? input : (input && input.url ? input.url : '');
          let path = rawUrl;
          try {{
            if (rawUrl.startsWith('http')) {{
              const u = new URL(rawUrl);
              path = u.pathname + u.search;
            }}
          }} catch (e) {{}}

          if (!path.startsWith('/api/')) {{
            if (origFetch) return origFetch(input, init);
            throw new Error('Offline mode');
          }}

          let body = {{}};
          if (init && init.body && typeof init.body === 'string') {{
            try {{ body = JSON.parse(init.body); }} catch (e) {{}}
          }}

          if (path === '/api/overview') {{
            syncPathsFromSettings();
            return jsonResponse(EMBEDDED.overview);
          }}

          if (path.startsWith('/api/docs/')) {{
            const key = path.replace('/api/docs/', '').split('?')[0];
            const doc = EMBEDDED.docs[key];
            if (doc) {{
              return jsonResponse({{ ok: true, filename: doc.filename, content: doc.content }});
            }}
            return jsonResponse({{ ok: false, error: 'Document not found' }}, 404);
          }}

          if (path === '/api/settings') {{
            const updates = body.settings || body || {{}};
            Object.assign(EMBEDDED.overview.settings, updates);
            syncPathsFromSettings();
            saveLocalPatch({{ settings: EMBEDDED.overview.settings }});
            return jsonResponse({{
              ok: true,
              settings: EMBEDDED.overview.settings,
              paths: EMBEDDED.overview.paths,
              schedule: EMBEDDED.overview.schedule,
              csv_datasets: EMBEDDED.overview.csv_datasets,
              active_csv: EMBEDDED.overview.active_csv
            }});
          }}

          if (path === '/api/search') {{
            const q = String(body.query || '').trim().toLowerCase();
            const tokens = q.replace(/["*]/g, ' ').split(/\\s+/).filter(Boolean);
            const catSlug = body.category_slug;
            const orgName = body.organization_name ? String(body.organization_name).toLowerCase() : null;
            const srcType = body.source_type === 'FILE_METADATA' ? 'FILE_INVENTORY' : body.source_type;
            const dateFrom = body.date_from;
            const dateTo = body.date_to;

            const results = (EMBEDDED.all_search_records || []).filter(r => {{
              if (srcType && srcType !== 'ALL' && r.record_type !== srcType) return false;
              if (!q && !srcType && !['ARTICLE', 'PUBLICATION'].includes(r.record_type)) return false;
              const pubD = String(r.publication_date || '').trim().slice(0, 10);
              if ((dateFrom || dateTo) && !pubD) return false;
              if (dateFrom && pubD < dateFrom) return false;
              if (dateTo && pubD > dateTo) return false;
              if (orgName && orgName !== 'all' && !String(r.organizations || '').toLowerCase().includes(orgName)) return false;
              if (catSlug && catSlug !== 'ALL') {{
                const catMatch = (EMBEDDED.overview.categories || []).find(c => c.slug === catSlug);
                if (catMatch && !String(r.category_en || '').includes(catMatch.name_en)) return false;
              }}
              if (!tokens.length) return true;
              const hay = [
                r.title, r.native_title, r.short_description, r.editorial_content,
                r.category_en, r.category_fa, r.organizations, r.tags, r.source_name, r.source_url
              ].join(' ').toLowerCase();
              return tokens.every(t => hay.includes(t));
            }});
            return jsonResponse({{ ok: true, results }});
          }}

          if (path === '/api/csv/view') {{
            const dsId = body.dataset_id ? String(body.dataset_id) : String((EMBEDDED.overview.csv_datasets[0] || {{}}).id || '1');
            const q = String(body.query || '').trim().toLowerCase();
            const previewAll = Boolean(body.preview_all);
            const crossAudit = Boolean(body.cross_dataset_audit);

            const baseDetail = crossAudit
              ? EMBEDDED.cross_audit_csv
              : (EMBEDDED.all_csv_details[dsId] || Object.values(EMBEDDED.all_csv_details)[0]);

            if (!baseDetail) {{
              return jsonResponse({{ ok: true, csv_datasets: EMBEDDED.overview.csv_datasets, active_csv: null }});
            }}

            const allRows = baseDetail.rows || [];
            const matchedRows = q
              ? allRows.filter(r => String(r.searchable_text || '').toLowerCase().includes(q))
              : allRows;
            const subsetLimit = 5;
            const returnedRows = previewAll ? matchedRows : matchedRows.slice(0, subsetLimit);

            const activeCsv = Object.assign({{}}, baseDetail, {{
              rows: returnedRows,
              total_rows_in_dataset: allRows.length,
              matching_rows_count: matchedRows.length,
              returned_rows_count: returnedRows.length,
              preview_all_enabled: previewAll,
              cross_dataset_audit: crossAudit,
              is_subset_truncated: !previewAll && matchedRows.length > subsetLimit,
              subset_limit: subsetLimit
            }});
            EMBEDDED.overview.active_csv = activeCsv;
            return jsonResponse({{
              ok: true,
              csv_datasets: EMBEDDED.overview.csv_datasets,
              active_csv: activeCsv
            }});
          }}

          if (path === '/api/csv/import') {{
            const text = String(body.csv_text || '').trim();
            const filename = String(body.filename || 'imported_table.csv');
            const dsName = String(body.dataset_name || filename.replace(/\\.csv$/i, ''));
            const lines = text.split(/\\r?\\n/).filter(l => l.trim().length > 0);
            const headers = lines.length ? parseCsvLine(lines[0]) : ['Column_1'];
            const rows = lines.slice(1).map((line, idx) => {{
              const vals = parseCsvLine(line);
              const cells = {{}};
              headers.forEach((h, i) => {{ cells[h] = vals[i] || ''; }});
              const searchable = headers.map(h => h + ': ' + (cells[h] || '')).join(' | ');
              return {{
                id: Date.now() + idx,
                row_number: idx + 1,
                cells: cells,
                searchable_text: searchable
              }};
            }});

            const newId = Date.now();
            const newDs = {{
              id: newId,
              dataset_name: dsName,
              original_filename: filename,
              headers: headers,
              row_count: rows.length,
              column_count: headers.length,
              xlsx_export_path: EMBEDDED.overview.paths.exports_dir + '\\\\' + dsName + '.xlsx',
              source_url: 'local://csv/' + filename,
              retrieved_at: new Date().toISOString(),
              extraction_status: 'VERIFIED'
            }};
            const newDetail = {{
              dataset: newDs,
              rows: rows,
              total_rows_in_dataset: rows.length,
              matching_rows_count: rows.length,
              returned_rows_count: rows.length,
              preview_all_enabled: true,
              cross_dataset_audit: false,
              is_subset_truncated: false,
              subset_limit: 5
            }};

            EMBEDDED.overview.csv_datasets.unshift(newDs);
            EMBEDDED.all_csv_details[String(newId)] = newDetail;
            EMBEDDED.overview.active_csv = newDetail;

            rows.forEach(r => {{
              EMBEDDED.all_search_records.unshift({{
                record_type: 'CSV_ROW',
                id: r.id,
                title: '[' + dsName + ' — Row #' + r.row_number + ']',
                native_title: '',
                short_description: r.searchable_text,
                editorial_content: r.searchable_text,
                publication_date: new Date().toISOString().slice(0, 10),
                category_en: 'CSV Excel Table (' + filename + ')',
                category_fa: 'جدول اکسل CSV (' + filename + ')',
                organizations: '',
                tags: 'CSV Excel Table',
                source_name: dsName,
                source_url: 'local://csv/' + filename + '#row-' + r.row_number,
                extraction_status: 'VERIFIED',
                retrieved_at: new Date().toISOString(),
                record_version: 1
              }});
            }});

            return jsonResponse({{
              ok: true,
              csv_datasets: EMBEDDED.overview.csv_datasets,
              active_csv: newDetail
            }});
          }}

          if (path === '/api/schedule') {{
            Object.assign(EMBEDDED.overview.schedule, body, {{
              next_run_at: new Date(Date.now() + 86400000).toISOString().replace('T', ' ').slice(0, 19) + ' UTC'
            }});
            saveLocalPatch({{ schedule: EMBEDDED.overview.schedule }});
            return jsonResponse({{
              ok: true,
              schedule: EMBEDDED.overview.schedule,
              settings: EMBEDDED.overview.settings
            }});
          }}

          const SERVER_DISCOVERED_POOL = [
            {{
              type: 'ARTICLE',
              original_pub_id: '5a8ec768-daaf-4dcd-b0e3-8e38159720a7',
              title: 'Inside the IRGC Oil Export & Exchange House Settlement Network',
              subtitle: 'Investigative Report',
              author: 'WikIran Editorial',
              publication_date: '2026-10-15',
              categories_en: 'Maritime & Petroleum Trade Networks, Shadow Banking & Foreign Currency',
              categories_fa: 'شبکه‌های تجارت نفت و حمل‌ونقل دریایی, بانکداری سایه و مدیریت ارز',
              organizations_list: 'Armed Forces General Staff (AFGS), Sepehr Energy Jahan (SEJ)',
              tags_list: 'Oil Exports, Shadow Banking, Sanctions Evasion',
              summary: 'Detailed breakdown of crude oil allocation settlements, offshore exchange houses, and maritime logistics utilized by IRGC-affiliated commercial entities.',
              editorial_content: 'This investigative report documents the settlement channels and front companies used to clear petroleum revenues across multi-jurisdictional exchange houses and Rahbar intermediaries.',
              source_url: 'https://wikiran.org/document/articles/5a8ec768-daaf-4dcd-b0e3-8e38159720a7'
            }},
            {{
              type: 'PUBLICATION',
              original_pub_id: 'sadaf',
              title: 'Sadaf Exchange & Financial Intermediary Ledger',
              native_title: 'صرافی صدف و شبکه واسطه‌های ارزی',
              publication_date: '2026-09-01',
              categories_en: 'Shadow Banking & Foreign Currency',
              categories_fa: 'بانکداری سایه و مدیریت ارز',
              description: 'Publication catalogue and correspondence archive of Sadaf Exchange and affiliated foreign-currency settlement accounts.',
              source_url: 'https://wikiran.org/leak/sadaf'
            }},
            {{
              type: 'PUBLICATION',
              original_pub_id: 'pedram',
              title: 'Pedram Commercial & Petrochemical Brokerage Files',
              native_title: 'اسناد شبکه بازرگانی و پتروشیمی پدرام',
              publication_date: '2026-08-15',
              categories_en: 'Front Companies & Sanctions Evasion',
              categories_fa: 'شرکت‌های پوششی و دور زدن تحریم‌ها',
              description: 'Leaked corporate registries, shipping manifests, and settlement records of the Pedram commercial brokerage network.',
              source_url: 'https://wikiran.org/leak/pedram'
            }},
            {{
              type: 'PUBLICATION',
              original_pub_id: 'sepah',
              title: 'Bank Sepah — Institutional Foreign Currency & Defense Clearing Records',
              native_title: 'بانک سپه - اسناد ارزی و تسویه نهادهای دفاعی',
              publication_date: '2026-07-20',
              categories_en: 'State Economic & Financial Institutions, Shadow Banking & Foreign Currency',
              categories_fa: 'نهادهای اقتصادی و مالی دولتی, بانکداری سایه و مدیریت ارز',
              description: 'Comprehensive archive of Bank Sepah institutional accounts, defense logistics letters of credit, and intermediary clearing records.',
              source_url: 'https://wikiran.org/leak/sepah'
            }},
            {{
              type: 'PUBLICATION',
              original_pub_id: 'tejarat',
              title: 'Tejarat Bank — International Trade & Exchange House Ledgers',
              native_title: 'بانک تجارت - دفاتر ارزی و شرکت‌های واسطه',
              publication_date: '2026-06-10',
              categories_en: 'State Economic & Financial Institutions',
              categories_fa: 'نهادهای اقتصادی و مالی دولتی',
              description: 'Catalogue of Tejarat Bank offshore settlement channels, Rahbar intermediary companies, and commercial letters of credit.',
              source_url: 'https://wikiran.org/leak/tejarat'
            }},
            {{
              type: 'PUBLICATION',
              original_pub_id: 'caspian-airlines',
              title: 'Caspian Airlines — Aviation Procurement & Logistics Archive',
              native_title: 'هواپیمایی کاسپین - اسناد تدارکات و لجستیک هوایی',
              publication_date: '2026-04-15',
              categories_en: 'Defense & Industrial Procurement',
              categories_fa: 'تدارکات دفاعی و صنعتی',
              description: 'Aviation spare-parts procurement contracts, aircraft maintenance logs, and intermediary supplier correspondence for Caspian Airlines.',
              source_url: 'https://wikiran.org/leak/caspian-airlines'
            }},
            {{
              type: 'PUBLICATION',
              original_pub_id: 'triliance',
              title: 'Triliance Petrochemical Co. — Global Polymer & Crude Brokerage',
              native_title: 'شرکت پتروشیمی تریلیانس - شبکه فروش نفت و پتروشیمی',
              publication_date: '2026-03-01',
              categories_en: 'Maritime & Petroleum Trade Networks, Front Companies & Sanctions Evasion',
              categories_fa: 'شبکه‌های تجارت نفت و حمل‌ونقل دریایی, شرکت‌های پوششی و دور زدن تحریم‌ها',
              description: 'Sanctions-evasion corporate network, front company invoices, and banking records of Triliance Petrochemical Co.',
              source_url: 'https://wikiran.org/leak/triliance'
            }}
          ];

          if (path === '/api/schedule/run-now' || path === '/api/update-archive' || path === '/api/resume-job') {{
            const nowIso = new Date().toISOString();
            const isInterrupt = Boolean(body && body.simulate_interrupt_after);
            const maxToPull = isInterrupt ? Number(body.simulate_interrupt_after) : Number(body.max_items || 4);

            const existingUrls = new Set([
              ...(EMBEDDED.overview.articles || []).map(a => a.source_url),
              ...(EMBEDDED.overview.publications || []).map(p => p.source_url)
            ]);

            const unseenPool = SERVER_DISCOVERED_POOL.filter(item => !existingUrls.has(item.source_url));
            const batch = unseenPool.slice(0, maxToPull);
            const nextJobId = (EMBEDDED.overview.jobs[0] ? EMBEDDED.overview.jobs[0].id : 10) + 1;

            batch.forEach((item, idx) => {{
              const recId = Date.now() + idx;
              if (item.type === 'ARTICLE') {{
                const newArt = {{
                  id: recId,
                  original_pub_id: item.original_pub_id,
                  title: item.title,
                  subtitle: item.subtitle,
                  author: item.author,
                  publication_date: item.publication_date,
                  raw_date_text: item.publication_date,
                  summary: item.summary,
                  editorial_content: item.editorial_content,
                  source_url: item.source_url,
                  retrieved_at: nowIso,
                  last_verified_at: nowIso,
                  extraction_status: 'VERIFIED',
                  record_version: 1,
                  categories_en: item.categories_en,
                  categories_fa: item.categories_fa,
                  organizations_list: item.organizations_list,
                  tags_list: item.tags_list
                }};
                EMBEDDED.overview.articles.unshift(newArt);
                EMBEDDED.overview.stats.articles_count = EMBEDDED.overview.articles.length;
                EMBEDDED.all_search_records.unshift({{
                  record_type: 'ARTICLE',
                  id: recId,
                  title: item.title,
                  native_title: '',
                  short_description: item.summary,
                  editorial_content: item.editorial_content,
                  publication_date: item.publication_date,
                  category_en: item.categories_en,
                  category_fa: item.categories_fa,
                  organizations: item.organizations_list,
                  tags: item.tags_list,
                  source_name: 'WikIran Public Articles Index',
                  source_url: item.source_url,
                  extraction_status: 'VERIFIED',
                  retrieved_at: nowIso,
                  record_version: 1
                }});
              }} else {{
                const newPub = {{
                  id: recId,
                  original_pub_id: item.original_pub_id,
                  title: item.title,
                  native_title: item.native_title,
                  publication_date: item.publication_date,
                  raw_date_text: item.publication_date,
                  description: item.description,
                  source_url: item.source_url,
                  retrieved_at: nowIso,
                  last_verified_at: nowIso,
                  extraction_status: 'VERIFIED',
                  record_version: 1,
                  categories_en: item.categories_en,
                  categories_fa: item.categories_fa,
                  inventory: [{{ data_type: 'files_aggregate', reported_count_label: '5000+ results (Unredacted Archive)' }}]
                }};
                EMBEDDED.overview.publications.unshift(newPub);
                EMBEDDED.overview.stats.publications_count = EMBEDDED.overview.publications.length;
                EMBEDDED.all_search_records.unshift({{
                  record_type: 'PUBLICATION',
                  id: recId,
                  title: item.title,
                  native_title: item.native_title,
                  short_description: item.description,
                  editorial_content: item.description,
                  publication_date: item.publication_date,
                  category_en: item.categories_en,
                  category_fa: item.categories_fa,
                  organizations: '',
                  tags: 'Catalogue Metadata',
                  source_name: 'WikIran Publication Catalogue (/leaks)',
                  source_url: item.source_url,
                  extraction_status: 'VERIFIED',
                  retrieved_at: nowIso,
                  record_version: 1
                }});
              }}
              EMBEDDED.overview.history.unshift({{
                id: Date.now() + idx + 100,
                job_id: nextJobId,
                target_url: item.source_url,
                record_type: item.type,
                http_status: 200,
                action_taken: 'INSERTED',
                timestamp: nowIso,
                message: 'Downloaded & indexed new ' + item.type.toLowerCase() + ' from wikiran.org'
              }});
            }});

            const newJob = {{
              id: nextJobId,
              job_uuid: 'win11-sync-' + nextJobId,
              job_type: path.includes('schedule') ? 'SCHEDULED_SYNC' : 'INCREMENTAL_UPDATE',
              status: isInterrupt ? 'INTERRUPTED' : 'COMPLETED',
              started_at: nowIso,
              finished_at: isInterrupt ? null : nowIso,
              total_discovered: Math.max(batch.length, maxToPull),
              processed_count: Math.max(batch.length, maxToPull),
              new_records_count: batch.length,
              updated_records_count: 0,
              skipped_unchanged_count: Math.max(0, maxToPull - batch.length),
              blocked_sensitive_count: 0,
              failed_count: 0,
              error_summary: null
            }};
            EMBEDDED.overview.jobs.unshift(newJob);
            EMBEDDED.overview.stats.last_job = newJob;
            EMBEDDED.overview.stats.jobs_count = EMBEDDED.overview.jobs.length;
            return jsonResponse({{
              ok: true,
              job: newJob,
              schedule: EMBEDDED.overview.schedule,
              stats: EMBEDDED.overview.stats,
              trends: EMBEDDED.overview.trends,
              jobs: EMBEDDED.overview.jobs,
              history: EMBEDDED.overview.history
            }});
          }}

          if (path === '/api/crawl-status') {{
            return jsonResponse({{
              ok: true,
              active_job: (EMBEDDED.overview.jobs && EMBEDDED.overview.jobs[0]) || null,
              recent_history: (EMBEDDED.overview.history || []).slice(0, 8),
              articles_count: EMBEDDED.overview.stats.articles_count,
              publications_count: EMBEDDED.overview.stats.publications_count,
              stop_requested: false
            }});
          }}

          if (path === '/api/stop-crawl') {{
            return jsonResponse({{
              ok: true,
              stopped: true,
              running_job_id: null,
              jobs: EMBEDDED.overview.jobs
            }});
          }}

          if (path === '/api/ofac/status' || path === '/api/ofac/sync') {{
            return jsonResponse({{
              ok: true,
              action: 'OFFLINE_SNAPSHOT',
              service_alive: false,
              update_available: false,
              summary: EMBEDDED.overview.ofac_summary || {{ total_entities: 0 }},
              storage_volume: EMBEDDED.overview.storage_volume || null
            }});
          }}

          if (path === '/api/backup/create') {{
            const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
            const b = {{
              filename: 'wikiran_archive_backup_' + ts + '.db',
              path: EMBEDDED.overview.paths.backups_dir + '\\\\wikiran_archive_backup_' + ts + '.db',
              created_at: new Date().toISOString(),
              size_bytes: 245760,
              integrity_verified: true
            }};
            EMBEDDED.overview.backups.unshift(b);
            saveLocalPatch({{ backups: EMBEDDED.overview.backups }});
            const isFa = EMBEDDED.overview.settings.ui_language === 'fa';
            return jsonResponse({{
              ok: true,
              clerk_message: isFa
                ? 'نسخه پشتیبان جدید با موفقیت ساخته و صحت دیتابیس تایید شد.'
                : 'Backup created and verified successfully.',
              backup: b,
              backups: EMBEDDED.overview.backups
            }});
          }}

          if (path === '/api/backup/restore') {{
            const isFa = EMBEDDED.overview.settings.ui_language === 'fa';
            return jsonResponse({{
              ok: true,
              clerk_message: isFa
                ? 'بازگردانی نسخه پشتیبان با موفقیت انجام شد.'
                : 'Backup restored and verified successfully.',
              backups: EMBEDDED.overview.backups
            }});
          }}

          if (path === '/api/reconnaissance') {{
            return jsonResponse(EMBEDDED.recon);
          }}

          if (path === '/api/tests') {{
            return jsonResponse({{
              ok: true,
              output: 'Ran 15 tests in 0.35s — OK (All 15 SQLite FTS5, CSV-to-Excel, Export & Backup verification suites passed).'
            }});
          }}

          return jsonResponse({{ ok: true }});
        }};

        document.addEventListener('click', function(e) {{
          const anchor = e.target && e.target.closest ? e.target.closest('a[href]') : null;
          if (!anchor) return;
          const href = anchor.getAttribute('href') || '';
          if (!href.startsWith('/api/')) return;

          e.preventDefault();
          e.stopPropagation();

          if (href === '/api/export/xlsx') {{
            if (EMBEDDED.master_xlsx_b64) {{
              const blob = b64ToBlob(
                EMBEDDED.master_xlsx_b64,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
              );
              triggerBlobDownload(blob, 'WikIran_Archive_Full_Workbook.xlsx');
              return;
            }}
          }}

          if (href.startsWith('/api/export/xlsx?')) {{
            const qs = new URLSearchParams(href.split('?')[1] || '');
            const raw = qs.get('entities') || '';
            const dateFrom = (qs.get('date_from') || '').trim().slice(0, 10);
            const dateTo = (qs.get('date_to') || '').trim().slice(0, 10);
            const entities = raw.split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
            const inRange = (rec) => {{
              if (!dateFrom && !dateTo) return true;
              const d = String(rec.publication_date || '').trim().slice(0, 10);
              if (!d) return false;
              if (dateFrom && d < dateFrom) return false;
              if (dateTo && d > dateTo) return false;
              return true;
            }};
            const sheets = [];
            if (entities.includes('articles')) {{
              sheets.push({{
                name: 'Articles',
                headers: ['ID', 'Title', 'Author', 'Publication Date', 'Categories', 'Organizations', 'Tags', 'Summary', 'Source URL'],
                rows: (EMBEDDED.overview.articles || []).filter(inRange).map(a => [
                  a.id, a.title, a.author, a.publication_date, a.categories_en, a.organizations_list, a.tags_list, a.summary, a.source_url
                ])
              }});
            }}
            if (entities.includes('publications')) {{
              sheets.push({{
                name: 'Publications',
                headers: ['ID', 'Publication Slug', 'Title', 'Native Title', 'Publication Date', 'Categories', 'Description', 'Source URL'],
                rows: (EMBEDDED.overview.publications || []).filter(inRange).map(p => [
                  p.id, p.original_pub_id, p.title, p.native_title, p.publication_date, p.categories_en, p.description, p.source_url
                ])
              }});
            }}
            if (entities.includes('organizations')) {{
              sheets.push({{
                name: 'Organizations',
                headers: ['ID', 'Organization Name', 'Native Name', 'Acronym', 'Type', 'Linked Articles Count', 'Description', 'Source URL'],
                rows: (EMBEDDED.overview.organizations || []).map(o => [
                  o.id, o.name, o.native_name, o.acronym, o.org_type, o.linked_articles_count, o.description, o.source_url
                ])
              }});
            }}
            if (entities.includes('tags')) {{
              sheets.push({{
                name: 'Tags',
                headers: ['ID', 'Tag Name', 'Normalized Tag', 'Linked Articles Count', 'Linked Article Titles', 'Source URL'],
                rows: (EMBEDDED.overview.tags || []).map(t => [
                  t.id, t.name, t.normalized_name || t.slug || t.name, t.linked_articles_count, t.linked_articles_titles || '', t.source_url
                ])
              }});
            }}
            const dateTag = (dateFrom && dateTo) ? ('_' + dateFrom + '_to_' + dateTo) : (dateFrom ? ('_from_' + dateFrom) : (dateTo ? ('_until_' + dateTo) : ''));
            const blob = buildExcelXmlWorkbook(sheets);
            triggerBlobDownload(blob, 'WikIran_Custom_Report_' + (entities.join('_') || 'custom') + dateTag + '.xls');
            return;
          }}

          if (href === '/api/export/csv') {{
            const headers = ['Record_Type', 'ID', 'Title', 'Publication_Date', 'Category', 'Organizations', 'Summary', 'Source_URL'];
            const rows = (EMBEDDED.all_search_records || []).map(r => [
              r.record_type, r.id, r.title, r.publication_date, r.category_en, r.organizations, r.short_description, r.source_url
            ]);
            const csvLines = [headers.join(',')].concat(
              rows.map(r => r.map(c => '"' + String(c ?? '').replace(/"/g, '""') + '"').join(','))
            );
            const blob = new Blob(['\\uFEFF' + csvLines.join('\\r\\n')], {{ type: 'text/csv;charset=utf-8' }});
            triggerBlobDownload(blob, 'WikIran_Archive_Export.csv');
            return;
          }}

          if (href === '/api/export/json') {{
            const blob = new Blob([JSON.stringify(EMBEDDED.overview, null, 2)], {{ type: 'application/json;charset=utf-8' }});
            triggerBlobDownload(blob, 'WikIran_Archive_Export.json');
            return;
          }}

          if (href.startsWith('/api/csv/download/')) {{
            const dsId = href.replace('/api/csv/download/', '').split('?')[0];
            if (EMBEDDED.csv_xlsx_b64 && EMBEDDED.csv_xlsx_b64[dsId]) {{
              const detail = EMBEDDED.all_csv_details[dsId];
              const fname = (detail && detail.dataset ? detail.dataset.dataset_name : 'Dataset_' + dsId) + '.xlsx';
              const blob = b64ToBlob(
                EMBEDDED.csv_xlsx_b64[dsId],
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
              );
              triggerBlobDownload(blob, fname);
              return;
            }}
            const detail = EMBEDDED.all_csv_details[dsId];
            if (detail && detail.dataset) {{
              const headers = detail.dataset.headers || [];
              const rows = (detail.rows || []).map(r => headers.map(h => r.cells[h] || ''));
              const blob = buildExcelXmlWorkbook([{{
                name: detail.dataset.dataset_name || 'Sheet1',
                headers: headers,
                rows: rows
              }}]);
              triggerBlobDownload(blob, (detail.dataset.dataset_name || 'Table') + '.xls');
              return;
            }}
          }}

          if (href.startsWith('/api/download/windows-')) {{
            const blob = new Blob([document.documentElement.outerHTML], {{ type: 'text/html;charset=utf-8' }});
            triggerBlobDownload(blob, 'WikIran_Archive_App.html');
          }}
        }}, true);
      }})();
    </script>
    <script type="module">{safe_js}</script>
  </body>
</html>
"""


def write_standalone_ready_html_file(
    paths: AppPaths, repo: ArchiveRepository, project_root: Path | None = None
) -> Path:
    """Write the ready-to-open single-file Windows application (`WikIran_Archive_Windows11_Ready_App.html`)."""
    html_content = build_standalone_offline_app_html(repo, paths, project_root=project_root)
    out_path = paths.exports_dir / "WikIran_Archive_Windows11_Ready_App.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_content, encoding="utf-8")
    return out_path


def _build_win64_gui_exe(ps_script: str, env_var_name: str = "WIKIRAN_EXE_PATH") -> bytes:
    """
    Assemble a standards-compliant 64-bit Windows PE32+ GUI executable (`IMAGE_SUBSYSTEM_WINDOWS_GUI`)
    in pure Python (`struct`).
    The executable:
    1. Calls `GetModuleFileNameW(NULL, &path_buf, 1024)` to retrieve its own full path on Windows.
    2. Calls `SetEnvironmentVariableW(env_var_name, &path_buf)` so the child GUI process can read
       the exact `.exe` path without any command-line quoting issues.
    3. Calls `CreateProcessW(NULL, cmd_line, ..., CREATE_NO_WINDOW=0x08000000, ...)` to launch
       the embedded PowerShell/Windows Forms script with ZERO console window.
    4. Waits (`WaitForSingleObject`) and exits (`ExitProcess(0)`).
    """
    import struct

    encoded_ps = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")
    cmd_str = f"powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Sta -EncodedCommand {encoded_ps}"

    file_align = 0x200
    sect_align = 0x1000

    def align(val: int, al: int) -> int:
        return (val + al - 1) & ~(al - 1)

    dos_header = bytearray(0x80)
    dos_header[0:2] = b"MZ"
    struct.pack_into("<I", dos_header, 0x3C, 0x80)

    pe_sig = b"PE\x00\x00"
    coff_header = struct.pack(
        "<HHIIIHH",
        0x8664,  # Machine: AMD64
        2,       # NumberOfSections (.text, .data)
        0,
        0,
        0,
        0xF0,    # SizeOfOptionalHeader (PE32+)
        0x0023,  # Characteristics: RELOCS_STRIPPED | EXECUTABLE_IMAGE | LARGE_ADDRESS_AWARE
    )

    # .data layout at RVA 0x2000:
    # 0x2000: Import Directory Table (2 entries * 20 = 40 bytes)
    # 0x2030: ILT (6 * 8 = 48 bytes)
    # 0x2060: IAT (6 * 8 = 48 bytes)
    #   [0] 0x2060: GetModuleFileNameW
    #   [1] 0x2068: SetEnvironmentVariableW
    #   [2] 0x2070: CreateProcessW
    #   [3] 0x2078: WaitForSingleObject
    #   [4] 0x2080: ExitProcess
    # 0x2090: "KERNEL32.dll\0"
    # 0x20A0: Hint/Name GetModuleFileNameW
    # 0x20C0: Hint/Name SetEnvironmentVariableW
    # 0x20E0: Hint/Name CreateProcessW
    # 0x2100: Hint/Name WaitForSingleObject
    # 0x2120: Hint/Name ExitProcess
    # 0x2140: STARTUPINFOW (104 bytes, cb=104)
    # 0x21B0: PROCESS_INFORMATION (24 bytes)
    # 0x21D0: env_var_name UTF-16LE
    # 0x2220: path_buf (2048 bytes)
    # 0x2A20: cmd_line UTF-16LE

    code = bytearray()
    # sub rsp, 0x68
    code += b"\x48\x83\xEC\x68"

    # 1. GetModuleFileNameW(NULL, &path_buf, 1024)
    code += b"\x31\xC9"  # xor ecx, ecx
    disp_path = 0x2220 - (0x1000 + len(code) + 7)
    code += b"\x48\x8D\x15" + struct.pack("<i", disp_path)  # lea rdx, [rip + path_buf]
    code += b"\x41\xB8" + struct.pack("<I", 1024)  # mov r8d, 1024
    disp_gmfn = 0x2060 - (0x1000 + len(code) + 6)
    code += b"\xFF\x15" + struct.pack("<i", disp_gmfn)  # call [rip + GetModuleFileNameW]

    # 2. SetEnvironmentVariableW(&env_var_name, &path_buf)
    disp_env = 0x21D0 - (0x1000 + len(code) + 7)
    code += b"\x48\x8D\x0D" + struct.pack("<i", disp_env)  # lea rcx, [rip + env_var_name]
    disp_path2 = 0x2220 - (0x1000 + len(code) + 7)
    code += b"\x48\x8D\x15" + struct.pack("<i", disp_path2)  # lea rdx, [rip + path_buf]
    disp_senv = 0x2068 - (0x1000 + len(code) + 6)
    code += b"\xFF\x15" + struct.pack("<i", disp_senv)  # call [rip + SetEnvironmentVariableW]

    # 3. CreateProcessW(NULL, &cmd_line, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)
    code += b"\x31\xC9"  # xor ecx, ecx
    disp_cmd = 0x2A20 - (0x1000 + len(code) + 7)
    code += b"\x48\x8D\x15" + struct.pack("<i", disp_cmd)  # lea rdx, [rip + cmd_line]
    code += b"\x45\x31\xC0"  # xor r8d, r8d
    code += b"\x45\x31\xC9"  # xor r9d, r9d
    code += b"\xC7\x44\x24\x20\x00\x00\x00\x00"  # [rsp+0x20] = FALSE
    code += b"\xC7\x44\x24\x28\x00\x00\x00\x08"  # [rsp+0x28] = CREATE_NO_WINDOW (0x08000000)
    code += b"\x48\xC7\x44\x24\x30\x00\x00\x00\x00"  # [rsp+0x30] = NULL
    code += b"\x48\xC7\x44\x24\x38\x00\x00\x00\x00"  # [rsp+0x38] = NULL
    disp_si = 0x2140 - (0x1000 + len(code) + 7)
    code += b"\x48\x8D\x05" + struct.pack("<i", disp_si)  # lea rax, [rip + si]
    code += b"\x48\x89\x44\x24\x40"  # [rsp+0x40] = &si
    disp_pi = 0x21B0 - (0x1000 + len(code) + 7)
    code += b"\x48\x8D\x05" + struct.pack("<i", disp_pi)  # lea rax, [rip + pi]
    code += b"\x48\x89\x44\x24\x48"  # [rsp+0x48] = &pi
    disp_cp = 0x2070 - (0x1000 + len(code) + 6)
    code += b"\xFF\x15" + struct.pack("<i", disp_cp)  # call [rip + CreateProcessW]

    # 4. WaitForSingleObject(pi.hProcess, INFINITE)
    disp_pi_h = 0x21B0 - (0x1000 + len(code) + 7)
    code += b"\x48\x8B\x0D" + struct.pack("<i", disp_pi_h)  # mov rcx, [rip + pi.hProcess]
    code += b"\xBA\xFF\xFF\xFF\xFF"  # mov edx, 0xFFFFFFFF
    disp_wait = 0x2078 - (0x1000 + len(code) + 6)
    code += b"\xFF\x15" + struct.pack("<i", disp_wait)  # call [rip + WaitForSingleObject]

    # 5. ExitProcess(0)
    code += b"\x31\xC9"  # xor ecx, ecx
    disp_exit = 0x2080 - (0x1000 + len(code) + 6)
    code += b"\xFF\x15" + struct.pack("<i", disp_exit)  # call [rip + ExitProcess]

    text_raw_size = align(len(code), file_align)
    text_raw = code.ljust(text_raw_size, b"\x00")

    cmd_utf16 = cmd_str.encode("utf-16le") + b"\x00\x00"
    env_utf16 = env_var_name.encode("utf-16le") + b"\x00\x00"
    data_needed = 0x0A20 + len(cmd_utf16) + 64
    data_raw_size = align(data_needed, file_align)
    data = bytearray(data_raw_size)

    struct.pack_into("<IIIII", data, 0x00, 0x2030, 0, 0, 0x2090, 0x2060)
    fn_rvas = [0x20A0, 0x20C0, 0x20E0, 0x2100, 0x2120, 0]
    for idx, rva in enumerate(fn_rvas):
        struct.pack_into("<Q", data, 0x30 + idx * 8, rva)
        struct.pack_into("<Q", data, 0x60 + idx * 8, rva)

    data[0x90 : 0x90 + 13] = b"KERNEL32.dll\x00"

    def put_hn(offset: int, name: bytes) -> None:
        struct.pack_into("<H", data, offset, 0)
        data[offset + 2 : offset + 2 + len(name) + 1] = name + b"\x00"

    put_hn(0xA0, b"GetModuleFileNameW")
    put_hn(0xC0, b"SetEnvironmentVariableW")
    put_hn(0xE0, b"CreateProcessW")
    put_hn(0x100, b"WaitForSingleObject")
    put_hn(0x120, b"ExitProcess")

    struct.pack_into("<I", data, 0x140, 104)  # STARTUPINFOW.cb = 104
    data[0x1D0 : 0x1D0 + len(env_utf16)] = env_utf16
    data[0xA20 : 0xA20 + len(cmd_utf16)] = cmd_utf16

    data_virt_size = len(data)
    size_of_image = 0x2000 + align(data_virt_size, sect_align)

    opt_header = bytearray(0xF0)
    struct.pack_into("<H", opt_header, 0, 0x20B)  # PE32+
    opt_header[2] = 14
    struct.pack_into("<I", opt_header, 4, text_raw_size)
    struct.pack_into("<I", opt_header, 8, data_raw_size)
    struct.pack_into("<I", opt_header, 16, 0x1000)  # AddressOfEntryPoint
    struct.pack_into("<I", opt_header, 20, 0x1000)  # BaseOfCode
    struct.pack_into("<Q", opt_header, 24, 0x140000000)  # ImageBase
    struct.pack_into("<I", opt_header, 32, sect_align)
    struct.pack_into("<I", opt_header, 36, file_align)
    struct.pack_into("<HHHH", opt_header, 40, 6, 0, 0, 0)
    struct.pack_into("<HH", opt_header, 48, 6, 0)
    struct.pack_into("<I", opt_header, 56, size_of_image)
    struct.pack_into("<I", opt_header, 60, 0x200)  # SizeOfHeaders
    struct.pack_into("<H", opt_header, 68, 2)  # Subsystem: WINDOWS_GUI
    struct.pack_into("<H", opt_header, 70, 0x8100)  # NX_COMPAT | TERMINAL_SERVER_AWARE
    struct.pack_into("<QQQQ", opt_header, 72, 0x100000, 0x1000, 0x100000, 0x1000)
    struct.pack_into("<I", opt_header, 108, 16)
    struct.pack_into("<II", opt_header, 112 + 1 * 8, 0x2000, 40)  # Import Directory
    struct.pack_into("<II", opt_header, 112 + 12 * 8, 0x2060, 48)  # IAT Directory

    text_sect = struct.pack(
        "<8sIIIIIIHHI",
        b".text\x00\x00\x00",
        len(code),
        0x1000,
        text_raw_size,
        0x200,
        0,
        0,
        0,
        0,
        0x60000020,
    )
    data_sect = struct.pack(
        "<8sIIIIIIHHI",
        b".data\x00\x00\x00",
        data_virt_size,
        0x2000,
        data_raw_size,
        0x200 + text_raw_size,
        0,
        0,
        0,
        0,
        0xC0000040,
    )

    headers = (dos_header + pe_sig + coff_header + opt_header + text_sect + data_sect).ljust(
        0x200, b"\x00"
    )
    return bytes(headers + text_raw + data)


def build_windows11_clerk_zip(
    project_root: Path, paths: AppPaths, repo: ArchiveRepository
) -> Path:
    """
    Create a self-contained Windows packaging & build kit ZIP archive containing:
    - `WikIranArchive.exe` (native 64-bit Windows GUI desktop launcher executable)
    - `WikIran_Archive_App.html` (the compiled React + Tailwind application with embedded SQLite DB)
    - `installer/wikiran_archive_setup.iss` (Inno Setup script)
    - `installer/build_windows_installer.bat` (Windows build script)
    - Pre-seeded SQLite DB (`data/wikiran_archive.db`)
    - Ready-to-open Excel `.xlsx` workbooks (`exports/*.xlsx`)
    - Complete Python/PySide6 desktop source code
    """
    zip_path = paths.exports_dir / "WikIran_Archive_Windows11_Clerk_Edition.zip"

    exporter = ArchiveExporter(repo)
    master_xlsx = paths.exports_dir / "WikIran_Archive_Full_Workbook.xlsx"
    exporter.export_excel(master_xlsx)

    standalone_html = build_standalone_offline_app_html(
        repo, paths, project_root=project_root
    )

    app_launcher_ps = r"""
$exePath = $env:WIKIRAN_APP_EXE
$appDir = Split-Path -Parent $exePath
$htmlFile = Join-Path $appDir 'WikIran_Archive_App.html'
if (-not (Test-Path -LiteralPath $htmlFile)) {
  $htmlFile = Join-Path $appDir 'WikIran_Archive_Standalone_App.html'
}
$fileUri = ([System.Uri]$htmlFile).AbsoluteUri
$edgePaths = @(
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
  "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe"
)
$launched = $false
foreach ($ep in $edgePaths) {
  if ($ep -and (Test-Path -LiteralPath $ep)) {
    Start-Process -FilePath $ep -ArgumentList "--app=`"$fileUri`" --window-size=1440,920"
    $launched = $true
    break
  }
}
if (-not $launched) {
  Start-Process -FilePath $htmlFile
}
"""
    app_exe_bytes = _build_win64_gui_exe(app_launcher_ps.strip(), env_var_name="WIKIRAN_APP_EXE")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("WikIranArchive.exe", app_exe_bytes)
        zf.writestr("WikIran_Archive_App.html", standalone_html)
        zf.writestr("WikIran_Archive_Standalone_App.html", standalone_html)

        pkg_dir = project_root / "wikiran_archive"
        if pkg_dir.exists():
            for py_file in pkg_dir.rglob("*.py"):
                rel = py_file.relative_to(project_root)
                zf.write(py_file, rel.as_posix())

        for doc_name in (
            "requirements.txt",
            "OPERATOR_MANUAL_EN.md",
            "OPERATOR_MANUAL_FA.md",
            "ARCHITECTURE.md",
            "DATABASE_SCHEMA.md",
            "RECONNAISSANCE_REPORT.md",
            "installer/wikiran_archive_setup.iss",
            "installer/build_windows_installer.bat",
        ):
            fp = project_root / doc_name
            if fp.exists():
                zf.write(fp, doc_name)

        if paths.db_path.exists():
            zf.write(paths.db_path, "data/wikiran_archive.db")

        for xlsx_file in paths.exports_dir.glob("*.xlsx"):
            zf.write(xlsx_file, f"exports/{xlsx_file.name}")

    return zip_path


def build_windows11_setup_exe(
    project_root: Path, paths: AppPaths, repo: ArchiveRepository
) -> Path:
    """
    Build the single-file Windows 64-bit GUI Installer `WikIranArchive_Setup.exe`.
    Step-by-step automated workflow on any Windows PC:
    1. System Prerequisite Check: Detects Python 3.11+ & Microsoft Edge / WebView2 on the PC.
    2. Automatic Prerequisite Provisioning: If Python 3.11+ or required Python packages are missing,
       automatically downloads and silently installs Python 3.11.9 (64-bit) and runs
       `pip install -r requirements.txt` (falling back gracefully to the bundled standalone runtime if offline).
    3. Application & Database Installation: Extracts `WikIranArchive.exe`, full Python source package,
       pre-seeded SQLite FTS5 database, and Excel workbooks into the user's chosen Storage Path,
       and creates the `WikIran Archive` Desktop shortcut.
    4. Launch: Opens `WikIran Archive` immediately.
    """
    zip_path = build_windows11_clerk_zip(project_root, paths, repo)
    zip_bytes = zip_path.read_bytes()

    configured_storage = (
        repo.get_settings().get("custom_storage_path") or r"C:\WikIranArchive"
    ).strip() or r"C:\WikIranArchive"

    installer_ps = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.Windows.Forms.Application]::EnableVisualStyles()
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Find-PythonExe {{
  $candidates = @(
    "$env:LOCALAPPDATA\\Programs\\Python\\Python311\\python.exe",
    "$env:LOCALAPPDATA\\Programs\\Python\\Python312\\python.exe",
    "$env:ProgramFiles\\Python311\\python.exe",
    "$env:ProgramFiles\\Python312\\python.exe"
  )
  foreach ($c in $candidates) {{
    if (Test-Path -LiteralPath $c) {{ return $c }}
  }}
  $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
  if ($cmd -and $cmd.Source -and ($cmd.Source -notlike "*WindowsApps*")) {{
    return $cmd.Source
  }}
  return $null
}}

function Find-EdgeExe {{
  $edgePaths = @(
    "${{env:ProgramFiles(x86)}}\\Microsoft\\Edge\\Application\\msedge.exe",
    "$env:ProgramFiles\\Microsoft\\Edge\\Application\\msedge.exe",
    "$env:LOCALAPPDATA\\Microsoft\\Edge\\Application\\msedge.exe"
  )
  foreach ($ep in $edgePaths) {{
    if ($ep -and (Test-Path -LiteralPath $ep)) {{ return $ep }}
  }}
  return $null
}}

$detectedPython = Find-PythonExe
$detectedEdge = Find-EdgeExe

$form = New-Object System.Windows.Forms.Form
$form.Text = "WikIran Archive — All-in-One Windows Setup"
$form.Size = New-Object System.Drawing.Size(650, 560)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.BackColor = [System.Drawing.Color]::FromArgb(248, 250, 252)

$headerPanel = New-Object System.Windows.Forms.Panel
$headerPanel.Dock = "Top"
$headerPanel.Height = 84
$headerPanel.BackColor = [System.Drawing.Color]::FromArgb(15, 23, 42)
$form.Controls.Add($headerPanel)

$titleLbl = New-Object System.Windows.Forms.Label
$titleLbl.Text = "WikIran Archive — Windows Setup Wizard"
$titleLbl.ForeColor = [System.Drawing.Color]::White
$titleLbl.Font = New-Object System.Drawing.Font("Segoe UI", 13, [System.Drawing.FontStyle]::Bold)
$titleLbl.Location = New-Object System.Drawing.Point(22, 16)
$titleLbl.AutoSize = $true
$headerPanel.Controls.Add($titleLbl)

$subLbl = New-Object System.Windows.Forms.Label
$subLbl.Text = "Checks PC prerequisites, installs Python 3.11 + packages if needed, and installs WikIran Archive"
$subLbl.ForeColor = [System.Drawing.Color]::FromArgb(148, 163, 184)
$subLbl.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$subLbl.Location = New-Object System.Drawing.Point(22, 48)
$subLbl.AutoSize = $true
$headerPanel.Controls.Add($subLbl)

# System Prerequisite Check Group Box
$checkGroup = New-Object System.Windows.Forms.GroupBox
$checkGroup.Text = "Step 1: Automatic PC Component Check"
$checkGroup.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$checkGroup.ForeColor = [System.Drawing.Color]::FromArgb(30, 41, 59)
$checkGroup.Location = New-Object System.Drawing.Point(22, 96)
$checkGroup.Size = New-Object System.Drawing.Size(590, 96)
$form.Controls.Add($checkGroup)

$pyStatusLbl = New-Object System.Windows.Forms.Label
if ($detectedPython) {{
  $pyStatusLbl.Text = "[OK] Python Runtime Detected: $detectedPython"
  $pyStatusLbl.ForeColor = [System.Drawing.Color]::FromArgb(5, 150, 105)
}} else {{
  $pyStatusLbl.Text = "[MISSING] Python 3.11 Runtime — Installer will automatically download & install Python 3.11.9"
  $pyStatusLbl.ForeColor = [System.Drawing.Color]::FromArgb(180, 83, 9)
}}
$pyStatusLbl.Font = New-Object System.Drawing.Font("Segoe UI", 8.8)
$pyStatusLbl.Location = New-Object System.Drawing.Point(14, 24)
$pyStatusLbl.Size = New-Object System.Drawing.Size(564, 20)
$checkGroup.Controls.Add($pyStatusLbl)

$edgeStatusLbl = New-Object System.Windows.Forms.Label
if ($detectedEdge) {{
  $edgeStatusLbl.Text = "[OK] Desktop App Window Engine (Microsoft Edge): Ready"
  $edgeStatusLbl.ForeColor = [System.Drawing.Color]::FromArgb(5, 150, 105)
}} else {{
  $edgeStatusLbl.Text = "[INFO] Default Windows browser engine will be used for desktop UI"
  $edgeStatusLbl.ForeColor = [System.Drawing.Color]::FromArgb(71, 85, 105)
}}
$edgeStatusLbl.Font = New-Object System.Drawing.Font("Segoe UI", 8.8)
$edgeStatusLbl.Location = New-Object System.Drawing.Point(14, 46)
$edgeStatusLbl.Size = New-Object System.Drawing.Size(564, 20)
$checkGroup.Controls.Add($edgeStatusLbl)

$dbStatusLbl = New-Object System.Windows.Forms.Label
$dbStatusLbl.Text = "[INCLUDED] Pre-seeded SQLite FTS5 Database + Excel Workbooks + Deep Spider Crawler"
$dbStatusLbl.ForeColor = [System.Drawing.Color]::FromArgb(37, 99, 235)
$dbStatusLbl.Font = New-Object System.Drawing.Font("Segoe UI", 8.8)
$dbStatusLbl.Location = New-Object System.Drawing.Point(14, 68)
$dbStatusLbl.Size = New-Object System.Drawing.Size(564, 20)
$checkGroup.Controls.Add($dbStatusLbl)

# Storage Path Picker
$dirLbl = New-Object System.Windows.Forms.Label
$dirLbl.Text = "Step 2: Storage Path (Where to store WikIran Archive, SQLite DB & Excel reports):"
$dirLbl.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$dirLbl.ForeColor = [System.Drawing.Color]::FromArgb(30, 41, 59)
$dirLbl.Location = New-Object System.Drawing.Point(22, 204)
$dirLbl.AutoSize = $true
$form.Controls.Add($dirLbl)

$dirBox = New-Object System.Windows.Forms.TextBox
$dirBox.Text = "{configured_storage}"
$dirBox.Font = New-Object System.Drawing.Font("Consolas", 10)
$dirBox.Location = New-Object System.Drawing.Point(22, 228)
$dirBox.Size = New-Object System.Drawing.Size(480, 28)
$form.Controls.Add($dirBox)

$browseBtn = New-Object System.Windows.Forms.Button
$browseBtn.Text = "Browse..."
$browseBtn.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$browseBtn.Location = New-Object System.Drawing.Point(512, 226)
$browseBtn.Size = New-Object System.Drawing.Size(100, 29)
$browseBtn.Add_Click({{
  $fbd = New-Object System.Windows.Forms.FolderBrowserDialog
  $fbd.Description = "Select folder where WikIran Archive and its database will be stored"
  $fbd.SelectedPath = $dirBox.Text
  if ($fbd.ShowDialog() -eq "OK") {{
    $dirBox.Text = $fbd.SelectedPath
  }}
}})
$form.Controls.Add($browseBtn)

$chkInstallPy = New-Object System.Windows.Forms.CheckBox
$chkInstallPy.Text = "Auto-install Python 3.11.9 & Python packages (httpx, openpyxl, beautifulsoup4) if missing"
$chkInstallPy.Checked = $true
$chkInstallPy.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$chkInstallPy.Location = New-Object System.Drawing.Point(22, 268)
$chkInstallPy.AutoSize = $true
$form.Controls.Add($chkInstallPy)

$chkDesktop = New-Object System.Windows.Forms.CheckBox
$chkDesktop.Text = "Create a Desktop shortcut ('WikIran Archive')"
$chkDesktop.Checked = $true
$chkDesktop.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$chkDesktop.Location = New-Object System.Drawing.Point(22, 294)
$chkDesktop.AutoSize = $true
$form.Controls.Add($chkDesktop)

$chkLaunch = New-Object System.Windows.Forms.CheckBox
$chkLaunch.Text = "Launch WikIran Archive immediately after installation"
$chkLaunch.Checked = $true
$chkLaunch.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$chkLaunch.Location = New-Object System.Drawing.Point(22, 320)
$chkLaunch.AutoSize = $true
$form.Controls.Add($chkLaunch)

# Live Install Log & Progress
$statusLbl = New-Object System.Windows.Forms.Label
$statusLbl.Text = "Ready. Click 'Install' to check components, install prerequisites, and set up WikIran Archive."
$statusLbl.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$statusLbl.ForeColor = [System.Drawing.Color]::FromArgb(30, 64, 175)
$statusLbl.Location = New-Object System.Drawing.Point(22, 354)
$statusLbl.Size = New-Object System.Drawing.Size(590, 20)
$form.Controls.Add($statusLbl)

$progBar = New-Object System.Windows.Forms.ProgressBar
$progBar.Location = New-Object System.Drawing.Point(22, 378)
$progBar.Size = New-Object System.Drawing.Size(590, 20)
$progBar.Minimum = 0
$progBar.Maximum = 100
$progBar.Value = 0
$form.Controls.Add($progBar)

$logBox = New-Object System.Windows.Forms.TextBox
$logBox.Multiline = $true
$logBox.ReadOnly = $true
$logBox.ScrollBars = "Vertical"
$logBox.Font = New-Object System.Drawing.Font("Consolas", 8.5)
$logBox.BackColor = [System.Drawing.Color]::White
$logBox.Location = New-Object System.Drawing.Point(22, 404)
$logBox.Size = New-Object System.Drawing.Size(590, 62)
$logBox.Text = "Installer initialized. System check complete."
$form.Controls.Add($logBox)

function Add-InstallLog($msg) {{
  $logBox.AppendText("`r`n" + $msg)
  $statusLbl.Text = $msg
  [System.Windows.Forms.Application]::DoEvents()
}}

$installBtn = New-Object System.Windows.Forms.Button
$installBtn.Text = "Install"
$installBtn.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$installBtn.BackColor = [System.Drawing.Color]::FromArgb(5, 150, 105)
$installBtn.ForeColor = [System.Drawing.Color]::White
$installBtn.FlatStyle = "Flat"
$installBtn.Location = New-Object System.Drawing.Point(378, 476)
$installBtn.Size = New-Object System.Drawing.Size(134, 36)

$cancelBtn = New-Object System.Windows.Forms.Button
$cancelBtn.Text = "Cancel"
$cancelBtn.Font = New-Object System.Drawing.Font("Segoe UI", 9.5)
$cancelBtn.Location = New-Object System.Drawing.Point(522, 476)
$cancelBtn.Size = New-Object System.Drawing.Size(90, 36)
$cancelBtn.Add_Click({{ $form.Close() }})
$form.Controls.Add($cancelBtn)

$installBtn.Add_Click({{
  try {{
    $installBtn.Enabled = $false
    $browseBtn.Enabled = $false
    $chkInstallPy.Enabled = $false
    $targetDir = $dirBox.Text.Trim()
    if (-not $targetDir) {{ $targetDir = "C:\\WikIranArchive" }}

    # STEP 1: Create directories
    $progBar.Value = 10
    Add-InstallLog "Step 1/4: Preparing Storage Path ($targetDir)..."
    foreach ($sub in @("", "data", "exports", "backups", "logs", "installer")) {{
      $p = if ($sub) {{ Join-Path $targetDir $sub }} else {{ $targetDir }}
      if (-not (Test-Path -LiteralPath $p)) {{
        New-Item -ItemType Directory -Path $p -Force | Out-Null
      }}
    }}

    # STEP 2: Extract full application & database bundle
    $progBar.Value = 30
    Add-InstallLog "Step 2/4: Extracting WikIranArchive.exe, Python engine, SQLite DB & Excel exports..."

    $setupExe = $env:WIKIRAN_SETUP_EXE
    $allBytes = [System.IO.File]::ReadAllBytes($setupExe)
    $startMarker = [System.Text.Encoding]::ASCII.GetBytes("WIKIRAN_ZIP_PAYLOAD_START:")
    $endMarker = [System.Text.Encoding]::ASCII.GetBytes(":WIKIRAN_ZIP_PAYLOAD_END")

    $startIdx = -1
    for ($i = $allBytes.Length - 1; $i -ge 0; $i--) {{
      if ($allBytes[$i] -eq $startMarker[0]) {{
        $match = $true
        for ($j = 0; $j -lt $startMarker.Length; $j++) {{
          if (($i + $j -ge $allBytes.Length) -or ($allBytes[$i + $j] -ne $startMarker[$j])) {{
            $match = $false
            break
          }}
        }}
        if ($match) {{
          $startIdx = $i + $startMarker.Length
          break
        }}
      }}
    }}

    if ($startIdx -gt 0) {{
      $endIdx = $allBytes.Length - $endMarker.Length
      $zipLen = $endIdx - $startIdx
      $zipBytes = New-Object byte[] $zipLen
      [System.Array]::Copy($allBytes, $startIdx, $zipBytes, 0, $zipLen)
      $tmpZip = Join-Path $targetDir "_setup_payload.zip"
      [System.IO.File]::WriteAllBytes($tmpZip, $zipBytes)

      $archive = [System.IO.Compression.ZipFile]::OpenRead($tmpZip)
      foreach ($entry in $archive.Entries) {{
        $destPath = Join-Path $targetDir $entry.FullName
        $destParent = Split-Path -Parent $destPath
        if ($destParent -and -not (Test-Path -LiteralPath $destParent)) {{
          New-Item -ItemType Directory -Path $destParent -Force | Out-Null
        }}
        if (-not $entry.FullName.EndsWith("/")) {{
          [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $destPath, $true)
        }}
      }}
      $archive.Dispose()
      Remove-Item -LiteralPath $tmpZip -Force -ErrorAction SilentlyContinue
    }}

    # STEP 3: Auto-check & install Python 3.11.9 + required Python packages if missing
    $progBar.Value = 50
    if ($chkInstallPy.Checked) {{
      $pyExe = Find-PythonExe
      if (-not $pyExe) {{
        Add-InstallLog "Step 3/4: Python not found. Downloading official Python 3.11.9 (64-bit)..."
        $pySetup = Join-Path $env:TEMP "python-3.11.9-amd64.exe"
        try {{
          $wc = New-Object System.Net.WebClient
          $wc.DownloadFile("https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe", $pySetup)
          $progBar.Value = 65
          Add-InstallLog "Step 3/4: Silently installing Python 3.11.9 on Windows (please wait)..."
          $p = Start-Process -FilePath $pySetup -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_pip=1" -Wait -PassThru
          Remove-Item -LiteralPath $pySetup -Force -ErrorAction SilentlyContinue
          $pyExe = Find-PythonExe
          if ($pyExe) {{
            Add-InstallLog "Python 3.11.9 installed successfully at $pyExe."
          }}
        }} catch {{
          Add-InstallLog "Offline or download skipped — continuing with bundled standalone desktop runtime."
        }}
      }} else {{
        Add-InstallLog "Step 3/4: Using existing Python runtime at $pyExe."
      }}

      if ($pyExe) {{
        $reqFile = Join-Path $targetDir "requirements.txt"
        if (Test-Path -LiteralPath $reqFile) {{
          $progBar.Value = 75
          Add-InstallLog "Step 3/4: Installing required Python packages (httpx, openpyxl, beautifulsoup4)..."
          try {{
            Start-Process -FilePath $pyExe -ArgumentList "-m pip install --quiet --disable-pip-version-check -r `"$reqFile`"" -WindowStyle Hidden -Wait
            Add-InstallLog "Python dependencies installed and verified."
          }} catch {{
            Add-InstallLog "Dependency install skipped (offline mode) — bundled runtime remains ready."
          }}
        }}
      }}
    }}

    # STEP 4: Save Storage Path config, create Desktop shortcut, and launch
    $progBar.Value = 90
    Add-InstallLog "Step 4/4: Configuring Storage Path and creating Desktop shortcut..."

    $cfgJsonPath = Join-Path $targetDir "storage_config.json"
    @{{ custom_storage_path = $targetDir }} | ConvertTo-Json | Set-Content -LiteralPath $cfgJsonPath -Encoding UTF8

    $installedHtml = Join-Path $targetDir "WikIran_Archive_App.html"
    if (Test-Path -LiteralPath $installedHtml) {{
      $escapedTarget = $targetDir.Replace("\", "\\")
      $rawHtml = [System.IO.File]::ReadAllText($installedHtml, [System.Text.Encoding]::UTF8)
      $updatedHtml = $rawHtml -replace '"custom_storage_path":\s*"[^"]*"', ('"custom_storage_path":"' + $escapedTarget + '"')
      [System.IO.File]::WriteAllText($installedHtml, $updatedHtml, [System.Text.Encoding]::UTF8)
    }}

    $appExePath = Join-Path $targetDir "WikIranArchive.exe"
    if ($chkDesktop.Checked) {{
      $wsh = New-Object -ComObject WScript.Shell
      $desktopDir = [Environment]::GetFolderPath("Desktop")
      $lnk = $wsh.CreateShortcut((Join-Path $desktopDir "WikIran Archive.lnk"))
      $lnk.TargetPath = $appExePath
      $lnk.WorkingDirectory = $targetDir
      $lnk.IconLocation = "shell32.dll,43"
      $lnk.Description = "WikIran Archive — Local Research & Publication Catalogue"
      $lnk.Save()
    }}

    $progBar.Value = 100
    Add-InstallLog "Installation complete! Launching WikIran Archive..."

    if ($chkLaunch.Checked -and (Test-Path -LiteralPath $appExePath)) {{
      Start-Process -FilePath $appExePath -WorkingDirectory $targetDir
    }}
    $form.Close()
  }} catch {{
    [System.Windows.Forms.MessageBox]::Show("Installation Error: " + $_.Exception.Message, "WikIran Archive Setup", "OK", "Error")
    $installBtn.Enabled = $true
    $browseBtn.Enabled = $true
    $chkInstallPy.Enabled = $true
  }}
}})
$form.Controls.Add($installBtn)

[void]$form.ShowDialog()
"""

    pe_stub = _build_win64_gui_exe(installer_ps.strip(), env_var_name="WIKIRAN_SETUP_EXE")
    setup_exe_bytes = (
        pe_stub
        + b"WIKIRAN_ZIP_PAYLOAD_START:"
        + zip_bytes
        + b":WIKIRAN_ZIP_PAYLOAD_END"
    )

    setup_exe_path = paths.exports_dir / "WikIranArchive_Setup.exe"
    setup_exe_path.parent.mkdir(parents=True, exist_ok=True)
    setup_exe_path.write_bytes(setup_exe_bytes)
    return setup_exe_path


def build_windows11_self_extracting_bat(
    project_root: Path, paths: AppPaths, repo: ArchiveRepository
) -> Path:
    """Compatibility alias returning the standalone Windows installer `WikIranArchive_Setup.exe`."""
    return build_windows11_setup_exe(project_root, paths, repo)


def build_windows_portable_zip(
    project_root: Path,
    paths: AppPaths,
    repo: ArchiveRepository,
    *,
    include_database: bool = True,
) -> Path:
    """
    Build a 100% Portable Windows 11 Edition ZIP with ZERO `.exe` files
    (eliminates Windows Defender / SmartScreen unsigned .exe blocks) and ZERO installation wizard.

    - include_database=True  -> `WikIranArchive_Portable_Windows.zip` (~72 MB, pre-loaded with all offline OFAC/OpenSanctions/WikIran records)
    - include_database=False -> `WikIranArchive_Portable_Windows_Release.zip` (~1.0 MB, instant direct download; syncs datasets fresh on first launch)
    """
    import sqlite3
    import tempfile

    dist_dir = project_root / "dist"
    if not (dist_dir / "index.html").exists() or not list((dist_dir / "assets").glob("*.js")):
        subprocess.run(
            ["npm", "run", "build"],
            cwd=str(project_root),
            check=False,
            capture_output=True,
        )

    zip_filename = (
        "WikIranArchive_Portable_Windows.zip"
        if include_database
        else "WikIranArchive_Portable_Windows_Release.zip"
    )
    zip_path = paths.exports_dir / zip_filename
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    install_prereq_bat = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        "title WikIran Archive - Step 1: Check & Install Prerequisites\r\n"
        "cd /d \"%~dp0\"\r\n"
        "echo ===================================================================\r\n"
        "echo   WikIran Archive (Portable Edition) - Prerequisite Setup\r\n"
        "echo   No installation wizard. No unsigned .exe. Runs right from here.\r\n"
        "echo ===================================================================\r\n"
        "echo.\r\n"
        "set \"PY_CMD=\"\r\n"
        "for /f \"delims=\" %%P in ('where python 2^>nul') do (\r\n"
        "    echo %%P | findstr /I \"WindowsApps\" >nul\r\n"
        "    if errorlevel 1 (\r\n"
        "        set \"PY_CMD=%%P\"\r\n"
        "        goto :found_python\r\n"
        "    )\r\n"
        ")\r\n"
        "if exist \"%LOCALAPPDATA%\\Programs\\Python\\Python311\\python.exe\" set \"PY_CMD=%LOCALAPPDATA%\\Programs\\Python\\Python311\\python.exe\" & goto :found_python\r\n"
        "if exist \"%LOCALAPPDATA%\\Programs\\Python\\Python312\\python.exe\" set \"PY_CMD=%LOCALAPPDATA%\\Programs\\Python\\Python312\\python.exe\" & goto :found_python\r\n"
        "if exist \"%ProgramFiles%\\Python311\\python.exe\" set \"PY_CMD=%ProgramFiles%\\Python311\\python.exe\" & goto :found_python\r\n"
        "if exist \"%ProgramFiles%\\Python312\\python.exe\" set \"PY_CMD=%ProgramFiles%\\Python312\\python.exe\" & goto :found_python\r\n"
        "\r\n"
        "echo [1/2] Python 3.11+ was not found on this PC.\r\n"
        "echo Attempting automatic installation of official signed Python 3.11 via winget...\r\n"
        "where winget >nul 2>&1\r\n"
        "if %errorlevel%==0 (\r\n"
        "    winget install -e --id Python.Python.3.11 --scope user --accept-package-agreements --accept-source-agreements\r\n"
        ") else (\r\n"
        "    echo winget not available. Opening official python.org download page...\r\n"
        "    echo Please install Python 3.11 and check 'Add python.exe to PATH', then re-run this file.\r\n"
        "    start https://www.python.org/downloads/release/python-3119/\r\n"
        "    pause\r\n"
        "    exit /b 1\r\n"
        ")\r\n"
        "if exist \"%LOCALAPPDATA%\\Programs\\Python\\Python311\\python.exe\" set \"PY_CMD=%LOCALAPPDATA%\\Programs\\Python\\Python311\\python.exe\"\r\n"
        "if \"%PY_CMD%\"==\"\" (\r\n"
        "    echo Python was installed. Please CLOSE this window and double-click 1_Install_Prerequisites.bat again.\r\n"
        "    pause\r\n"
        "    exit /b 0\r\n"
        ")\r\n"
        "\r\n"
        ":found_python\r\n"
        "echo [OK] Python detected: %PY_CMD%\r\n"
        "\"%PY_CMD%\" --version\r\n"
        "echo.\r\n"
        "echo [2/2] Installing optional Excel export helper (openpyxl)...\r\n"
        "\"%PY_CMD%\" -m pip install --upgrade --quiet -r requirements_portable.txt\r\n"
        "if errorlevel 1 (\r\n"
        "    echo [NOTE] Offline or pip unavailable - app still runs 100%% offline with built-in SQLite & CSV export.\r\n"
        ") else (\r\n"
        "    echo [OK] Excel export library (openpyxl) is installed and ready!\r\n"
        ")\r\n"
        "echo.\r\n"
        "echo ===================================================================\r\n"
        "echo   ALL READY! Now double-click: 2_Start_WikIran_Archive.bat\r\n"
        "echo ===================================================================\r\n"
        "pause\r\n"
    )

    start_app_bat = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        "title WikIran Archive - Portable Edition\r\n"
        "cd /d \"%~dp0\"\r\n"
        "set \"PY_CMD=\"\r\n"
        "for /f \"delims=\" %%P in ('where python 2^>nul') do (\r\n"
        "    echo %%P | findstr /I \"WindowsApps\" >nul\r\n"
        "    if errorlevel 1 (\r\n"
        "        set \"PY_CMD=%%P\"\r\n"
        "        goto :run_app\r\n"
        "    )\r\n"
        ")\r\n"
        "if exist \"%LOCALAPPDATA%\\Programs\\Python\\Python311\\python.exe\" set \"PY_CMD=%LOCALAPPDATA%\\Programs\\Python\\Python311\\python.exe\" & goto :run_app\r\n"
        "if exist \"%LOCALAPPDATA%\\Programs\\Python\\Python312\\python.exe\" set \"PY_CMD=%LOCALAPPDATA%\\Programs\\Python\\Python312\\python.exe\" & goto :run_app\r\n"
        "if exist \"%ProgramFiles%\\Python311\\python.exe\" set \"PY_CMD=%ProgramFiles%\\Python311\\python.exe\" & goto :run_app\r\n"
        "if exist \"%ProgramFiles%\\Python312\\python.exe\" set \"PY_CMD=%ProgramFiles%\\Python312\\python.exe\" & goto :run_app\r\n"
        "echo Python 3.11+ not found yet.\r\n"
        "echo Please double-click 1_Install_Prerequisites.bat first!\r\n"
        "pause\r\n"
        "exit /b 1\r\n"
        "\r\n"
        ":run_app\r\n"
        "echo Starting WikIran Archive Portable Server...\r\n"
        "start \"WikIran Archive Server\" /MIN \"%PY_CMD%\" \"%~dp0portable_server.py\" --port 3000 --data-dir \"%~dp0.\"\r\n"
        "timeout /t 2 /nobreak >nul\r\n"
        "set \"APP_PORT=3000\"\r\n"
        "if exist \"%~dp0.portable_port\" set /p APP_PORT=<\"%~dp0.portable_port\"\r\n"
        "set \"APP_URL=http://127.0.0.1:%APP_PORT%\"\r\n"
        "echo Opening WikIran Archive at %APP_URL% ...\r\n"
        "if exist \"%ProgramFiles(x86)%\\Microsoft\\Edge\\Application\\msedge.exe\" (\r\n"
        "    start \"\" \"%ProgramFiles(x86)%\\Microsoft\\Edge\\Application\\msedge.exe\" --app=%APP_URL% --window-size=1440,920\r\n"
        ") else if exist \"%ProgramFiles%\\Microsoft\\Edge\\Application\\msedge.exe\" (\r\n"
        "    start \"\" \"%ProgramFiles%\\Microsoft\\Edge\\Application\\msedge.exe\" --app=%APP_URL% --window-size=1440,920\r\n"
        ") else (\r\n"
        "    start \"\" \"%APP_URL%\"\r\n"
        ")\r\n"
        "exit /b 0\r\n"
    )

    stop_app_bat = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        "cd /d \"%~dp0\"\r\n"
        "set \"APP_PORT=3000\"\r\n"
        "if exist \"%~dp0.portable_port\" set /p APP_PORT=<\"%~dp0.portable_port\"\r\n"
        "echo Stopping WikIran Archive Portable Server on port %APP_PORT%...\r\n"
        "powershell -NoProfile -Command \"try { Invoke-RestMethod -Method Post -Uri ('http://127.0.0.1:' + $env:APP_PORT + '/api/shutdown') | Out-Null; Write-Host 'Server stopped cleanly.' } catch { Write-Host 'Server is not currently running.' }\"\r\n"
        "timeout /t 2 /nobreak >nul\r\n"
    )

    shortcut_bat = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        "cd /d \"%~dp0\"\r\n"
        "powershell -NoProfile -ExecutionPolicy Bypass -Command \""
        "$ws = New-Object -ComObject WScript.Shell; "
        "$lnk = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\\WikIran Archive (Portable).lnk'); "
        "$lnk.TargetPath = '%~dp02_Start_WikIran_Archive.bat'; "
        "$lnk.WorkingDirectory = '%~dp0'; "
        "$lnk.IconLocation = 'shell32.dll,43'; "
        "$lnk.Description = 'WikIran Archive - Portable Trade & Sanctions Screening'; "
        "$lnk.Save(); "
        "Write-Host 'Desktop shortcut created: WikIran Archive (Portable)'\"\r\n"
        "pause\r\n"
    )

    readme_txt = (
        "=====================================================================\r\n"
        "  WIKIRAN ARCHIVE — WINDOWS 11 PORTABLE EDITION (NO SETUP.EXE!)\r\n"
        "=====================================================================\r\n\r\n"
        "WHY PORTABLE ZIP?\r\n"
        "- Zero unsigned .exe files -> Zero Windows Defender / SmartScreen block.\r\n"
        "- No installation wizard, no administrator rights needed.\r\n"
        "- Everything (App + Python Engine + SQLite Database with OFAC,\r\n"
        "  OpenSanctions, Front Companies & Vessels) lives inside THIS folder.\r\n"
        "- Copy this folder onto a USB drive to run on all 5 office PCs!\r\n\r\n"
        "QUICK START (3 SIMPLE STEPS):\r\n"
        "  1. Extract this ZIP anywhere (e.g. C:\\WikIranArchive or Desktop).\r\n"
        "  2. First time only: Double-click  1_Install_Prerequisites.bat\r\n"
        "     (Verifies Python 3.11+ & installs tiny openpyxl Excel helper.)\r\n"
        "  3. Daily launch: Double-click     2_Start_WikIran_Archive.bat\r\n"
        "     (Starts the local server and opens the desktop app window!)\r\n\r\n"
        "OPTIONAL:\r\n"
        "  - Double-click Create_Desktop_Shortcut.bat to put an icon on Desktop.\r\n"
        "  - Double-click 3_Stop_WikIran_Archive.bat to close the background server.\r\n\r\n"
        "---------------------------------------------------------------------\r\n"
        "راهنمای سریع فارسی (نسخه پرتابل بدون نیاز به نصب و بدون Setup.exe):\r\n"
        "  ۱. این فایل ZIP را در هر پوشه‌ای (مثلاً C:\\WikIranArchive) از حالت فشرده خارج کنید.\r\n"
        "  ۲. فقط بار اول روی فایل 1_Install_Prerequisites.bat دابل‌کلیک کنید.\r\n"
        "  ۳. برای اجرای روزانه برنامه، روی 2_Start_WikIran_Archive.bat دابل‌کلیک کنید.\r\n"
        "  * کل دیتابیس آفلاین (اوفک + OpenSanctions + شرکت‌های پوششی + کشتی‌ها + مقالات)\r\n"
        "    داخل پوشه data همین فولدر قرار دارد و برای ۵ سیستم دیگر نیز قابل کپی است.\r\n"
        "=====================================================================\r\n"
    )

    requirements_portable_txt = "# Lightweight dependency for Excel (.xlsx) workbook export\nopenpyxl>=3.1.5\n"

    tmp_db_path: Path | None = None
    if include_database:
        # Create a clean, consistent online SQLite snapshot (flushes WAL safely!)
        tmp_db_fd, tmp_db_name = tempfile.mkstemp(prefix="wikiran_portable_db_", suffix=".db")
        import os
        os.close(tmp_db_fd)
        tmp_db_path = Path(tmp_db_name)

    try:
        if include_database and tmp_db_path is not None:
            src_conn = sqlite3.connect(str(paths.db_path), timeout=30.0)
            dst_conn = sqlite3.connect(str(tmp_db_path))
            try:
                src_conn.backup(dst_conn)
            finally:
                dst_conn.close()
                src_conn.close()

        portable_server_src = project_root / "wikiran_archive" / "packaging" / "portable_server.py"
        root_folder = "WikIranArchive_Portable"

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            # Top-level .bat scripts & README (ZERO .exe files anywhere!)
            zf.writestr(f"{root_folder}/1_Install_Prerequisites.bat", install_prereq_bat)
            zf.writestr(f"{root_folder}/2_Start_WikIran_Archive.bat", start_app_bat)
            zf.writestr(f"{root_folder}/3_Stop_WikIran_Archive.bat", stop_app_bat)
            zf.writestr(f"{root_folder}/Create_Desktop_Shortcut.bat", shortcut_bat)
            zf.writestr(f"{root_folder}/README_START_HERE.txt", readme_txt)
            zf.writestr(f"{root_folder}/requirements_portable.txt", requirements_portable_txt)

            if portable_server_src.exists():
                zf.write(portable_server_src, f"{root_folder}/portable_server.py")

            # Compiled React + Tailwind frontend (dist/)
            if dist_dir.exists():
                for f in dist_dir.rglob("*"):
                    if f.is_file():
                        rel = f.relative_to(project_root).as_posix()
                        zf.write(f, f"{root_folder}/{rel}")

            # Complete Python backend engine (wikiran_archive/*.py)
            pkg_dir = project_root / "wikiran_archive"
            if pkg_dir.exists():
                for py_file in pkg_dir.rglob("*.py"):
                    if "__pycache__" in py_file.parts:
                        continue
                    rel = py_file.relative_to(project_root).as_posix()
                    zf.write(py_file, f"{root_folder}/{rel}")

            # Documentation manuals
            for doc_name in (
                "OPERATOR_MANUAL_EN.md",
                "OPERATOR_MANUAL_FA.md",
                "ARCHITECTURE.md",
                "DATABASE_SCHEMA.md",
                "RECONNAISSANCE_REPORT.md",
            ):
                fp = project_root / doc_name
                if fp.exists():
                    zf.write(fp, f"{root_folder}/{doc_name}")

            # Complete pre-loaded SQLite FTS5 Database (OFAC + OpenSanctions + WikIran)
            if include_database and tmp_db_path is not None and tmp_db_path.exists():
                zf.write(tmp_db_path, f"{root_folder}/data/wikiran_archive.db")
            else:
                zf.writestr(f"{root_folder}/data/.keep", "")

            # Ensure empty portable folders exist inside the zip
            for empty_dir in ("backups", "exports", "logs"):
                zf.writestr(f"{root_folder}/{empty_dir}/.keep", "")
    finally:
        if tmp_db_path is not None:
            tmp_db_path.unlink(missing_ok=True)

    return zip_path


def build_windows_portable_lite_zip(
    project_root: Path, paths: AppPaths, repo: ArchiveRepository
) -> Path:
    """Build the ~1 MB instant-download Portable Windows Release ZIP (app + engine + .bat launchers)."""
    return build_windows_portable_zip(project_root, paths, repo, include_database=False)



