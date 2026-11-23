"""
WikIran Archive — Portable Edition Local Server (Pure Python Standard Library).

Runs locally on Windows 11 with ZERO Node.js and ZERO unsigned .exe files:
- Serves the compiled React UI from ./dist/
- Handles all /api/* routes directly through wikiran_archive.main.handle_api_command
- Stores all SQLite data, exports, backups, and logs right inside the portable folder
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import socket
import sys
import tempfile
import threading
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

# Ensure portable folder root is on sys.path
PORTABLE_ROOT = Path(__file__).resolve().parent
if str(PORTABLE_ROOT) not in sys.path:
    sys.path.insert(0, str(PORTABLE_ROOT))

from wikiran_archive.main import handle_api_command  # noqa: E402

DOC_FILES: dict[str, str] = {
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


def _find_available_port(preferred: int = 3000, max_tries: int = 15) -> int:
    for p in range(preferred, preferred + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return preferred


def make_handler(dist_dir: Path, data_dir: Path, project_root: Path):
    class PortableHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args: Any) -> None:
            # Keep Windows console output clean and readable
            pass

        def _send_json(self, obj: Any, status: int = 200) -> None:
            raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def _send_file(self, file_path: Path, download_name: str | None = None) -> None:
            if not file_path.exists() or not file_path.is_file():
                self._send_json({"ok": False, "error": "File not found"}, status=404)
                return
            mime, _ = mimetypes.guess_type(str(file_path))
            if file_path.suffix.lower() == ".js":
                mime = "application/javascript; charset=utf-8"
            elif file_path.suffix.lower() == ".css":
                mime = "text/css; charset=utf-8"
            elif file_path.suffix.lower() == ".svg":
                mime = "image/svg+xml"
            elif not mime:
                mime = "application/octet-stream"

            size = file_path.stat().st_size
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(size))
            if download_name:
                safe_name = download_name.replace('"', "")
                self.send_header("Content-Disposition", f'attachment; filename="{safe_name}"')
            self.end_headers()
            with file_path.open("rb") as f:
                while True:
                    chunk = f.read(256 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)

        def _read_json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            try:
                parsed = json.loads(raw.decode("utf-8"))
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}

        def _run_api(self, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
            return handle_api_command(
                action,
                json.dumps(payload or {}, ensure_ascii=False),
                custom_dir=str(data_dir),
            )

        def do_GET(self) -> None:
            parsed = urllib.parse.urlsplit(self.path)
            path = parsed.path
            qs = urllib.parse.parse_qs(parsed.query)

            try:
                if path == "/api/health":
                    self._send_json({"ok": True, "mode": "portable", "data_dir": str(data_dir)})
                    return

                if path == "/api/overview":
                    self._send_json(self._run_api("overview"))
                    return

                if path == "/api/crawl-status":
                    self._send_json(self._run_api("crawl_status"))
                    return

                if path == "/api/ofac/status":
                    self._send_json(self._run_api("ofac_status"))
                    return

                if path == "/api/opensanctions/status":
                    self._send_json(self._run_api("opensanctions_status"))
                    return

                if path.startswith("/api/export/"):
                    fmt = path.replace("/api/export/", "").strip("/").lower() or "xlsx"
                    raw_ent = (qs.get("entities") or [""])[0]
                    entities = [e.strip().lower() for e in raw_ent.split(",") if e.strip()] or None
                    date_from = (qs.get("date_from") or [""])[0].strip() or None
                    date_to = (qs.get("date_to") or [""])[0].strip() or None
                    data = self._run_api(
                        "export",
                        {"format": fmt, "entities": entities, "date_from": date_from, "date_to": date_to},
                    )
                    out_p = Path(str(data.get("path") or ""))
                    if not data.get("ok") or not out_p.exists():
                        self._send_json({"ok": False, "error": "Export file could not be generated."}, 500)
                        return
                    self._send_file(out_p, download_name=str(data.get("filename") or out_p.name))
                    return

                if path.startswith("/api/csv/download/"):
                    ds_id = int(path.replace("/api/csv/download/", "").strip("/"))
                    data = self._run_api("csv_view", {"dataset_id": ds_id})
                    xlsx_path = Path(str(((data.get("active_csv") or {}).get("dataset") or {}).get("xlsx_export_path") or ""))
                    if not xlsx_path.exists():
                        self._send_json({"ok": False, "error": "Converted Excel file not found."}, 404)
                        return
                    self._send_file(xlsx_path, download_name=xlsx_path.name)
                    return

                if path == "/api/backup/full-download":
                    req_path = (qs.get("path") or [""])[0].strip()
                    if req_path and Path(req_path).exists() and req_path.lower().endswith(".zip"):
                        p = Path(req_path)
                        self._send_file(p, download_name=p.name)
                        return
                    data = self._run_api("backup_full_create")
                    zip_p = Path(str((data.get("backup") or {}).get("path") or ""))
                    if not data.get("ok") or not zip_p.exists():
                        self._send_json({"ok": False, "error": "Full portable backup could not be created."}, 500)
                        return
                    self._send_file(zip_p, download_name=zip_p.name)
                    return

                if path.startswith("/api/watchlist/template/"):
                    fmt = path.replace("/api/watchlist/template/", "").strip("/").lower()
                    fmt = "csv" if fmt == "csv" else "xlsx"
                    data = self._run_api("watchlist_template", {"format": fmt})
                    out_p = Path(str(data.get("path") or ""))
                    if not data.get("ok") or not out_p.exists():
                        self._send_json({"ok": False, "error": "Template could not be generated."}, 500)
                        return
                    self._send_file(out_p, download_name=str(data.get("filename") or out_p.name))
                    return

                if path == "/api/watchlist/report/download":
                    req_path = (qs.get("path") or [""])[0].strip()
                    p = Path(req_path) if req_path else Path("")
                    if (
                        not req_path
                        or not p.exists()
                        or not p.name.startswith("WikIran_Watchlist_Risk_Report_")
                        or p.suffix.lower() not in (".xlsx", ".csv")
                    ):
                        self._send_json({"ok": False, "error": "Watchlist risk report not found."}, 404)
                        return
                    self._send_file(p, download_name=p.name)
                    return

                if path == "/api/leaks/catalog":
                    refresh_flag = ((qs.get("refresh") or [""])[0].strip().lower() in ("1", "true"))
                    self._send_json(self._run_api("leaks_catalog", {"refresh": refresh_flag}))
                    return

                if path in ("/api/download/windows-portable-lite-zip", "/api/download/windows-portable-zip", "/api/download/windows-package"):
                    action_key = "windows_portable_lite_zip" if "lite" in path else "windows_portable_zip"
                    data = self._run_api(action_key)
                    zip_p = Path(str(data.get("path") or ""))
                    if not data.get("ok") or not zip_p.exists():
                        self._send_json({"ok": False, "error": "Portable ZIP could not be generated."}, 500)
                        return
                    self._send_file(zip_p, download_name=str(data.get("filename") or zip_p.name))
                    return

                if path in ("/api/download/windows-portable-chunk", "/api/backup/full-chunk"):
                    target_file = (
                        data_dir / "exports" / "WikIranArchive_Portable_Windows.zip"
                        if "portable" in path
                        else None
                    )
                    if target_file is None:
                        b_dir = data_dir / "backups"
                        zips = sorted(b_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True) if b_dir.exists() else []
                        target_file = zips[0] if zips else None
                    if not target_file or not target_file.exists():
                        self._send_json({"ok": False, "error": "Prepared ZIP file not found."}, 404)
                        return
                    fsize = target_file.stat().st_size
                    offset = max(0, int((qs.get("offset") or ["0"])[0]))
                    length = min(16 * 1024 * 1024, max(1, int((qs.get("length") or [str(8 * 1024 * 1024)])[0])))
                    if offset >= fsize:
                        self._send_json({"ok": False, "error": "Offset out of range"}, 416)
                        return
                    read_len = min(length, fsize - offset)
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(read_len))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    with target_file.open("rb") as fh:
                        fh.seek(offset)
                        rem = read_len
                        while rem > 0:
                            buf = fh.read(min(256 * 1024, rem))
                            if not buf:
                                break
                            self.wfile.write(buf)
                            rem -= len(buf)
                    return

                if path.startswith("/api/docs/"):
                    key = path.replace("/api/docs/", "").strip("/")
                    rel = DOC_FILES.get(key)
                    if not rel:
                        self._send_json({"ok": False, "error": "Document not found"}, 404)
                        return
                    fp = project_root / rel
                    if not fp.exists():
                        self._send_json({"ok": False, "error": "File missing on disk"}, 404)
                        return
                    self._send_json(
                        {"ok": True, "filename": rel, "content": fp.read_text(encoding="utf-8", errors="replace")}
                    )
                    return

                # Serve static React frontend from ./dist/
                rel_static = path.lstrip("/")
                if not rel_static:
                    rel_static = "index.html"
                candidate = (dist_dir / rel_static).resolve()
                if str(candidate).startswith(str(dist_dir.resolve())) and candidate.is_file():
                    self._send_file(candidate)
                    return

                # SPA fallback
                index_file = dist_dir / "index.html"
                if index_file.exists():
                    self._send_file(index_file)
                    return
                self._send_json({"ok": False, "error": "Frontend dist/index.html missing."}, 404)
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, 500)

        def do_POST(self) -> None:
            parsed = urllib.parse.urlsplit(self.path)
            path = parsed.path

            try:
                if path == "/api/shutdown":
                    self._send_json({"ok": True, "message": "Shutting down portable server..."})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return

                if path == "/api/backup/full-restore-upload":
                    raw_name = str(self.headers.get("X-Backup-Filename") or "uploaded_backup.zip")
                    ext = ".db" if raw_name.lower().endswith(".db") else ".zip"
                    length = int(self.headers.get("Content-Length") or 0)
                    fd, tmp_name = tempfile.mkstemp(prefix="wikiran_restore_", suffix=ext)
                    os.close(fd)
                    tmp_path = Path(tmp_name)
                    try:
                        remaining = length
                        with tmp_path.open("wb") as out_f:
                            while remaining > 0:
                                chunk = self.rfile.read(min(256 * 1024, remaining))
                                if not chunk:
                                    break
                                out_f.write(chunk)
                                remaining -= len(chunk)
                        data = self._run_api(
                            "backup_full_restore", {"path": str(tmp_path), "confirmed": True}
                        )
                        self._send_json(data)
                    finally:
                        tmp_path.unlink(missing_ok=True)
                    return

                if path == "/api/download/windows-portable-prepare":
                    data = self._run_api("windows_portable_zip")
                    zip_p = Path(str(data.get("path") or ""))
                    if not data.get("ok") or not zip_p.exists():
                        self._send_json({"ok": False, "error": "Portable ZIP could not be generated."}, 500)
                        return
                    sz = zip_p.stat().st_size
                    cs = 8 * 1024 * 1024
                    self._send_json({
                        "ok": True,
                        "filename": zip_p.name,
                        "size_bytes": sz,
                        "chunk_size": cs,
                        "total_chunks": (sz + cs - 1) // cs,
                    })
                    return

                if path == "/api/backup/full-prepare":
                    body_p = self._read_json_body()
                    req_p = str(body_p.get("path") or "").strip()
                    if req_p and Path(req_p).exists() and req_p.lower().endswith(".zip"):
                        zip_p = Path(req_p)
                    else:
                        data = self._run_api("backup_full_create")
                        zip_p = Path(str((data.get("backup") or {}).get("path") or ""))
                    if not zip_p.exists():
                        self._send_json({"ok": False, "error": "Backup ZIP could not be prepared."}, 500)
                        return
                    sz = zip_p.stat().st_size
                    cs = 8 * 1024 * 1024
                    self._send_json({
                        "ok": True,
                        "filename": zip_p.name,
                        "size_bytes": sz,
                        "chunk_size": cs,
                        "total_chunks": (sz + cs - 1) // cs,
                    })
                    return

                body = self._read_json_body()
                route_map: dict[str, tuple[str, dict[str, Any]]] = {
                    "/api/search": ("search", body),
                    "/api/settings": ("set_settings", {"settings": body}),
                    "/api/schedule": ("schedule_update", body),
                    "/api/schedule/run-now": ("schedule_run_now", {}),
                    "/api/update-archive": ("update_archive", body),
                    "/api/stop-crawl": ("stop_crawl", {}),
                    "/api/resume-job": ("resume_job", body),
                    "/api/ofac/sync": ("ofac_sync", body),
                    "/api/opensanctions/sync": ("opensanctions_sync", body),
                    "/api/wikiran/sync-archives": ("wikiran_sync_archives", body),
                    "/api/watchlist/screen": ("watchlist_screen", body),
                    "/api/leaks/download": ("leaks_download", body),
                    "/api/reconnaissance": ("reconnaissance", {}),
                    "/api/csv/import": ("csv_import", body),
                    "/api/csv/view": ("csv_view", body),
                    "/api/backup/create": ("backup_create", {}),
                    "/api/backup/full-create": ("backup_full_create", {}),
                    "/api/backup/restore": ("backup_restore", body),
                    "/api/integrity-check": ("integrity_check", {}),
                }
                if path in route_map:
                    action, payload = route_map[path]
                    self._send_json(self._run_api(action, payload))
                    return

                self._send_json({"ok": False, "error": f"Unknown endpoint: {path}"}, 404)
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, 500)

    return PortableHandler


def main() -> int:
    parser = argparse.ArgumentParser(description="WikIran Archive Portable Server")
    parser.add_argument("--port", type=int, default=3000)
    parser.add_argument("--data-dir", type=str, default=str(PORTABLE_ROOT))
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    dist_dir = PORTABLE_ROOT / "dist"
    port = _find_available_port(args.port)

    port_file = data_dir / ".portable_port"
    try:
        port_file.write_text(str(port), encoding="utf-8")
    except OSError:
        pass

    handler_cls = make_handler(dist_dir=dist_dir, data_dir=data_dir, project_root=PORTABLE_ROOT)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler_cls)
    print(f"WikIran Archive Portable Server listening on http://127.0.0.1:{port}", flush=True)
    print(f"Portable Data Folder: {data_dir}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        try:
            port_file.unlink(missing_ok=True)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
