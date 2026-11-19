"""
Bilingual translation dictionary and RTL/LTR layout configuration for
Persian (fa) and English (en) interfaces.
"""

from __future__ import annotations

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "WikIran Archive",
        "app_subtitle": "Local Public Research Archive & Publication Catalogue",
        "nav_dashboard": "Dashboard",
        "nav_search": "Search Archive",
        "nav_articles": "Articles",
        "nav_publications": "Publication Catalogue",
        "nav_organizations": "Organizations",
        "nav_categories": "Categories",
        "nav_exports": "Export Reports",
        "nav_history": "Collection History",
        "nav_settings": "Settings",
        "nav_help": "Help",
        "action_search_archive": "Search Archive",
        "action_browse_articles": "Browse Articles",
        "action_browse_catalogue": "Browse Catalogue",
        "action_update_archive": "Update Archive",
        "action_export_excel": "Export to Excel",
        "action_create_backup": "Create Backup",
        "action_help": "Help",
        "mode_clerk": "Clerk Workspace",
        "mode_admin": "Administrator Console",
        "stat_articles": "Indexed Public Articles",
        "stat_publications": "Publication Catalogues",
        "stat_organizations": "Public Organizations",
        "stat_categories": "Research Categories",
        "safety_banner": "Public Research Scope Active: Private correspondence, banking records, and personal identifiers are strictly excluded.",
        "direction": "LTR",
    },
    "fa": {
        "app_title": "آرشیو ویکی‌ایران",
        "app_subtitle": "سامانه محلی آرشیو پژوهش‌های عمومی و فهرست انتشارات",
        "nav_dashboard": "پیشخوان",
        "nav_search": "جستجو در آرشیو",
        "nav_articles": "مقالات تحلیلی",
        "nav_publications": "فهرست انتشارات",
        "nav_organizations": "سازمان‌ها و نهادها",
        "nav_categories": "دسته‌بندی‌های موضوعی",
        "nav_exports": "گزارش‌گیری و خروجی",
        "nav_history": "تاریخچه بروزرسانی",
        "nav_settings": "تنظیمات",
        "nav_help": "راهنمای کاربری",
        "action_search_archive": "جستجو در آرشیو",
        "action_browse_articles": "مشاهده مقالات",
        "action_browse_catalogue": "مشاهده فهرست انتشارات",
        "action_update_archive": "بروزرسانی آرشیو",
        "action_export_excel": "خروجی اکسل (Excel)",
        "action_create_backup": "تهیه نسخه پشتیبان",
        "action_help": "راهنما",
        "mode_clerk": "میز کار متصدی (ساده)",
        "mode_admin": "پنل مدیریت سامانه",
        "stat_articles": "مقالات عمومی ثبت‌شده",
        "stat_publications": "فهرست‌های انتشارات",
        "stat_organizations": "سازمان‌ها و نهادهای عمومی",
        "stat_categories": "دسته‌بندی‌های پژوهشی",
        "safety_banner": "حریم پژوهش عمومی فعال است: مکاتبات خصوصی، اسناد بانکی، مدارک هویتی و اطلاعات شخصی افراد به‌طور کامل حذف شده‌اند.",
        "direction": "RTL",
    },
}


def tr(key: str, lang: str = "en") -> str:
    """Translate a UI label into the active language ('en' or 'fa')."""
    normalized_lang = "fa" if lang == "fa" else "en"
    return TRANSLATIONS[normalized_lang].get(key, TRANSLATIONS["en"].get(key, key))


def is_rtl_language(lang: str) -> bool:
    """Return True if the selected language requires Right-to-Left (RTL) layout."""
    return lang == "fa"
