"""
Logging and friendly clerk message mapping.
Ensures Python tracebacks, SQL queries, and HTTP debug noise are never shown to the clerk,
while preserving detailed diagnostic logs for administrators.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(logs_dir: Path, name: str = "wikiran_archive") -> logging.Logger:
    """Configure a rotating file logger for technical administrator diagnostics."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "diagnostic.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def friendly_clerk_message(error_code: str, lang: str = "en") -> str:
    """
    Return a non-technical, friendly message suitable for an office clerk.
    Never exposes Python stack traces, SQL syntax, or raw HTTP exceptions.
    """
    messages_en = {
        "NETWORK_UNAVAILABLE": "Could not reach the online archive. You can continue searching all local records offline.",
        "RATE_LIMITED": "The website requested a slower connection speed. Collection has paused automatically and can be resumed later.",
        "ACCESS_RESTRICTED": "Online access is temporarily restricted by the remote server. Collection has been safely paused.",
        "BACKUP_SUCCESS": "A verified safety backup of the archive has been created.",
        "BACKUP_RESTORE_SUCCESS": "The archive has been safely restored from the selected backup.",
        "BACKUP_INVALID": "The selected backup file could not be verified and was not restored.",
        "EXPORT_SUCCESS": "Your report has been exported and saved to the Exports folder.",
        "COLLECTION_INTERRUPTED": "The update was paused. Progress was saved and can be resumed at any time.",
        "GENERIC_ERROR": "The operation could not be completed. Details have been recorded in the Administrator log.",
    }
    messages_fa = {
        "NETWORK_UNAVAILABLE": "امکان اتصال به سامانه آنلاین وجود ندارد. می‌توانید بدون اینترنت در آرشیو محلی جستجو کنید.",
        "RATE_LIMITED": "سرور مقصد درخواست کاهش سرعت دریافت را داده است. بروزرسانی به‌طور خودکار متوقف شد و بعداً قابل ادامه است.",
        "ACCESS_RESTRICTED": "دسترسی آنلاین موقتاً توسط سرور مقصد محدود شده است. عملیات با ایمنی متوقف شد.",
        "BACKUP_SUCCESS": "نسخه پشتیبان تاییدشده از آرشیو با موفقیت ایجاد شد.",
        "BACKUP_RESTORE_SUCCESS": "آرشیو با موفقیت از فایل پشتیبان انتخابی بازیابی شد.",
        "BACKUP_INVALID": "فایل پشتیبان انتخابی معتبر نبود و بازیابی انجام نشد.",
        "EXPORT_SUCCESS": "گزارش شما با موفقیت استخراج و در پوشه خروجی ذخیره شد.",
        "COLLECTION_INTERRUPTED": "بروزرسانی متوقف شد. پیشرفت کار ذخیره شده و هر زمان قابل ادامه است.",
        "GENERIC_ERROR": "عملیات تکمیل نشد. جزئیات فنی در گزارش مدیر سیستم ثبت گردید.",
    }
    table = messages_fa if lang == "fa" else messages_en
    return table.get(error_code, table["GENERIC_ERROR"])


def read_diagnostic_logs(logs_dir: Path, max_lines: int = 200) -> list[str]:
    """Read the latest lines of the technical diagnostic log for the Administrator view."""
    log_file = logs_dir / "diagnostic.log"
    if not log_file.exists():
        return []
    lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-max_lines:]
