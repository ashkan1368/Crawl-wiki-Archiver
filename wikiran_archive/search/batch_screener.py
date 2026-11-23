"""
Batch Watchlist Screener for Trade & Sanctions Compliance.

Allows compliance teams to upload an Excel (.xlsx), CSV (.csv), or plain text list of
counterparties (companies, individuals, vessels, banks, exchange houses), screen every
entry across:
  1. U.S. Treasury OFAC Sanctions (offline SQLite FTS5)
  2. OpenSanctions Global Sanctions (offline SQLite FTS5)
  3. WikIran Offline Archive (Front Companies, Vessels, Articles, Cached Leak Docs)
  4. Optional Live WikIran 3.1M+ Leak Search (with phrase/token precision filtering and
     automatic permanent offline caching!)

Works 100% reliably with OR without `openpyxl` installed via built-in OpenXML (.xlsx)
reading and writing fallbacks.
"""

from __future__ import annotations

import base64
import csv
import io
import re
import time
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..collector.wikiran_live import search_wikiran_live
from ..database.repository import ArchiveRepository
from ..export.exporters import write_multi_sheet_xlsx
from .fts_search import ArchiveSearchEngine, SearchFilters

TEMPLATE_HEADERS = [
    "Name",
    "Entity_Type",
    "Alias_or_Alt_Name",
    "Country",
    "Reference_ID",
    "Notes",
]

TEMPLATE_SAMPLE_ROWS = [
    [
        "Bank Sepah",
        "Bank",
        "بانک سپه",
        "Iran",
        "TRD-2026-001",
        "Sample banking counterparty check",
    ],
    [
        "Sahara Thunder",
        "Company",
        "صحرا تاندر",
        "Iran",
        "TRD-2026-002",
        "Sample maritime/front company check",
    ],
    [
        "Sepehr Energy Jahan",
        "Company",
        "سپهر انرژی جهان",
        "Iran",
        "TRD-2026-003",
        "Sample oil & petrochemical screening",
    ],
    [
        "Nordic Clean Logistics GmbH",
        "Company",
        "",
        "Germany",
        "TRD-2026-004",
        "Sample clean/non-sanctioned counterparty",
    ],
]

TEMPLATE_GUIDE_ROWS = [
    [
        "Name",
        "REQUIRED",
        "Put ONE company, person, bank, exchange house, or vessel name per row. English or Persian.",
        "در هر ردیف فقط نام یک شرکت، شخص، بانک، صرافی یا کشتی (انگلیسی یا فارسی) وارد کنید.",
    ],
    [
        "Entity_Type",
        "Optional",
        "Use Company, Person, Vessel, Bank, or Exchange — or leave blank.",
        "نوع نهاد (Company / Person / Vessel / Bank / Exchange) — اختیاری.",
    ],
    [
        "Alias_or_Alt_Name",
        "Optional",
        "Alternative spelling, Persian/English equivalent, or IMO/Registration number (also screened!). Separate multiple aliases with ';'.",
        "نام جایگزین، معادل فارسی/انگلیسی یا شماره IMO کشتی (این ستون هم بررسی می‌شود). چند مورد را با ; جدا کنید.",
    ],
    [
        "Country",
        "Optional",
        "Counterparty country or vessel flag for your internal report.",
        "کشور طرف معامله یا پرچم کشتی برای ثبت در گزارش نهایی.",
    ],
    [
        "Reference_ID",
        "Optional",
        "Your internal invoice, client, or contract code so you can match results back to your records.",
        "کد داخلی مشتری، فاکتور یا قرارداد شما برای تطبیق آسان در گزارش ریسک.",
    ],
    [
        "Notes",
        "Optional",
        "Any internal trade note (carried directly into the output Excel report).",
        "یادداشت داخلی معامله (مستقیماً در گزارش خروجی اکسل نمایش داده می‌شود).",
    ],
    [
        "IMPORTANT TIP",
        "—",
        "Delete the 4 sample rows in Watchlist_Input and paste your real names starting at Row 2. Keep Row 1 headers intact.",
        "۴ ردیف نمونه در شیت Watchlist_Input را پاک کنید و نام‌های واقعی خود را از ردیف ۲ به بعد وارد نمایید.",
    ],
]

