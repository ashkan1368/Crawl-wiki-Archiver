"""
Export engine supporting organized multi-sheet Excel (.xlsx) workbooks, CSV, and JSON.
Produces valid OpenXML (.xlsx) files with 6 dedicated sheets:
1. Articles
2. Publications
3. Organizations
4. Categories
5. Sources
6. Collection Statistics
Uses openpyxl if installed, or a standards-compliant OpenXML (.xlsx) ZIP builder so
it works reliably in all Python 3 environments without external binary dependencies.
"""

from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from ..database.repository import ArchiveRepository, utc_now_iso


def _col_letter(col_idx: int) -> str:
    """Convert 1-based column index to Excel column letter (A, B, ..., Z, AA...)."""
    result = ""
    while col_idx > 0:
        col_idx, rem = divmod(col_idx - 1, 26)
        result = chr(65 + rem) + result
    return result


def _build_worksheet_xml(headers: list[str], rows: list[list[Any]]) -> str:
    """Build valid OpenXML worksheet XML with header styling and inline strings."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        "  <sheetData>",
    ]
    all_rows = [headers] + rows
    for r_idx, row_values in enumerate(all_rows, start=1):
        lines.append(f'    <row r="{r_idx}">')
        for c_idx, val in enumerate(row_values, start=1):
            cell_ref = f"{_col_letter(c_idx)}{r_idx}"
            if isinstance(val, (int, float)) and not isinstance(val, bool) and r_idx > 1:
                lines.append(f'      <c r="{cell_ref}"><v>{val}</v></c>')
            else:
                text_val = escape(str(val if val is not None else ""))
                lines.append(
                    f'      <c r="{cell_ref}" t="inlineStr"><is><t>{text_val}</t></is></c>'
                )
        lines.append("    </row>")
    lines.append("  </sheetData>")
    lines.append("</worksheet>")
    return "\n".join(lines)


def write_multi_sheet_xlsx(output_path: Path, sheets: list[tuple[str, list[str], list[list[Any]]]]) -> Path:
    """
    Write a multi-sheet .xlsx workbook using openpyxl if present, or native OpenXML ZIP packaging.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import openpyxl  # type: ignore

        wb = openpyxl.Workbook()
        default_ws = wb.active
        for idx, (sheet_name, headers, rows) in enumerate(sheets):
            ws = default_ws if idx == 0 else wb.create_sheet(title=sheet_name[:31])
            ws.title = sheet_name[:31]
            ws.append(headers)
            for row in rows:
                ws.append([v if v is not None else "" for v in row])
        wb.save(str(output_path))
        return output_path
    except ImportError:
        pass

    # Standards-compliant OpenXML (.xlsx) generator
    content_types = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '  <Default Extension="xml" ContentType="application/xml"/>',
        '  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
    ]
    for i in range(1, len(sheets) + 1):
        content_types.append(
            f'  <Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    content_types.append("</Types>")

    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

    wb_xml = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        "  <sheets>",
    ]
    wb_rels = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
    ]
    for i, (sheet_name, _, _) in enumerate(sheets, start=1):
        safe_name = escape(sheet_name[:31])
        wb_xml.append(f'    <sheet name="{safe_name}" sheetId="{i}" r:id="rId{i}"/>')
        wb_rels.append(
            f'  <Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
        )
    wb_xml.append("  </sheets>")
    wb_xml.append("</workbook>")
    wb_rels.append("</Relationships>")

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "\n".join(content_types))
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", "\n".join(wb_xml))
        zf.writestr("xl/_rels/workbook.xml.rels", "\n".join(wb_rels))
        for i, (_, headers, rows) in enumerate(sheets, start=1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", _build_worksheet_xml(headers, rows))

    return output_path


class ArchiveExporter:
    """Exports verified public research data into Excel (.xlsx), CSV, and JSON."""

    def __init__(self, repo: ArchiveRepository) -> None:
        self.repo = repo

    def export_excel(
        self,
        output_path: str | Path,
        entities: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> Path:
        """
        Create an organized Excel (.xlsx) workbook.
        - If `entities` is None or empty, exports the standard 6 sheets:
          Articles, Publications, Organizations, Categories, Sources, Collection Statistics.
        - If `entities` is specified by the Export Report Wizard (e.g. ['articles', 'publications', 'organizations', 'tags']),
          exports only the chosen data entities in the workbook.
        - If `date_from` and/or `date_to` (YYYY-MM-DD) are specified, filters Articles and Publications
          by their normalized `publication_date`.
        """
        path = Path(output_path)
        articles = self.repo.list_articles()
        publications = self.repo.list_publications()

        clean_from = (date_from or "").strip()[:10]
        clean_to = (date_to or "").strip()[:10]
        if clean_from or clean_to:
            def _in_date_range(record: dict[str, Any]) -> bool:
                pub_date = str(record.get("publication_date") or "").strip()[:10]
                if not pub_date:
                    return False
                if clean_from and pub_date < clean_from:
                    return False
                if clean_to and pub_date > clean_to:
                    return False
                return True

            articles = [a for a in articles if _in_date_range(a)]
            publications = [p for p in publications if _in_date_range(p)]

        organizations = self.repo.list_organizations()
        categories = self.repo.list_categories()
        tags = self.repo.list_tags()
        sources = self.repo.list_sources()
        stats = self.repo.get_dashboard_stats()
        jobs = self.repo.list_collection_jobs()

        art_sheet = (
            "Articles",
            [
                "ID",
                "Original ID",
                "Title",
                "Subtitle",
                "Author",
                "Publication Date",
                "Categories (EN)",
                "Categories (FA)",
                "Organizations",
                "Tags",
                "Summary",
                "Source URL",
                "Retrieved Timestamp",
                "Last Verified Timestamp",
                "Status",
                "Version",
            ],
            [
                [
                    a["id"],
                    a["original_pub_id"],
                    a["title"],
                    a["subtitle"],
                    a["author"],
                    a["publication_date"],
                    a.get("categories_en", ""),
                    a.get("categories_fa", ""),
                    a.get("organizations_list", ""),
                    a.get("tags_list", ""),
                    a["summary"],
                    a["source_url"],
                    a["retrieved_at"],
                    a["last_verified_at"],
                    a["extraction_status"],
                    a["record_version"],
                ]
                for a in articles
            ],
        )

        pub_sheet = (
            "Publications",
            [
                "ID",
                "Slug",
                "Title",
                "Native Title",
                "Publication Date",
                "Categories (EN)",
                "Description",
                "Safe File Inventory Metadata",
                "Source URL",
                "Retrieved Timestamp",
                "Last Verified Timestamp",
                "Status",
                "Version",
            ],
            [
                [
                    p["id"],
                    p["original_pub_id"],
                    p["title"],
                    p["native_title"],
                    p["publication_date"],
                    p.get("categories_en", ""),
                    p["description"],
                    "; ".join(
                        f"{inv['data_type']}: {inv['reported_count_label']}"
                        for inv in p.get("inventory", [])
                    ),
                    p["source_url"],
                    p["retrieved_at"],
                    p["last_verified_at"],
                    p["extraction_status"],
                    p["record_version"],
                ]
                for p in publications
            ],
        )

        org_sheet = (
            "Organizations",
            [
                "ID",
                "Organization Name",
                "Native Name",
                "Acronym",
                "Type",
                "Linked Articles",
                "Description",
                "Source URL",
                "Retrieved Timestamp",
            ],
            [
                [
                    o["id"],
                    o["name"],
                    o["native_name"],
                    o["acronym"],
                    o["org_type"],
                    o.get("linked_articles_count", 0),
                    o["description"],
                    o["source_url"],
                    o["retrieved_at"],
                ]
                for o in organizations
            ],
        )

        tag_sheet = (
            "Tags",
            [
                "ID",
                "Normalized Tag",
                "Tag Name",
                "Linked Articles Count",
                "Linked Article Titles",
                "Source URL",
                "Retrieved Timestamp",
            ],
            [
                [
                    t.get("id", ""),
                    t.get("normalized_name") or t.get("slug") or t.get("name", ""),
                    t.get("name", ""),
                    t.get("linked_articles_count", 0),
                    t.get("linked_articles_titles") or "",
                    t.get("source_url", ""),
                    t.get("retrieved_at", ""),
                ]
                for t in tags
            ],
        )

        cat_sheet = (
            "Categories",
            [
                "ID",
                "Slug",
                "Category Name (EN)",
                "Category Name (FA)",
                "Articles Count",
                "Publications Count",
                "Description",
                "Retrieved Timestamp",
            ],
            [
                [
                    c["id"],
                    c["slug"],
                    c["name_en"],
                    c["name_fa"],
                    c.get("article_count", 0),
                    c.get("publication_count", 0),
                    c["description"],
                    c["retrieved_at"],
                ]
                for c in categories
            ],
        )

        src_sheet = (
            "Sources",
            [
                "ID",
                "Source Name",
                "Source Type",
                "Source URL",
                "Robots Policy Status",
                "Retrieved Timestamp",
                "Last Verified Timestamp",
            ],
            [
                [
                    s["id"],
                    s["name"],
                    s["source_type"],
                    s["source_url"],
                    s["robots_status"],
                    s["retrieved_at"],
                    s["last_verified_at"],
                ]
                for s in sources
            ],
        )

        stat_rows: list[list[Any]] = [
            ["Total Articles Indexed", stats["articles_count"], utc_now_iso()],
            ["Total Publication Catalogues", stats["publications_count"], utc_now_iso()],
            ["Total Public Organizations", stats["organizations_count"], utc_now_iso()],
            ["Total Public Entities", stats["entities_count"], utc_now_iso()],
            ["Total Categories", stats["categories_count"], utc_now_iso()],
            ["Total Sources", stats["sources_count"], utc_now_iso()],
            ["Collection Jobs Executed", stats["jobs_count"], utc_now_iso()],
            ["Sensitive Records Policy", "STRICTLY EXCLUDED (0 Stored)", utc_now_iso()],
        ]
        for j in jobs[:10]:
            stat_rows.append(
                [
                    f"Job #{j['id']} ({j['job_type']})",
                    f"Status: {j['status']} | Processed: {j['processed_count']} | Blocked Sensitive: {j['blocked_sensitive_count']}",
                    j["started_at"],
                ]
            )

        stat_sheet = (
            "Collection Statistics",
            ["Metric / Collection Event", "Value / Summary", "Timestamp"],
            stat_rows,
        )

        if entities:
            requested_keys = [key.strip().lower() for key in entities if key.strip()]

            def _build_ofac_sheet(scope: str) -> tuple[str, list[str], list[list[Any]]]:
                ofac_headers = [
                    "OFAC ID",
                    "List Source",
                    "Primary Name",
                    "Entity Type",
                    "Sanctions Programs",
                    "Aliases (AKA)",
                    "Countries",
                    "Addresses",
                    "Vessel / Call Sign / Flag",
                    "Remarks & Identifiers",
                    "Treasury Date Published",
                    "Official Treasury URL",
                ]
                if scope == "ofac_iran":
                    rows_db = self.repo.conn.execute(
                        """
                        SELECT ent_num, list_source, sdn_name, sdn_type, programs,
                               aliases_text, countries_text, addresses_text,
                               call_sign, vessel_type, vessel_flag, remarks,
                               date_published, source_url
                        FROM ofac_entities
                        WHERE UPPER(programs) LIKE '%IRAN%'
                           OR UPPER(programs) LIKE '%IRGC%'
                           OR UPPER(programs) LIKE '%IFSR%'
                           OR UPPER(programs) LIKE '%IFCA%'
                           OR UPPER(programs) LIKE '%FSE-IR%'
                           OR UPPER(programs) LIKE '%HRIT-IR%'
                           OR UPPER(countries_text) LIKE '%IRAN%'
                        ORDER BY sdn_name ASC;
                        """
                    ).fetchall()
                    sheet_title = "OFAC Iran Sanctions"
                else:
                    rows_db = self.repo.conn.execute(
                        """
                        SELECT ent_num, list_source, sdn_name, sdn_type, programs,
                               aliases_text, countries_text, addresses_text,
                               call_sign, vessel_type, vessel_flag, remarks,
                               date_published, source_url
                        FROM ofac_entities
                        ORDER BY list_source ASC, sdn_name ASC;
                        """
                    ).fetchall()
                    sheet_title = "OFAC Full Sanctions"

                formatted_rows: list[list[Any]] = []
                for r in rows_db:
                    vessel_meta = " | ".join(
                        p
                        for p in (r["vessel_type"], r["call_sign"], r["vessel_flag"])
                        if p
                    )
                    formatted_rows.append(
                        [
                            r["ent_num"],
                            r["list_source"],
                            r["sdn_name"],
                            r["sdn_type"],
                            str(r["programs"] or "").replace("] [", "; "),
                            r["aliases_text"],
                            r["countries_text"],
                            r["addresses_text"],
                            vessel_meta,
                            r["remarks"],
                            r["date_published"],
                            r["source_url"],
                        ]
                    )
                return (sheet_title, ofac_headers, formatted_rows)

            def _build_opensanctions_sheet(scope: str) -> tuple[str, list[str], list[list[Any]]]:
                os_headers = [
                    "OpenSanctions ID",
                    "Schema / Type",
                    "Primary Name",
                    "Aliases",
                    "Countries",
                    "Birth Date",
                    "Identifiers (IMO / Passport / Reg)",
                    "Addresses",
                    "Sanctions Programs",
                    "Source Lists (UN/EU/UK/US/etc.)",
                    "Sanctions Details",
                    "Last Changed",
                    "OpenSanctions URL",
                ]
                if scope == "opensanctions_iran":
                    rows_db = self.repo.conn.execute(
                        """
                        SELECT os_id, schema_type, name, aliases, countries, birth_date,
                               identifiers, addresses, program_ids, datasets, sanctions,
                               last_change, source_url
                        FROM opensanctions_entities
                        WHERE (';' || LOWER(countries) || ';') LIKE '%;ir;%'
                           OR UPPER(program_ids) LIKE '%IRAN%'
                           OR UPPER(sanctions) LIKE '%IRAN%'
                           OR UPPER(sanctions) LIKE '%IRGC%'
                           OR UPPER(datasets) LIKE '%IRAN%'
                        ORDER BY name ASC;
                        """
                    ).fetchall()
                    sheet_title = "OpenSanctions Iran"
                else:
                    rows_db = self.repo.conn.execute(
                        """
                        SELECT os_id, schema_type, name, aliases, countries, birth_date,
                               identifiers, addresses, program_ids, datasets, sanctions,
                               last_change, source_url
                        FROM opensanctions_entities
                        ORDER BY name ASC
                        LIMIT 100000;
                        """
                    ).fetchall()
                    sheet_title = "OpenSanctions Global"

                formatted_rows = [
                    [
                        r["os_id"],
                        r["schema_type"],
                        r["name"],
                        r["aliases"],
                        r["countries"],
                        r["birth_date"],
                        r["identifiers"],
                        r["addresses"],
                        r["program_ids"],
                        r["datasets"],
                        r["sanctions"],
                        r["last_change"],
                        r["source_url"],
                    ]
                    for r in rows_db
                ]
                return (sheet_title, os_headers, formatted_rows)

            entity_map: dict[str, tuple[str, list[str], list[list[Any]]]] = {
                "articles": art_sheet,
                "publications": pub_sheet,
                "organizations": org_sheet,
                "tags": tag_sheet,
                "categories": cat_sheet,
                "sources": src_sheet,
                "statistics": stat_sheet,
            }
            if "ofac_iran" in requested_keys:
                entity_map["ofac_iran"] = _build_ofac_sheet("ofac_iran")
            if "ofac_all" in requested_keys:
                entity_map["ofac_all"] = _build_ofac_sheet("ofac_all")
            if "opensanctions_iran" in requested_keys:
                entity_map["opensanctions_iran"] = _build_opensanctions_sheet("opensanctions_iran")
            if "opensanctions_all" in requested_keys:
                entity_map["opensanctions_all"] = _build_opensanctions_sheet("opensanctions_all")

            selected_sheets = [
                entity_map[key] for key in requested_keys if key in entity_map
            ]
            if selected_sheets:
                return write_multi_sheet_xlsx(path, selected_sheets)

        return write_multi_sheet_xlsx(
            path,
            [art_sheet, pub_sheet, org_sheet, cat_sheet, src_sheet, stat_sheet],
        )

    def export_csv(self, output_path: str | Path) -> Path:
        """Export unified articles and publication catalogues to UTF-8-SIG CSV (Excel compatible)."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        articles = self.repo.list_articles()
        publications = self.repo.list_publications()

        headers = [
            "Record Type",
            "ID",
            "Original Identifier",
            "Title",
            "Publication Date",
            "Categories (EN)",
            "Categories (FA)",
            "Summary / Description",
            "Source URL",
            "Retrieved Timestamp",
            "Last Verified Timestamp",
            "Extraction Status",
            "Version",
        ]

        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for a in articles:
                writer.writerow(
                    [
                        "ARTICLE",
                        a["id"],
                        a["original_pub_id"],
                        a["title"],
                        a["publication_date"],
                        a.get("categories_en", ""),
                        a.get("categories_fa", ""),
                        a["summary"],
                        a["source_url"],
                        a["retrieved_at"],
                        a["last_verified_at"],
                        a["extraction_status"],
                        a["record_version"],
                    ]
                )
            for p in publications:
                writer.writerow(
                    [
                        "PUBLICATION_CATALOGUE",
                        p["id"],
                        p["original_pub_id"],
                        p["title"],
                        p["publication_date"],
                        p.get("categories_en", ""),
                        p.get("categories_fa", ""),
                        p["description"],
                        p["source_url"],
                        p["retrieved_at"],
                        p["last_verified_at"],
                        p["extraction_status"],
                        p["record_version"],
                    ]
                )

        return path

    def export_json(self, output_path: str | Path) -> Path:
        """Export structured JSON archive report with provenance and safety attestation."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "application": "WikIran Archive",
            "version": "1.0.0",
            "exported_at": utc_now_iso(),
            "safety_attestation": "Metadata and public editorial analysis only. Sensitive underlying leaked files and personal identifiers are strictly excluded.",
            "statistics": self.repo.get_dashboard_stats(),
            "articles": self.repo.list_articles(),
            "publications": self.repo.list_publications(),
            "organizations": self.repo.list_organizations(),
            "categories": self.repo.list_categories(),
            "sources": self.repo.list_sources(),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
