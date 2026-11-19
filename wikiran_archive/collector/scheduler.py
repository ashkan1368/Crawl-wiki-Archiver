"""
Background task runner and scheduled collection coordinator for WikIran Archive.
Allows defining recurring intervals (e.g., daily at 02:00, weekly on Sunday, or every 6/12 hours)
for the incremental archive update service, computing next execution times, and executing
non-blocking background collection updates.
"""

from __future__ import annotations

import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from ..database.connection import get_connection
from ..database.repository import ArchiveRepository, utc_now_iso
from .engine import CollectionEngine

WEEKDAY_MAP: dict[str, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


@dataclass
class ScheduleConfig:
    """Configuration state for the Scheduled Collection background task runner."""

    enabled: bool
    frequency: str  # 'daily', 'weekly', 'every_6h', 'every_12h'
    time_utc: str  # 'HH:MM', e.g., '02:00'
    day_of_week: str  # 'monday' .. 'sunday'
    max_items_per_run: int
    last_run_at: str
    next_run_at: str
    runner_status: str


def compute_next_run_iso(
    frequency: str,
    time_utc: str = "02:00",
    day_of_week: str = "sunday",
    now: datetime | None = None,
) -> str:
    """Compute the next scheduled UTC timestamp based on interval rules."""
    ref = now or datetime.now(timezone.utc)
    try:
        parts = time_utc.strip().split(":")
        target_hour = max(0, min(23, int(parts[0])))
        target_minute = max(0, min(59, int(parts[1]))) if len(parts) > 1 else 0
    except Exception:
        target_hour, target_minute = 2, 0

    freq = (frequency or "daily").lower()
    if freq == "every_6h":
        nxt = ref + timedelta(hours=6)
        return nxt.strftime("%Y-%m-%dT%H:%M:%SZ")
    if freq == "every_12h":
        nxt = ref + timedelta(hours=12)
        return nxt.strftime("%Y-%m-%dT%H:%M:%SZ")

    candidate = ref.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    if freq == "weekly":
        target_wd = WEEKDAY_MAP.get(day_of_week.lower(), 6)
        days_ahead = (target_wd - ref.weekday()) % 7
        candidate = candidate + timedelta(days=days_ahead)
        if candidate <= ref:
            candidate = candidate + timedelta(days=7)
        return candidate.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Default: daily at HH:MM
    if candidate <= ref:
        candidate = candidate + timedelta(days=1)
    return candidate.strftime("%Y-%m-%dT%H:%M:%SZ")


class ScheduledCollectionRunner:
    """
    Manages the Scheduled Collection configuration and background thread execution
    for periodic incremental archive updates.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = str(db_path)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._is_executing = False

    def get_schedule_config(self, repo: ArchiveRepository | None = None) -> ScheduleConfig:
        own_conn = None
        if repo is None:
            own_conn = get_connection(self.db_path)
            repo = ArchiveRepository(own_conn)
        try:
            s = repo.get_settings()
            enabled = s.get("schedule_enabled", "true").lower() == "true"
            frequency = s.get("schedule_frequency", "daily")
            time_utc = s.get("schedule_time_utc", "02:00")
            day_of_week = s.get("schedule_day_of_week", "sunday")
            max_items = int(s.get("schedule_max_items", "6") or "6")
            last_run_at = s.get("schedule_last_run_at", "2026-11-18T02:00:00Z")
            next_run_at = (
                compute_next_run_iso(frequency, time_utc, day_of_week)
                if enabled
                else "Paused (Schedule Disabled)"
            )
            status = (
                "RUNNING_UPDATE"
                if self._is_executing
                else ("ACTIVE_IDLE" if enabled else "PAUSED")
            )
            return ScheduleConfig(
                enabled=enabled,
                frequency=frequency,
                time_utc=time_utc,
                day_of_week=day_of_week,
                max_items_per_run=max_items,
                last_run_at=last_run_at,
                next_run_at=next_run_at,
                runner_status=status,
            )
        finally:
            if own_conn is not None:
                own_conn.close()

    def update_schedule_config(
        self,
        *,
        enabled: bool | None = None,
        frequency: str | None = None,
        time_utc: str | None = None,
        day_of_week: str | None = None,
        max_items_per_run: int | None = None,
        repo: ArchiveRepository | None = None,
    ) -> dict[str, Any]:
        own_conn = None
        if repo is None:
            own_conn = get_connection(self.db_path)
            repo = ArchiveRepository(own_conn)
        try:
            if enabled is not None:
                repo.set_setting("schedule_enabled", "true" if enabled else "false")
            if frequency is not None:
                repo.set_setting("schedule_frequency", frequency)
            if time_utc is not None:
                repo.set_setting("schedule_time_utc", time_utc)
            if day_of_week is not None:
                repo.set_setting("schedule_day_of_week", day_of_week)
            if max_items_per_run is not None:
                repo.set_setting("schedule_max_items", str(max(1, int(max_items_per_run))))
            cfg = self.get_schedule_config(repo)
            return asdict(cfg)
        finally:
            if own_conn is not None:
                own_conn.close()

    def trigger_scheduled_run_now(
        self,
        fetcher: Callable[[str], tuple[int, str]] | None = None,
    ) -> dict[str, Any]:
        """Execute a scheduled incremental update run and record its completion timestamp."""
        self._is_executing = True
        conn = get_connection(self.db_path)
        try:
            repo = ArchiveRepository(conn)
            cfg = self.get_schedule_config(repo)
            engine = CollectionEngine(repo, fetcher=fetcher)
            job_summary = engine.run_incremental_update(max_items=cfg.max_items_per_run)
            now_str = utc_now_iso()
            repo.set_setting("schedule_last_run_at", now_str)
            updated_cfg = self.get_schedule_config(repo)
            return {
                "schedule": asdict(updated_cfg),
                "job": job_summary,
            }
        finally:
            self._is_executing = False
            conn.close()