COLUMN_ALIASES: dict[str, set[str]] = {
    "name": {
        "name",
        "entity",
        "entity_name",
        "company",
        "company_name",
        "counterparty",
        "full_name",
        "fullname",
        "target",
        "vessel",
        "vessel_name",
        "client",
        "client_name",
        "subject",
        "party",
        "نام",
        "نام شرکت",
        "نام کامل",
        "طرف معامله",
    },
    "entity_type": {
        "entity_type",
        "type",
        "category",
        "kind",
        "role",
        "نوع",
        "نوع نهاد",
    },
    "alias": {
        "alias_or_alt_name",
        "alias",
        "aliases",
        "alt_name",
        "alternative_name",
        "persian_name",
        "farsi_name",
        "imo",
        "identifier",
        "reg_no",
        "نام جایگزین",
        "نام فارسی",
        "شناسه",
    },
    "country": {
        "country",
        "jurisdiction",
        "nationality",
        "flag",
        "location",
        "کشور",
        "ملیت",
    },
    "reference_id": {
        "reference_id",
        "ref_id",
        "ref",
        "reference",
        "id",
        "code",
        "invoice",
        "invoice_no",
        "client_id",
        "contract_id",
        "کد",
        "شماره پیگیری",
        "شناسه داخلی",
    },
    "notes": {
        "notes",
        "note",
        "comment",
        "comments",
        "remarks",
        "description",
        "توضیحات",
        "یادداشت",
    },
}

GENERIC_LEGAL_STOPWORDS = {
    "co",
    "company",
    "companies",
    "corp",
    "corporation",
    "inc",
    "incorporated",
    "ltd",
    "limited",
    "llc",
    "llp",
    "lp",
    "plc",
    "gmbh",
    "ag",
    "sa",
    "sarl",
    "bv",
    "nv",
    "fze",
    "fzc",
    "fzco",
    "dmcc",
    "pjsc",
    "jsc",
    "trading",
    "trade",
    "logistics",
    "shipping",
    "maritime",
    "transport",
    "group",
    "holding",
    "holdings",
    "international",
    "intl",
    "global",
    "general",
    "services",
    "service",
    "industrial",
    "industry",
    "industries",
    "commercial",
    "commerce",
    "energy",
    "oil",
    "gas",
    "petrochemical",
    "bank",
    "exchange",
    "house",
    "the",
    "and",
    "of",
    "for",
    "شرکت",
    "تجاری",
    "بازرگانی",
    "بین",
    "المللی",
    "گروه",
    "صنعتی",
}


def _normalize_header_key(raw: str) -> str:
    cleaned = str(raw or "").strip().lower()
    cleaned = re.sub(r"[\s\-/]+", "_", cleaned)
    cleaned = re.sub(r"[^a-z0-9_\u0600-\u06ff]+", "", cleaned)
    return cleaned


def _map_header_to_field(raw: str) -> str | None:
    norm = _normalize_header_key(raw)
    if not norm:
        return None
    for field, aliases in COLUMN_ALIASES.items():
        if norm in aliases:
            return field
    return None


def _col_ref_to_index(cell_ref: str) -> int:
    """Convert Excel cell ref like 'C2' or 'AA5' to 0-based column index."""
    letters = "".join(ch for ch in cell_ref if ch.isalpha()).upper()
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return max(0, idx - 1)


