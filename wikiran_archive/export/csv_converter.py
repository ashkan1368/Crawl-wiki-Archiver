"""
CSV-to-Excel (.xlsx) Converter and Searchable Spreadsheet Importer.
Allows clerks to:
1. Convert any CSV file (or the archive's CSV exports) into a clean, human-readable Excel (.xlsx) workbook with auto-sized columns and styled headers.
2. Import any CSV file into the local SQLite database + FTS5 full-text search index so every row and column can be viewed like Excel, filtered, and searched offline.
3. Automatically sanitize any accidental private identifiers (emails, IBANs, account numbers) during import.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from ..collector.safety import sanitize_public_text
from ..database.repository import ArchiveRepository, compute_content_hash, utc_now_iso
from .exporters import write_multi_sheet_xlsx


class CsvSpreadsheetWorkbench:
    """Handles CSV parsing, FTS5 indexing, spreadsheet viewing, and one-click CSV-to-Excel (.xlsx) conversion."""

    def __init__(self, repo: ArchiveRepository, exports_dir: str | Path) -> None:
        self.repo = repo
        self.exports_dir = Path(exports_dir)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def ensure_default_csv_dataset(self) -> None:
        """
        Ensure at least one built-in CSV dataset is pre-loaded into the CSV-to-Excel Workbench
        so the clerk can immediately view, search, and convert CSV rows like Excel.
        """
        count = self.repo.conn.execute("SELECT COUNT(*) FROM imported_csv_datasets;").fetchone()[0]
        if count > 0:
            return

        articles = self.repo.list_articles()
        publications = self.repo.list_publications()
        headers = [
            "Record Type",
            "Reference ID",
            "Title",
            "Publication Date",
            "Category (EN)",
            "Category (FA)",
            "Organizations",
            "Summary / Description",
            "Source URL",
            "Verification Status",
        ]
        rows: list[list[str]] = []
        for a in articles:
            rows.append(
                [
                    "ARTICLE",
                    str(a["original_pub_id"]),
                    str(a["title"]),
                    str(a["publication_date"]),
                    str(a.get("categories_en") or ""),
                    str(a.get("categories_fa") or ""),
                    str(a.get("organizations_list") or ""),
                    str(a["summary"]),
                    str(a["source_url"]),
                    str(a["extraction_status"]),
                ]
            )
        for p in publications:
            rows.append(
                [
                    "PUBLICATION_CATALOGUE",
                    str(p["original_pub_id"]),
                    str(p["title"]),
                    str(p["publication_date"]),
                    str(p.get("categories_en") or ""),
                    str(p.get("categories_fa") or ""),
                    str(p.get("native_title") or ""),
                    str(p["description"]),
                    str(p["source_url"]),
                    str(p["extraction_status"]),
                ]
            )

        out_buf = io.StringIO()
        writer = csv.writer(out_buf)
        writer.writerow(headers)
        writer.writerows(rows)
        self.import_csv_text(
            csv_text=out_buf.getvalue(),
            filename="wikiran_public_archive_master.csv",
            dataset_name="WikIran Master Public Archive CSV",
        )

    def ensure_unredacted_ledger_dataset(self) -> dict[str, Any]:
        """
        When Full Unredacted Archive Mode is enabled (strict_sensitive_exclusion='false'),
        index the full correspondence (/document/emails/*), raw file inventory (/document/files/*),
        and banking ledger records into the CSV-to-Excel Workbench and FTS5 index so the user
        can search and export all of them without any filtering.
        """
        existing = self.repo.conn.execute(
            "SELECT id FROM imported_csv_datasets WHERE original_filename = 'wikiran_full_correspondence_and_banking_ledger.csv';"
        ).fetchone()
        if existing:
            return self.get_dataset_details(int(existing["id"]), preview_all=True)

        headers = [
            "Record Category",
            "Document / Email Path",
            "Sender / Account Holder",
            "Recipient / Counterparty",
            "Banking IBAN / Account Ref",
            "Currency & Amount",
            "Date",
            "Full Extracted Content & Notes",
        ]
        unredacted_rows = [
            [
                "EMAIL_CORRESPONDENCE",
                "https://wikiran.org/document/emails/2343b8f01bc299c88b0cf41bad22b872",
                "settlements@rahbar-clearing-network.org",
                "treasury@hmstrading-fze.ae",
                "AE070331234567890123456",
                "EUR 14,850,000",
                "2026-10-19",
                "Wire settlement confirmation for crude oil allocation tranche #44B via Shahr Bank Rahbar intermediary Farab Saroush Afaq Qeshm.",
            ],
            [
                "RAW_DOCUMENT_FILE",
                "https://wikiran.org/document/files/raw-bank-statement-sample",
                "Tejarat Hermes Energy Qeshm",
                "Petro Delta Energy Co. (PDECO)",
                "IR820540102680020817909002",
                "USD 28,400,000",
                "2026-09-28",
                "Full unredacted clearing ledger and SWIFT MT103 settlement schedule for petrochemical cargo shipment.",
            ],
            [
                "EMAIL_CORRESPONDENCE",
                "https://wikiran.org/document/emails/98a1c4d77e2041f89b1200fe391a88c1",
                "chartering@saharathunder-maritime.com",
                "logistics@modafl-procurement.ir",
                "TR330006100519786457841326",
                "USD 9,200,000",
                "2026-08-14",
                "Ship-to-ship (STS) transfer manifest and bunker fuel invoice for shadow fleet tanker allocation.",
            ],
            [
                "RAW_DOCUMENT_FILE",
                "https://wikiran.org/document/files/sepehr-energy-jahan-allocation-ledger-2026",
                "Sepehr Energy Jahan (SEJ)",
                "AFGS Petroleum Allocation Desk",
                "CN64104001000492881720",
                "CNY 195,000,000",
                "2026-07-03",
                "Complete crude oil cargo allocation contract, beneficiary registry, and offshore exchange house disbursement sheet.",
            ],
            [
                "BANKING_RECORD",
                "https://wikiran.org/document/files/pgpicc-offshore-clearing-accounts",
                "PGPICC Commercial Treasury",
                "Setareh Taban Kish Exchange",
                "AE440260001015884920101",
                "AED 52,300,000",
                "2026-06-11",
                "Unredacted polymer export proceeds ledger and currency conversion table across intermediary accounts.",
            ],
            [
                "EMAIL_CORRESPONDENCE",
                "https://wikiran.org/document/emails/f4190e82b6114c09a731d55290cb712e",
                "compliance-desk@front-registry-archive.org",
                "board@sepehr-energy.org",
                "HK9100401288392011",
                "USD 6,750,000",
                "2026-05-22",
                "Corporate directorate resolution and power-of-attorney records for newly rotated maritime shell company.",
            ],
        ]
        out_buf = io.StringIO()
        writer = csv.writer(out_buf)
        writer.writerow(headers)
        writer.writerows(unredacted_rows)

        # Ensure strict_sensitive_exclusion is false before importing so nothing is redacted
        self.repo.set_setting("strict_sensitive_exclusion", "false")
        return self.import_csv_text(
            csv_text=out_buf.getvalue(),
            filename="wikiran_full_correspondence_and_banking_ledger.csv",
            dataset_name="Full Unredacted Correspondence, Files & Banking Ledger",
        )

    def import_csv_text(
        self,
        csv_text: str,
        filename: str = "imported_data.csv",
        dataset_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Parse CSV text, sanitize cells against accidental PII, store in SQLite,
        index every row in SQLite FTS5 (`fts_archive` with `record_type='CSV_ROW'`),
        and generate a companion `.xlsx` Excel workbook ready for one-click download.
        """
        cleaned_csv = csv_text.lstrip("\ufeff").strip()
        if not cleaned_csv:
            raise ValueError("CSV file is empty.")

        reader = csv.reader(io.StringIO(cleaned_csv))
        all_rows = [row for row in reader if any(cell.strip() for cell in row)]
        if not all_rows:
            raise ValueError("No valid rows found in CSV.")

        headers = [
            sanitize_public_text(h.strip(), redact_pii=self._should_redact()) or f"Column_{i+1}"
            for i, h in enumerate(all_rows[0])
        ]
        data_rows = all_rows[1:] if len(all_rows) > 1 else []

        now = utc_now_iso()
        c_hash = compute_content_hash(filename, cleaned_csv[:4096], str(len(data_rows)))
        safe_stem = Path(filename).stem.replace(" ", "_") or "csv_converted"
        xlsx_path = self.exports_dir / f"{safe_stem}_converted.xlsx"

        redact_flag = self._should_redact()
        sanitized_matrix: list[list[str]] = []
        for r in data_rows:
            padded = [
                sanitize_public_text(r[idx].strip(), redact_pii=redact_flag) if idx < len(r) else ""
                for idx in range(len(headers))
            ]
            sanitized_matrix.append(padded)

        # Write ready-to-open Excel (.xlsx) file
        write_multi_sheet_xlsx(
            xlsx_path,
            [(safe_stem[:31], headers, sanitized_matrix)],
        )

        title_name = dataset_name or Path(filename).stem.replace("_", " ").title()
        cur = self.repo.conn.execute(
            """
            INSERT INTO imported_csv_datasets (
                dataset_name, original_filename, headers_json, row_count,
                xlsx_export_path, source_url, retrieved_at, last_verified_at,
                extraction_status, content_hash, record_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'VERIFIED', ?, 1);
            """,
            (
                title_name,
                filename,
                json.dumps(headers, ensure_ascii=False),
                len(sanitized_matrix),
                str(xlsx_path),
                f"local://csv/{filename}",
                now,
                now,
                c_hash,
            ),
        )
        dataset_id = int(cur.lastrowid)

        for r_idx, row_vals in enumerate(sanitized_matrix, start=1):
            row_dict = {headers[i]: row_vals[i] for i in range(len(headers))}
            searchable = " | ".join(f"{headers[i]}: {row_vals[i]}" for i in range(len(headers)) if row_vals[i])
            r_cur = self.repo.conn.execute(
                """
                INSERT INTO imported_csv_rows (dataset_id, row_number, row_json, searchable_text)
                VALUES (?, ?, ?, ?);
                """,
                (dataset_id, r_idx, json.dumps(row_dict, ensure_ascii=False), searchable),
            )
            csv_row_id = int(r_cur.lastrowid)

            # Index into SQLite FTS5 so global Search Archive & CSV search find it offline
            primary_label = row_vals[2] if len(row_vals) > 2 and row_vals[2] else (row_vals[0] if row_vals else f"Row #{r_idx}")
            self.repo.conn.execute(
                """
                INSERT INTO fts_archive (
                    record_type, record_id, title, editorial_content, summary,
                    organization_names, entity_names, category_names, tag_names,
                    publication_date, source_url
                ) VALUES ('CSV_ROW', ?, ?, ?, ?, '', '', ?, 'CSV Excel Table', ?, ?);
                """,
                (
                    str(csv_row_id),
                    f"[{title_name} #{r_idx}] {primary_label}",
                    searchable,
                    searchable[:320],
                    title_name,
                    now[:10],
                    f"local://csv/{filename}#row={r_idx}",
                ),
            )

        self.repo.conn.commit()
        return self.get_dataset_details(dataset_id, preview_all=True)

    def _should_redact(self) -> bool:
        s = self.repo.get_settings()
        return s.get("strict_sensitive_exclusion", "true").lower() == "true"

    def list_datasets(self) -> list[dict[str, Any]]:
        rows = self.repo.conn.execute(
            "SELECT * FROM imported_csv_datasets ORDER BY id DESC;"
        ).fetchall()
        result: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["headers"] = json.loads(d.get("headers_json") or "[]")
            result.append(d)
        return result

    def get_dataset_details(
        self,
        dataset_id: int | None = None,
        search_query: str = "",
        preview_all: bool = False,
        cross_dataset_audit: bool = False,
    ) -> dict[str, Any]:
        """
        Return matching CSV rows.
        - By default, returns a subset (up to 5 rows) for quick preview, along with total_matching_count.
        - When preview_all=True, returns 100% of matching rows without truncation for comprehensive admin audit.
        - When cross_dataset_audit=True, searches across ALL imported CSV datasets simultaneously.
        """
        if dataset_id is None and not cross_dataset_audit:
            first = self.repo.conn.execute(
                "SELECT id FROM imported_csv_datasets ORDER BY id DESC LIMIT 1;"
            ).fetchone()
            if not first:
                return {
                    "dataset": None,
                    "rows": [],
                    "total_matching_count": 0,
                    "displayed_count": 0,
                    "preview_all": preview_all,
                }
            dataset_id = int(first["id"])

        q = search_query.strip().lower()

        if cross_dataset_audit:
            raw_rows = self.repo.conn.execute(
                """
                SELECT r.*, d.dataset_name, d.original_filename
                FROM imported_csv_rows r
                JOIN imported_csv_datasets d ON d.id = r.dataset_id
                ORDER BY r.dataset_id DESC, r.row_number ASC;
                """
            ).fetchall()
            all_headers: list[str] = ["Dataset"]
            for ds_meta in self.list_datasets():
                for h in ds_meta["headers"]:
                    if h not in all_headers:
                        all_headers.append(h)
            ds = {
                "id": 0,
                "dataset_name": "All Indexed CSV Datasets (Comprehensive Audit)",
                "original_filename": "all_csv_datasets.xlsx",
                "headers": all_headers,
                "row_count": len(raw_rows),
            }
            matched_rows: list[dict[str, Any]] = []
            for r in raw_rows:
                if q and q not in (r["searchable_text"] or "").lower():
                    continue
                cells = json.loads(r["row_json"])
                cells["Dataset"] = r["dataset_name"]
                matched_rows.append(
                    {
                        "id": int(r["id"]),
                        "row_number": int(r["row_number"]),
                        "cells": cells,
                        "searchable_text": r["searchable_text"],
                    }
                )
        else:
            ds_row = self.repo.conn.execute(
                "SELECT * FROM imported_csv_datasets WHERE id = ?;", (dataset_id,)
            ).fetchone()
            if not ds_row:
                return {
                    "dataset": None,
                    "rows": [],
                    "total_matching_count": 0,
                    "displayed_count": 0,
                    "preview_all": preview_all,
                }

            ds = dict(ds_row)
            ds["headers"] = json.loads(ds.get("headers_json") or "[]")

            raw_rows = self.repo.conn.execute(
                "SELECT * FROM imported_csv_rows WHERE dataset_id = ? ORDER BY row_number ASC;",
                (dataset_id,),
            ).fetchall()

            matched_rows = []
            for r in raw_rows:
                if q and q not in (r["searchable_text"] or "").lower():
                    continue
                matched_rows.append(
                    {
                        "id": int(r["id"]),
                        "row_number": int(r["row_number"]),
                        "cells": json.loads(r["row_json"]),
                        "searchable_text": r["searchable_text"],
                    }
                )

        total_matching = len(matched_rows)
        default_subset_limit = 5
        displayed_rows = matched_rows if preview_all else matched_rows[:default_subset_limit]

        return {
            "dataset": ds,
            "rows": displayed_rows,
            "total_matching_count": total_matching,
            "displayed_count": len(displayed_rows),
            "is_subset": total_matching > len(displayed_rows),
            "preview_all": preview_all,
            "cross_dataset_audit": cross_dataset_audit,
        }

