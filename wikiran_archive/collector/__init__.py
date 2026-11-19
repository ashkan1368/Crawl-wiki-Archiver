"""Collector package initialization."""

from .discovery import DiscoveryResult, extract_discovered_links, parse_robots_txt
from .engine import CollectionEngine, PoliteHttpFetcher
from .extractor import (
    ExtractedArticle,
    ExtractedPublicationCatalogue,
    extract_article_from_html,
    extract_catalogue_cards_from_leaks_index,
    extract_publication_catalogue_from_html,
)
from .normalizer import classify_categories_from_text, normalize_date, normalize_url
from .safety import is_permitted_research_url, sanitize_public_text
from .scheduler import ScheduleConfig, ScheduledCollectionRunner, compute_next_run_iso

__all__ = [
    "CollectionEngine",
    "DiscoveryResult",
    "ExtractedArticle",
    "ExtractedPublicationCatalogue",
    "PoliteHttpFetcher",
    "ScheduleConfig",
    "ScheduledCollectionRunner",
    "classify_categories_from_text",
    "compute_next_run_iso",
    "extract_article_from_html",
    "extract_catalogue_cards_from_leaks_index",
    "extract_discovered_links",
    "extract_publication_catalogue_from_html",
    "is_permitted_research_url",
    "normalize_date",
    "normalize_url",
    "parse_robots_txt",
    "sanitize_public_text",
]