def _read_xlsx_bytes_pure_python(raw_bytes: bytes) -> list[list[str]]:
    """
    Pure-Python OpenXML (.xlsx) reader using zipfile + ElementTree.
    Works seamlessly even when openpyxl is not installed.
    """
    rows_out: list[list[str]] = []
    with zipfile.ZipFile(io.BytesIO(raw_bytes), "r") as zf:
        names = set(zf.namelist())
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in names:
            ss_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in ss_root.iter():
                if si.tag.endswith("}si") or si.tag == "si":
                    parts = [
                        (t.text or "")
                        for t in si.iter()
                        if t.tag.endswith("}t") or t.tag == "t"
                    ]
                    shared_strings.append("".join(parts))

        # Prefer Watchlist_Input sheet if present, otherwise xl/worksheets/sheet1.xml
        target_sheet = "xl/worksheets/sheet1.xml"
        if "xl/workbook.xml" in names and "xl/_rels/workbook.xml.rels" in names:
            try:
                wb_root = ET.fromstring(zf.read("xl/workbook.xml"))
                rels_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
                rel_map: dict[str, str] = {}
                for rel in rels_root.iter():
                    if rel.tag.endswith("}Relationship") or rel.tag == "Relationship":
                        rid = rel.attrib.get("Id", "")
                        tgt = rel.attrib.get("Target", "").lstrip("/")
                        if rid and tgt:
                            rel_map[rid] = tgt if tgt.startswith("xl/") else f"xl/{tgt}"
                sheet_targets: list[tuple[str, str]] = []
                for sh in wb_root.iter():
                    if sh.tag.endswith("}sheet") or sh.tag == "sheet":
                        s_name = sh.attrib.get("name", "")
                        rid = ""
                        for k, v in sh.attrib.items():
                            if k.endswith("}id") or k == "r:id":
                                rid = v
                                break
                        if rid in rel_map:
                            sheet_targets.append((s_name, rel_map[rid]))
                for s_name, s_path in sheet_targets:
                    if s_name.lower() == "watchlist_input" and s_path in names:
                        target_sheet = s_path
                        break
                else:
                    if sheet_targets and sheet_targets[0][1] in names:
                        target_sheet = sheet_targets[0][1]
            except Exception:
                pass

        if target_sheet not in names:
            candidates = sorted(n for n in names if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
            if not candidates:
                return []
            target_sheet = candidates[0]

        sh_root = ET.fromstring(zf.read(target_sheet))
        for row_el in sh_root.iter():
            if not (row_el.tag.endswith("}row") or row_el.tag == "row"):
                continue
            row_cells: dict[int, str] = {}
            max_col = -1
            for c_el in row_el:
                if not (c_el.tag.endswith("}c") or c_el.tag == "c"):
                    continue
                ref = c_el.attrib.get("r", "")
                c_idx = _col_ref_to_index(ref) if ref else (max_col + 1)
                c_type = c_el.attrib.get("t", "")
                val_text = ""
                if c_type == "inlineStr":
                    parts = [
                        (t.text or "")
                        for t in c_el.iter()
                        if t.tag.endswith("}t") or t.tag == "t"
                    ]
                    val_text = "".join(parts)
                else:
                    v_el = next(
                        (ch for ch in c_el if ch.tag.endswith("}v") or ch.tag == "v"),
                        None,
                    )
                    if v_el is not None and v_el.text is not None:
                        if c_type == "s":
                            try:
                                val_text = shared_strings[int(v_el.text)]
                            except (ValueError, IndexError):
                                val_text = v_el.text
                        else:
                            val_text = v_el.text
                row_cells[c_idx] = val_text.strip()
                if c_idx > max_col:
                    max_col = c_idx
            if max_col >= 0:
                vals = [row_cells.get(i, "") for i in range(max_col + 1)]
                if any(vals):
                    rows_out.append(vals)
    return rows_out


def generate_watchlist_template_csv(exports_dir: Path) -> Path:
    """Create the exact UTF-8 BOM CSV watchlist template for Excel/Persian compatibility."""
    exports_dir.mkdir(parents=True, exist_ok=True)
    out_path = exports_dir / "WikIran_Batch_Watchlist_Template.csv"
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(TEMPLATE_HEADERS)
        for row in TEMPLATE_SAMPLE_ROWS:
            writer.writerow(row)
    return out_path


def generate_watchlist_template_xlsx(exports_dir: Path) -> Path:
    """Create a real 2-sheet Excel (.xlsx) template with input sheet + instructions."""
    exports_dir.mkdir(parents=True, exist_ok=True)
    out_path = exports_dir / "WikIran_Batch_Watchlist_Template.xlsx"
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    except ImportError:
        return write_multi_sheet_xlsx(
            out_path,
            [
                ("Watchlist_Input", TEMPLATE_HEADERS, TEMPLATE_SAMPLE_ROWS),
                (
                    "Instructions_Guide",
                    ["Column Header", "Required?", "How to Fill Correctly (English)", "راهنمای تکمیل (فارسی)"],
                    TEMPLATE_GUIDE_ROWS,
                ),
            ],
        )

    wb = Workbook()
    ws = wb.active
    ws.title = "Watchlist_Input"

    navy_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    sub_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    body_font = Font(name="Calibri", size=10, color="0F172A")
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    ws.append(TEMPLATE_HEADERS)
    for col_idx in range(1, len(TEMPLATE_HEADERS) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = navy_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="left", vertical="center")
        cell.border = thin_border
    ws.row_dimensions[1].height = 24

    for r_idx, row in enumerate(TEMPLATE_SAMPLE_ROWS, start=2):
        ws.append(row)
        for col_idx in range(1, len(TEMPLATE_HEADERS) + 1):
            cell = ws.cell(row=r_idx, column=col_idx)
            cell.font = body_font
            cell.border = thin_border
            if r_idx % 2 == 1:
                cell.fill = sub_fill
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    for idx, width in enumerate([34, 16, 28, 16, 18, 36], start=1):
        ws.column_dimensions[chr(64 + idx)].width = width
    ws.freeze_panes = "A2"

    guide = wb.create_sheet("Instructions_Guide")
    guide_all = [
        ["Column Header", "Required?", "How to Fill Correctly (English)", "راهنمای تکمیل (فارسی)"],
        *TEMPLATE_GUIDE_ROWS,
    ]
    for r_i, g_row in enumerate(guide_all, start=1):
        guide.append(g_row)
        for c_i in range(1, 5):
            cell = guide.cell(row=r_i, column=c_i)
            cell.border = thin_border
            if r_i == 1:
                cell.fill = navy_fill
                cell.font = header_font
            else:
                cell.font = Font(name="Calibri", size=10, bold=(c_i == 1))
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    for col_l, w in (("A", 22), ("B", 14), ("C", 56), ("D", 56)):
        guide.column_dimensions[col_l].width = w
    guide.freeze_panes = "A2"

    wb.save(out_path)
    return out_path


def parse_watchlist_input(
    *,
    file_b64: str | None = None,
    filename: str = "",
    raw_text: str | None = None,
    max_rows: int = 5000,
) -> dict[str, Any]:
    """
    Parse an uploaded .xlsx, .csv, or plain-text pasted watchlist into normalized entries.
    Works with or without openpyxl installed.
    """
    rows_matrix: list[list[str]] = []
    detected_format = "text"
    fname_low = (filename or "").strip().lower()

    if file_b64:
        raw_bytes = base64.b64decode(file_b64)
        if fname_low.endswith(".xlsx") or fname_low.endswith(".xlsm") or raw_bytes[:2] == b"PK":
            detected_format = "xlsx"
            try:
                from openpyxl import load_workbook

                wb = load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
                sheet = wb["Watchlist_Input"] if "Watchlist_Input" in wb.sheetnames else wb.active
                for r in sheet.iter_rows(values_only=True):
                    vals = [str(v).strip() if v is not None else "" for v in r]
                    if any(vals):
                        rows_matrix.append(vals)
                wb.close()
            except ImportError:
                rows_matrix = _read_xlsx_bytes_pure_python(raw_bytes)
        else:
            detected_format = "csv"
            raw_text = raw_bytes.decode("utf-8-sig", errors="replace")

    if raw_text is not None and not rows_matrix:
        text_clean = raw_text.lstrip("\ufeff").strip()
        if not text_clean:
            return {
                "entries": [],
                "detected_format": detected_format,
                "detected_columns": [],
                "skipped_rows": 0,
            }
        lines = [ln for ln in text_clean.splitlines() if ln.strip()]
        first_line = lines[0]
        delimiter: str | None = None
        if "\t" in first_line:
            delimiter = "\t"
        elif "," in first_line:
            delimiter = ","
        elif ";" in first_line and len(first_line.split(";")) >= 2:
            delimiter = ";"

        if delimiter:
            detected_format = "csv"
            reader = csv.reader(io.StringIO(text_clean), delimiter=delimiter)
            for r in reader:
                vals = [str(v).strip() for v in r]
                if any(vals):
                    rows_matrix.append(vals)
        else:
            detected_format = "lines"
            for ln in lines:
                rows_matrix.append([ln.strip()])

    if not rows_matrix:
        return {
            "entries": [],
            "detected_format": detected_format,
            "detected_columns": [],
            "skipped_rows": 0,
        }

    header_row = rows_matrix[0]
    mapped_cols: dict[int, str] = {}
    for idx, col_label in enumerate(header_row):
        mapped = _map_header_to_field(col_label)
        if mapped and mapped not in mapped_cols.values():
            mapped_cols[idx] = mapped

    has_header = "name" in mapped_cols.values() or (
        len(mapped_cols) >= 2 and detected_format in ("xlsx", "csv")
    )
    data_rows = rows_matrix[1:] if has_header else rows_matrix
    detected_columns = header_row if has_header else ["Name"]

    if not has_header:
        mapped_cols = {0: "name"}
        max_len = max((len(r) for r in data_rows), default=1)
        if max_len >= 2:
            mapped_cols[1] = "entity_type"
        if max_len >= 3:
            mapped_cols[2] = "alias"
        if max_len >= 4:
            mapped_cols[3] = "country"
        if max_len >= 5:
            mapped_cols[4] = "reference_id"
        if max_len >= 6:
            mapped_cols[5] = "notes"

    entries: list[dict[str, str]] = []
    skipped = 0
    for row_idx, r in enumerate(data_rows, start=1):
        if len(entries) >= max_rows:
            break
        rec = {
            "row_number": str(row_idx),
            "name": "",
            "entity_type": "",
            "alias": "",
            "country": "",
            "reference_id": "",
            "notes": "",
        }
        for c_idx, field in mapped_cols.items():
            if c_idx < len(r):
                rec[field] = str(r[c_idx] or "").strip()
        if not rec["name"] and rec["alias"]:
            rec["name"] = rec["alias"]
            rec["alias"] = ""
        if not rec["name"] or len(rec["name"]) < 2:
            skipped += 1
            continue
        entries.append(rec)

    return {
        "entries": entries,
        "detected_format": detected_format,
        "detected_columns": detected_columns,
        "skipped_rows": skipped,
    }


def _distinctive_tokens(name: str) -> list[str]:
    """Extract non-generic distinctive tokens from an entity name for precision matching."""
    raw_tokens = re.findall(r"[a-zA-Z0-9\u0600-\u06ff]{2,}", (name or "").lower())
    distinct = [t for t in raw_tokens if t not in GENERIC_LEGAL_STOPWORDS]
    return distinct if distinct else raw_tokens


def _live_hit_matches_entity(query_name: str, title: str, snippet: str) -> bool:
    """
    Prevent false positives from WikIran's broad OR-matching on generic words like 'Logistics' or 'GmbH'.
    A live hit counts as relevant if:
      - The full normalized query appears as a substring, OR
      - All distinctive tokens (up to first 2 distinctive tokens) appear in title+snippet.
    """
    hay = f"{title} {snippet}".lower()
    norm_q = re.sub(r"\s+", " ", (query_name or "").strip().lower())
    if norm_q and norm_q in hay:
        return True
    tokens = _distinctive_tokens(query_name)
    if not tokens:
        return False
    if len(tokens) == 1:
        return tokens[0] in hay
    # Require at least the first two distinctive tokens (e.g., "sahara" & "thunder", or "nordic" & "clean")
    required_hits = min(2, len(tokens))
    matched_count = sum(1 for tok in tokens if tok in hay)
    return matched_count >= required_hits


def _export_batch_report_csv(
    exports_dir: Path, results: list[dict[str, Any]], timestamp_tag: str
) -> Path:
    exports_dir.mkdir(parents=True, exist_ok=True)
    out_path = exports_dir / f"WikIran_Watchlist_Risk_Report_{timestamp_tag}.csv"
    headers = [
        "Row",
        "Reference_ID",
        "Input_Name",
        "Alias_or_Alt_Name",
        "Entity_Type",
        "Country",
        "Risk_Level",
        "Total_Hits",
        "OFAC_Hits",
        "OpenSanctions_Hits",
        "WikIran_Offline_Hits",
        "WikIran_Live_3M_Total",
        "Top_Match_Title",
        "Top_Match_Source",
        "Sanctions_Programs_or_Leak",
        "Top_Match_URL",
        "Notes",
    ]
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for item in results:
            writer.writerow(
                [
                    item["row_number"],
                    item["reference_id"],
                    item["name"],
                    item["alias"],
                    item["entity_type"],
                    item["country"],
                    item["risk_label"],
                    item["total_hits"],
                    item["ofac_hits"],
                    item["opensanctions_hits"],
                    item["wikiran_offline_hits"],
                    item["wikiran_live_total_label"],
                    item["top_match_title"],
                    item["top_match_source"],
                    item["sanctions_or_leak_tags"],
                    item["top_match_url"],
                    item["notes"],
                ]
            )
    return out_path


def _export_batch_report_xlsx(
    exports_dir: Path,
    results: list[dict[str, Any]],
    summary: dict[str, Any],
    timestamp_tag: str,
) -> Path:
    exports_dir.mkdir(parents=True, exist_ok=True)
    out_path = exports_dir / f"WikIran_Watchlist_Risk_Report_{timestamp_tag}.xlsx"

    summary_pairs = [
        ["Screening Timestamp (UTC)", summary["screened_at"]],
        ["Total Counterparties Screened", summary["total_screened"]],
        ["HIGH RISK (OFAC / OpenSanctions Match)", summary["high_risk_count"]],
        ["ELEVATED RISK (WikIran Archive / Leak Match)", summary["elevated_risk_count"]],
        ["CLEAR (No Match Found)", summary["clear_count"]],
        [
            "Live WikIran 3.1M Search Enabled",
            "Yes" if summary["live_wikiran_enabled"] else "No (Offline Only)",
        ],
        ["New WikIran Documents Auto-Saved Offline", summary["newly_cached_wikiran_docs"]],
        [
            "Datasets Checked",
            "OFAC Sanctions + OpenSanctions + WikIran Front Companies/Vessels/Articles + WikIran Leak Archive",
        ],
    ]
    res_headers = [
        "Row",
        "Reference_ID",
        "Input_Name",
        "Alias_or_Alt_Name",
        "Entity_Type",
        "Country",
        "Risk_Level",
        "Total_Hits",
        "OFAC_Hits",
        "OpenSanctions_Hits",
        "WikIran_Offline_Hits",
        "WikIran_Live_3M_Total",
        "Top_Match_Title",
        "Top_Match_Source",
        "Sanctions_Programs_or_Leak",
        "Top_Match_URL",
        "Notes",
    ]
    res_rows = [
        [
            item["row_number"],
            item["reference_id"],
            item["name"],
            item["alias"],
            item["entity_type"],
            item["country"],
            item["risk_label"],
            item["total_hits"],
            item["ofac_hits"],
            item["opensanctions_hits"],
            item["wikiran_offline_hits"],
            item["wikiran_live_total_label"],
            item["top_match_title"],
            item["top_match_source"],
            item["sanctions_or_leak_tags"],
            item["top_match_url"],
            item["notes"],
        ]
        for item in results
    ]
    ev_headers = [
        "Input_Name",
        "Reference_ID",
        "Risk_Level",
        "Source_Dataset",
        "Matched_Title",
        "Programs_or_Leak",
        "Date",
        "Snippet",
        "Source_URL",
    ]
    ev_rows = [
        [
            item["name"],
            item["reference_id"],
            item["risk_label"],
            hit.get("source_bucket", ""),
            hit.get("title", ""),
            hit.get("programs_or_leak", ""),
            hit.get("publication_date", ""),
            hit.get("snippet", ""),
            hit.get("source_url", ""),
        ]
        for item in results
        for hit in item.get("evidence_hits", [])
    ]

    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    except ImportError:
        return write_multi_sheet_xlsx(
            out_path,
            [
                ("Executive_Summary", ["Metric", "Value"], summary_pairs),
                ("Screening_Results", res_headers, res_rows),
                ("Detailed_Evidence", ev_headers, ev_rows),
            ],
        )

    wb = Workbook()
    navy_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    body_font = Font(name="Calibri", size=10, color="0F172A")
    high_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    high_font = Font(name="Calibri", size=10, bold=True, color="991B1B")
    elev_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    elev_font = Font(name="Calibri", size=10, bold=True, color="92400E")
    clear_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    clear_font = Font(name="Calibri", size=10, bold=True, color="166534")
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    ws_sum = wb.active
    ws_sum.title = "Executive_Summary"
    ws_sum.append(["Metric", "Value"])
    for c_i in (1, 2):
        cell = ws_sum.cell(row=1, column=c_i)
        cell.fill = navy_fill
        cell.font = header_font
        cell.border = thin_border
    for r_idx, row in enumerate(summary_pairs, start=2):
        ws_sum.append(row)
        for c_i in (1, 2):
            cell = ws_sum.cell(row=r_idx, column=c_i)
            cell.border = thin_border
            cell.font = Font(name="Calibri", size=10, bold=(c_i == 1))
    ws_sum.column_dimensions["A"].width = 42
    ws_sum.column_dimensions["B"].width = 58

    ws_res = wb.create_sheet("Screening_Results")
    ws_res.append(res_headers)
    for c_i in range(1, len(res_headers) + 1):
        cell = ws_res.cell(row=1, column=c_i)
        cell.fill = navy_fill
        cell.font = header_font
        cell.border = thin_border
    ws_res.freeze_panes = "A2"

    for r_idx, (item, r_vals) in enumerate(zip(results, res_rows), start=2):
        ws_res.append(r_vals)
        for c_i in range(1, len(res_headers) + 1):
            cell = ws_res.cell(row=r_idx, column=c_i)
            cell.border = thin_border
            cell.font = body_font
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            if c_i == 7:
                if item["risk_level"] == "HIGH_RISK":
                    cell.fill = high_fill
                    cell.font = high_font
                elif item["risk_level"] == "ELEVATED_RISK":
                    cell.fill = elev_fill
                    cell.font = elev_font
                else:
                    cell.fill = clear_fill
                    cell.font = clear_font

    for idx, w in enumerate([7, 15, 30, 22, 13, 13, 24, 11, 11, 16, 17, 18, 34, 22, 28, 38, 24], start=1):
        ws_res.column_dimensions[chr(64 + idx)].width = w

    ws_ev = wb.create_sheet("Detailed_Evidence")
    ws_ev.append(ev_headers)
    for c_i in range(1, len(ev_headers) + 1):
        cell = ws_ev.cell(row=1, column=c_i)
        cell.fill = navy_fill
        cell.font = header_font
        cell.border = thin_border
    ws_ev.freeze_panes = "A2"
    for r_vals in ev_rows:
        ws_ev.append(r_vals)
    for col_l, w in (("A", 28), ("B", 15), ("C", 22), ("D", 22), ("E", 34), ("F", 28), ("G", 13), ("H", 48), ("I", 40)):
        ws_ev.column_dimensions[col_l].width = w

    wb.save(out_path)
    return out_path


def run_batch_watchlist_screening(
    repo: ArchiveRepository,
    exports_dir: Path,
    *,
    file_b64: str | None = None,
    filename: str = "",
    raw_text: str | None = None,
    include_live_wikiran: bool = True,
    max_live_queries: int = 80,
) -> dict[str, Any]:
    """
    Screen every row of an uploaded Excel/CSV/pasted watchlist across OFAC, OpenSanctions,
    WikIran offline archive, and optionally live WikIran 3.1M+ leak search (auto-caching verified hits!).
    """
    parsed = parse_watchlist_input(
        file_b64=file_b64,
        filename=filename,
        raw_text=raw_text,
    )
    entries = parsed["entries"]
    if not entries:
        return {
            "ok": False,
            "error": "No valid entity names found in the uploaded file or text. Please put at least one name in the 'Name' column.",
        }

    search_engine = ArchiveSearchEngine(repo.conn)
    screened_results: list[dict[str, Any]] = []
    high_risk_count = 0
    elevated_risk_count = 0
    clear_count = 0
    newly_cached_wikiran_docs = 0
    live_queries_used = 0
    live_capped = False

    for entry in entries:
        primary_name = entry["name"]
        alias_raw = entry["alias"]
        terms: list[str] = [primary_name]
        if alias_raw:
            for part in re.split(r"[;|]+", alias_raw):
                clean_part = part.strip()
                if clean_part and len(clean_part) >= 2 and clean_part.lower() != primary_name.lower():
                    terms.append(clean_part)

        ofac_hits: list[dict[str, Any]] = []
        os_hits: list[dict[str, Any]] = []
        wikiran_offline_hits: list[dict[str, Any]] = []
        wikiran_live_hits: list[dict[str, Any]] = []
        wikiran_live_total_int = 0
        wikiran_live_total_label = "—"
        seen_keys: set[str] = set()

        for term in terms:
            local_matches = search_engine.search(SearchFilters(query=term))
            for m in local_matches[:30]:
                rec_type = str(m.get("record_type") or "")
                dedup_k = f"{rec_type}:{m.get('source_url') or m.get('title')}"
                if dedup_k in seen_keys:
                    continue
                seen_keys.add(dedup_k)

                if rec_type == "OFAC_SANCTION":
                    ofac_hits.append(
                        {
                            "source_bucket": "OFAC Sanctions",
                            "record_type": rec_type,
                            "title": str(m.get("title") or ""),
                            "programs_or_leak": str(m.get("ofac_programs") or m.get("ofac_list_source") or "OFAC"),
                            "publication_date": str(m.get("publication_date") or ""),
                            "snippet": str(m.get("short_description") or "")[:240],
                            "source_url": str(m.get("source_url") or ""),
                        }
                    )
                elif rec_type == "OPENSANCTIONS":
                    os_hits.append(
                        {
                            "source_bucket": "OpenSanctions",
                            "record_type": rec_type,
                            "title": str(m.get("title") or ""),
                            "programs_or_leak": str(m.get("os_datasets") or m.get("category_en") or "OpenSanctions"),
                            "publication_date": str(m.get("publication_date") or ""),
                            "snippet": str(m.get("short_description") or "")[:240],
                            "source_url": str(m.get("source_url") or ""),
                        }
                    )
                else:
                    wikiran_offline_hits.append(
                        {
                            "source_bucket": str(m.get("category_en") or "WikIran Offline"),
                            "record_type": rec_type,
                            "title": str(m.get("title") or ""),
                            "programs_or_leak": str(m.get("source_name") or m.get("tags") or "WikIran Archive"),
                            "publication_date": str(m.get("publication_date") or ""),
                            "snippet": str(m.get("short_description") or "")[:240],
                            "source_url": str(m.get("source_url") or ""),
                        }
                    )

        # Optional Live WikIran 3.1M+ search with exact-phrase & distinctive-token precision check
        if include_live_wikiran:
            if live_queries_used < max_live_queries:
                live_queries_used += 1
                quoted_q = f'"{primary_name}"' if " " in primary_name else primary_name
                live_resp = search_wikiran_live(
                    repo,
                    quoted_q,
                    max_pages=1,
                    tab_type="all",
                    auto_cache=False,
                )
                if live_resp.get("online"):
                    verified_cards: list[dict[str, Any]] = []
                    for lr in live_resp.get("results", []):
                        lr_title = str(lr.get("title") or "")
                        lr_snip = str(lr.get("short_description") or "")
                        if not _live_hit_matches_entity(primary_name, lr_title, lr_snip):
                            continue
                        dedup_k = f"LIVE:{lr.get('source_url') or lr_title}"
                        if dedup_k in seen_keys:
                            continue
                        seen_keys.add(dedup_k)
                        verified_cards.append(lr)
                        if len(wikiran_live_hits) < 10:
                            wikiran_live_hits.append(
                                {
                                    "source_bucket": "WikIran Live 3.1M Archive",
                                    "record_type": "WIKIRAN_LIVE",
                                    "title": lr_title,
                                    "programs_or_leak": str(lr.get("category_en") or lr.get("source_name") or "WikIran Live"),
                                    "publication_date": str(lr.get("publication_date") or ""),
                                    "snippet": lr_snip[:240],
                                    "source_url": str(lr.get("source_url") or ""),
                                }
                            )
                    if verified_cards:
                        wikiran_live_total_int = int(live_resp.get("total_int") or len(verified_cards))
                        wikiran_live_total_label = str(live_resp.get("total_label") or f"{len(verified_cards)} results")
                        # Auto-cache ONLY verified matching documents into local SQLite + FTS5!
                        try:
                            from ..collector.wikiran_live import upsert_wikiran_documents_batch
                            to_save = [
                                {
                                    "doc_id": f"live:{abs(hash(c.get('source_url') or c.get('title')))}",
                                    "doc_type": c.get("wikiran_doc_type") or "LEAKED_FILE",
                                    "title": c.get("title") or "",
                                    "snippet": c.get("short_description") or "",
                                    "raw_description": c.get("editorial_content") or c.get("short_description") or "",
                                    "leak_sources": c.get("tags") or "",
                                    "leak_source_labels": c.get("source_name") or "WikIran Live",
                                    "country_or_flag": c.get("ofac_countries") or "",
                                    "bank_or_operator": c.get("organizations") or "",
                                    "identifier_or_imo": c.get("os_identifiers") or "",
                                    "document_date": c.get("publication_date") or "",
                                    "source_url": c.get("source_url") or "",
                                }
                                for c in verified_cards
                                if c.get("source_url")
                            ]
                            c_new, _ = upsert_wikiran_documents_batch(repo.conn, to_save)
                            newly_cached_wikiran_docs += c_new
                        except Exception:
                            pass
                    else:
                        wikiran_live_total_int = 0
                        wikiran_live_total_label = "0 results"
                else:
                    wikiran_live_total_label = "Offline"
                if live_queries_used < len(entries):
                    time.sleep(0.12)
            else:
                live_capped = True
                wikiran_live_total_label = f"Skipped (>{max_live_queries} live cap)"

        combined_evidence = (
            ofac_hits[:6]
            + os_hits[:6]
            + wikiran_offline_hits[:6]
            + wikiran_live_hits[:6]
        )
        total_hits = (
            len(ofac_hits)
            + len(os_hits)
            + len(wikiran_offline_hits)
            + len(wikiran_live_hits)
        )

        if ofac_hits or os_hits:
            risk_level = "HIGH_RISK"
            risk_label = "HIGH RISK (SANCTIONED)"
            high_risk_count += 1
        elif wikiran_offline_hits or wikiran_live_hits:
            risk_level = "ELEVATED_RISK"
            risk_label = "ELEVATED RISK (WIKIRAN HIT)"
            elevated_risk_count += 1
        else:
            risk_level = "CLEAR"
            risk_label = "CLEAR (NO MATCH)"
            clear_count += 1

        top_hit = combined_evidence[0] if combined_evidence else {}
        tags_collected: list[str] = []
        for h in combined_evidence[:4]:
            tag_val = str(h.get("programs_or_leak") or "").strip()
            if tag_val and tag_val not in tags_collected:
                tags_collected.append(tag_val)

        screened_results.append(
            {
                "row_number": int(entry["row_number"]),
                "name": primary_name,
                "alias": alias_raw,
                "entity_type": entry["entity_type"],
                "country": entry["country"],
                "reference_id": entry["reference_id"],
                "notes": entry["notes"],
                "risk_level": risk_level,
                "risk_label": risk_label,
                "total_hits": total_hits,
                "ofac_hits": len(ofac_hits),
                "opensanctions_hits": len(os_hits),
                "wikiran_offline_hits": len(wikiran_offline_hits),
                "wikiran_live_hits": len(wikiran_live_hits),
                "wikiran_live_total_int": wikiran_live_total_int,
                "wikiran_live_total_label": wikiran_live_total_label,
                "top_match_title": str(top_hit.get("title") or ""),
                "top_match_source": str(top_hit.get("source_bucket") or ""),
                "top_match_url": str(top_hit.get("source_url") or ""),
                "sanctions_or_leak_tags": " | ".join(tags_collected),
                "evidence_hits": combined_evidence,
            }
        )

    tier_rank = {"HIGH_RISK": 0, "ELEVATED_RISK": 1, "CLEAR": 2}
    screened_results.sort(key=lambda x: (tier_rank.get(x["risk_level"], 3), x["row_number"]))

    now_dt = datetime.now(timezone.utc)
    timestamp_tag = now_dt.strftime("%Y%m%d_%H%M%S")
    summary = {
        "screened_at": now_dt.isoformat(),
        "total_screened": len(screened_results),
        "high_risk_count": high_risk_count,
        "elevated_risk_count": elevated_risk_count,
        "clear_count": clear_count,
        "live_wikiran_enabled": bool(include_live_wikiran),
        "live_queries_used": live_queries_used,
        "live_capped": live_capped,
        "newly_cached_wikiran_docs": newly_cached_wikiran_docs,
        "detected_format": parsed["detected_format"],
        "detected_columns": parsed["detected_columns"],
        "skipped_rows": parsed["skipped_rows"],
    }

    csv_report = _export_batch_report_csv(exports_dir, screened_results, timestamp_tag)
    xlsx_report = _export_batch_report_xlsx(exports_dir, screened_results, summary, timestamp_tag)

    return {
        "ok": True,
        "summary": summary,
        "results": screened_results,
        "reports": {
            "csv_path": str(csv_report),
            "csv_filename": csv_report.name,
            "xlsx_path": str(xlsx_report),
            "xlsx_filename": xlsx_report.name,
        },
    }
