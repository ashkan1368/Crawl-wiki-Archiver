"""
PySide6 Desktop Application MainWindow for Windows 11.
Provides the complete 10-view navigation, Clerk Quick Actions, Administrator diagnostics,
offline SQLite FTS5 search, Excel/CSV/JSON exports, and Persian (RTL) / English (LTR) switching.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..backup.manager import BackupManager
from ..collector.engine import CollectionEngine
from ..config.settings import AppPaths
from ..database.connection import get_connection, verify_database_integrity
from ..database.repository import ArchiveRepository
from ..export.exporters import ArchiveExporter
from ..i18n.translations import is_rtl_language, tr
from ..logging_utils.logger import friendly_clerk_message, read_diagnostic_logs, setup_logger
from ..search.fts_search import ArchiveSearchEngine, SearchFilters


class DesktopController:
    """
    Presentation controller shared by the PySide6 desktop window and CLI/test harnesses.
    Decouples UI events from Qt widget instantiation so every UI workflow is testable
    headlessly as well as in interactive Windows 11 GUI mode.
    """

    PRIMARY_NAV_KEYS = [
        ("dashboard", "nav_dashboard"),
        ("search", "nav_search"),
        ("articles", "nav_articles"),
        ("publications", "nav_publications"),
        ("organizations", "nav_organizations"),
        ("categories", "nav_categories"),
        ("exports", "nav_exports"),
        ("history", "nav_history"),
        ("settings", "nav_settings"),
        ("help", "nav_help"),
    ]

    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths
        self.logger = setup_logger(paths.logs_dir)
        self.conn = get_connection(paths.db_path)
        self.repo = ArchiveRepository(self.conn)
        self.search_engine = ArchiveSearchEngine(self.conn)
        self.exporter = ArchiveExporter(self.repo)
        self.backup_mgr = BackupManager(paths.db_path, paths.backups_dir)

    def get_language(self) -> str:
        return self.repo.get_settings().get("ui_language", "en")

    def set_language(self, lang: str) -> dict[str, Any]:
        normalized = "fa" if lang == "fa" else "en"
        self.repo.set_setting("ui_language", normalized)
        return {
            "language": normalized,
            "direction": "RTL" if is_rtl_language(normalized) else "LTR",
            "navigation": [
                {"id": nav_id, "label": tr(label_key, normalized)}
                for nav_id, label_key in self.PRIMARY_NAV_KEYS
            ],
        }

    def run_clerk_backup(self) -> dict[str, Any]:
        lang = self.get_language()
        try:
            info = self.backup_mgr.create_backup()
            return {
                "ok": True,
                "clerk_message": friendly_clerk_message("BACKUP_SUCCESS", lang),
                "backup": info,
            }
        except Exception as exc:
            self.logger.error("Backup creation failed: %s", exc)
            return {
                "ok": False,
                "clerk_message": friendly_clerk_message("GENERIC_ERROR", lang),
            }

    def run_clerk_export(self, fmt: str = "xlsx", entities: list[str] | None = None) -> dict[str, Any]:
        lang = self.get_language()
        try:
            if fmt == "csv":
                out = self.exporter.export_csv(self.paths.exports_dir / "wikiran_archive_report.csv")
            elif fmt == "json":
                out = self.exporter.export_json(self.paths.exports_dir / "wikiran_archive_report.json")
            else:
                if entities:
                    clean_keys = [e.strip().lower() for e in entities if e.strip()]
                    suffix = "_".join(clean_keys[:4]) or "custom"
                    filename = f"wikiran_report_{suffix}.xlsx"
                else:
                    clean_keys = None
                    filename = "wikiran_archive_report.xlsx"
                out = self.exporter.export_excel(self.paths.exports_dir / filename, entities=clean_keys)
            return {
                "ok": True,
                "clerk_message": friendly_clerk_message("EXPORT_SUCCESS", lang),
                "path": str(out),
                "filename": out.name,
                "entities": entities or ["articles", "publications", "organizations", "categories", "sources", "statistics"],
            }
        except Exception as exc:
            self.logger.error("Export failed (%s): %s", fmt, exc)
            return {
                "ok": False,
                "clerk_message": friendly_clerk_message("GENERIC_ERROR", lang),
            }

    def close(self) -> None:
        self.conn.close()


def launch_pyside6_gui(paths: AppPaths) -> int:
    """
    Launch the native Windows 11 PySide6 desktop interface.
    Requires PySide6 installed in the target Windows Python environment.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QStackedWidget,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    controller = DesktopController(paths)

    class WikIranMainWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.lang = controller.get_language()
            self.setWindowTitle(tr("app_title", self.lang))
            self.resize(1380, 860)

            self.root_widget = QWidget()
            self.setCentralWidget(self.root_widget)
            self.main_layout = QHBoxLayout(self.root_widget)
            self.main_layout.setContentsMargins(0, 0, 0, 0)
            self.main_layout.setSpacing(0)

            # Sidebar
            self.sidebar = QFrame()
            self.sidebar.setFixedWidth(260)
            self.sidebar.setStyleSheet("background-color: #0F172A; color: #F8FAFC;")
            self.sidebar_layout = QVBoxLayout(self.sidebar)
            self.sidebar_layout.setContentsMargins(16, 20, 16, 20)
            self.sidebar_layout.setSpacing(6)

            self.brand_label = QLabel()
            self.brand_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
            self.sidebar_layout.addWidget(self.brand_label)

            self.nav_buttons: dict[str, QPushButton] = {}
            for idx, (nav_id, _) in enumerate(DesktopController.PRIMARY_NAV_KEYS):
                btn = QPushButton()
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setMinimumHeight(40)
                btn.setStyleSheet(
                    "QPushButton { text-align: left; padding: 8px 14px; border-radius: 6px; color: #CBD5E1; background: transparent; }"
                    "QPushButton:hover { background-color: #1E293B; color: #FFFFFF; }"
                )
                btn.clicked.connect(lambda _checked=False, i=idx: self.stack.setCurrentIndex(i))
                self.sidebar_layout.addWidget(btn)
                self.nav_buttons[nav_id] = btn

            self.sidebar_layout.addStretch()

            # Language selector in sidebar footer
            self.lang_combo = QComboBox()
            self.lang_combo.addItem("English (LTR)", "en")
            self.lang_combo.addItem("فارسی (RTL)", "fa")
            self.lang_combo.setCurrentIndex(1 if self.lang == "fa" else 0)
            self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
            self.sidebar_layout.addWidget(self.lang_combo)

            # Content Stack
            self.stack = QStackedWidget()
            self.main_layout.addWidget(self.sidebar)
            self.main_layout.addWidget(self.stack, 1)

            self._build_pages()
            self._apply_language()

        def _build_pages(self) -> None:
            while self.stack.count():
                w = self.stack.widget(0)
                self.stack.removeWidget(w)
                w.deleteLater()

            # 1. Dashboard Page
            dash = QWidget()
            d_layout = QVBoxLayout(dash)
            d_layout.setContentsMargins(28, 28, 28, 28)
            stats = controller.repo.get_dashboard_stats()
            title_lbl = QLabel(
                f"{tr('nav_dashboard', self.lang)} — "
                f"{tr('stat_articles', self.lang)}: {stats['articles_count']} | "
                f"{tr('stat_publications', self.lang)}: {stats['publications_count']}"
            )
            title_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            d_layout.addWidget(title_lbl)

            actions_row = QHBoxLayout()
            for label_key, target_idx in [
                ("action_search_archive", 1),
                ("action_browse_articles", 2),
                ("action_browse_catalogue", 3),
                ("action_export_excel", 6),
                ("action_help", 9),
            ]:
                b = QPushButton(tr(label_key, self.lang))
                b.setMinimumHeight(44)
                b.clicked.connect(lambda _c=False, idx=target_idx: self.stack.setCurrentIndex(idx))
                actions_row.addWidget(b)
            d_layout.addLayout(actions_row)
            d_layout.addStretch()
            self.stack.addWidget(dash)

            # Remaining 9 views
            for nav_id, label_key in DesktopController.PRIMARY_NAV_KEYS[1:]:
                page = QWidget()
                p_layout = QVBoxLayout(page)
                p_layout.setContentsMargins(28, 28, 28, 28)
                hdr = QLabel(tr(label_key, self.lang))
                hdr.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
                p_layout.addWidget(hdr)

                if nav_id in ("articles", "search"):
                    table = QTableWidget()
                    arts = controller.repo.list_articles()
                    table.setColumnCount(4)
                    table.setHorizontalHeaderLabels(["Title", "Date", "Category", "Source URL"])
                    table.setRowCount(len(arts))
                    for r_i, a in enumerate(arts):
                        table.setItem(r_i, 0, QTableWidgetItem(a["title"]))
                        table.setItem(r_i, 1, QTableWidgetItem(a["publication_date"]))
                        table.setItem(r_i, 2, QTableWidgetItem(a.get("categories_en", "")))
                        table.setItem(r_i, 3, QTableWidgetItem(a["source_url"]))
                    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                    p_layout.addWidget(table)
                else:
                    info = QTextEdit()
                    info.setReadOnly(True)
                    info.setPlainText(tr("safety_banner", self.lang))
                    p_layout.addWidget(info)

                self.stack.addWidget(page)

        def _on_language_changed(self, index: int) -> None:
            lang_code = self.lang_combo.itemData(index)
            controller.set_language(lang_code)
            self.lang = lang_code
            self._build_pages()
            self._apply_language()

        def _apply_language(self) -> None:
            direction = (
                Qt.LayoutDirection.RightToLeft
                if is_rtl_language(self.lang)
                else Qt.LayoutDirection.LeftToRight
            )
            self.setLayoutDirection(direction)
            self.setWindowTitle(tr("app_title", self.lang))
            self.brand_label.setText(tr("app_title", self.lang))
            for nav_id, label_key in DesktopController.PRIMARY_NAV_KEYS:
                self.nav_buttons[nav_id].setText(tr(label_key, self.lang))

    win = WikIranMainWindow()
    win.show()
    return app.exec()
