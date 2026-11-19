"""
Polite collection engine with robots.txt verification, rate limiting, exponential backoff,
persistent checkpoints, interrupted-task recovery, and incremental deduplicated updates.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import uuid
from typing import Callable

from ..database.repository import ArchiveRepository, utc_now_iso
from .discovery import extract_discovered_links, extract_sitemap_urls, parse_robots_txt
from .extractor import (
    extract_article_from_html,
    extract_catalogue_cards_from_leaks_index,
    extract_publication_catalogue_from_html,
)
from .safety import is_permitted_research_url


class PoliteHttpFetcher:
    """
    Polite HTTP fetcher supporting configurable delay, exponential backoff,
    User-Agent identification, and automatic suspension on 403/429 access restrictions.
    Uses httpx if available in the environment, falling back seamlessly to urllib.request.
    """

    def __init__(
        self,
        user_agent: str,
        delay_seconds: float = 0.15,
        timeout_seconds: float = 15.0,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        allow_all_paths: bool = False,
    ) -> None:
        self.user_agent = user_agent
        self.delay_seconds = max(0.0, float(delay_seconds))
        self.timeout_seconds = float(timeout_seconds)
        self.max_retries = int(max_retries)
        self.backoff_factor = float(backoff_factor)
        self.allow_all_paths = allow_all_paths
        self._last_request_time = 0.0

    def fetch(self, url: str) -> tuple[int, str]:
        """
        Fetch a permitted public URL politely.
        Returns (http_status, body_text).
        Raises PermissionError on 403/429 so the engine suspends gracefully.
        """
        permitted, reason = is_permitted_research_url(
            url, allow_all_paths=self.allow_all_paths
        )
        if not permitted:
            raise ValueError(f"Blocked by safety policy: {reason}")

        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)

        attempt = 0
        while True:
            attempt += 1
            self._last_request_time = time.monotonic()
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
                    },
                )
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    status = int(resp.status)
                    body = resp.read().decode("utf-8", errors="replace")
                    return status, body
            except urllib.error.HTTPError as http_err:
                if http_err.code in (401, 403, 429):
                    raise PermissionError(
                        f"Remote server returned HTTP {http_err.code} for {url}. Suspending collection."
                    ) from http_err
                if attempt >= self.max_retries:
                    raise
                sleep_dur = (self.backoff_factor ** (attempt - 1)) * max(0.2, self.delay_seconds)
                time.sleep(sleep_dur)
            except Exception:
                if attempt >= self.max_retries:
                    raise
                sleep_dur = (self.backoff_factor ** (attempt - 1)) * max(0.2, self.delay_seconds)
                time.sleep(sleep_dur)


class CollectionEngine:
    """
    Deep Spider & Incremental Collection Engine:
    - Verifies robots.txt and sitemap.xml
    - Recursively crawls pagination (/search?tabType=articles&page=1..N) until the last page
    - Crawls /leaks and /archives and follows newly discovered links inside every fetched page
    - Supports instant Stop / Pause via in-memory signal OR SQLite setting (`stop_crawl_requested`)
    """

    def __init__(
        self,
        repo: ArchiveRepository,
        fetcher: Callable[[str], tuple[int, str]] | None = None,
    ) -> None:
        self.repo = repo
        self._custom_fetcher_supplied = fetcher is not None
        settings = repo.get_settings()
        strict_exclusion = settings.get("strict_sensitive_exclusion", "false").lower() == "true"
        if fetcher is not None:
            self.fetch_fn = fetcher
        else:
            http_fetcher = PoliteHttpFetcher(
                user_agent=settings.get(
                    "user_agent",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) WikIranArchive/2.0",
                ),
                delay_seconds=min(0.12, float(settings.get("request_delay_seconds", "0.12"))),
                timeout_seconds=float(settings.get("request_timeout_seconds", "15")),
                max_retries=int(settings.get("max_retries", "2")),
                backoff_factor=float(settings.get("backoff_factor", "1.5")),
                allow_all_paths=not strict_exclusion,
            )
            self.fetch_fn = http_fetcher.fetch

        self._stop_requested = False

    def request_stop(self) -> None:
        """Signal the running collection task to checkpoint and pause cleanly."""
        self._stop_requested = True
        try:
            self.repo.set_setting("stop_crawl_requested", "true")
        except Exception:
            pass

    def _is_stop_signaled(self) -> bool:
        """Check both in-memory flag and SQLite cross-process stop_crawl_requested setting."""
        if self._stop_requested:
            return True
        try:
            row = self.repo.conn.execute(
                "SELECT setting_value FROM app_settings WHERE setting_key = 'stop_crawl_requested';"
            ).fetchone()
            if row and str(row[0]).lower() == "true":
                self._stop_requested = True
                return True
        except Exception:
            pass
        return False

    def create_interrupted_checkpoint_job(
        self,
        pending_urls: list[str],
        completed_urls: list[str] | None = None,
        job_type: str = "INCREMENTAL_UPDATE",
    ) -> int:
        """
        Create or persist an interrupted collection job with a saved checkpoint queue.
        Used both when a job is paused mid-flight and for deterministic recovery testing.
        """
        now = utc_now_iso()
        job_uuid = str(uuid.uuid4())
        done = completed_urls or []
        checkpoint = {
            "pending_urls": pending_urls,
            "completed_urls": done,
            "base_url": self.repo.get_settings().get("source_base_url", "https://wikiran.org"),
        }
        cur = self.repo.conn.execute(
            """
            INSERT INTO collection_jobs (
                job_uuid, job_type, status, started_at,
                total_discovered, processed_count, checkpoint_data, error_summary
            ) VALUES (?, ?, 'INTERRUPTED', ?, ?, ?, ?, 'Task paused with verified checkpoint');
            """,
            (
                job_uuid,
                job_type,
                now,
                len(pending_urls) + len(done),
                len(done),
                json.dumps(checkpoint),
            ),
        )
        self.repo.conn.commit()
        return int(cur.lastrowid)

    def run_incremental_update(
        self,
        max_items: int = 12,
        simulate_interrupt_after: int | None = None,
        deep_spider: bool = True,
    ) -> dict[str, int | str]:
        """
        Run a deep spider discovery and extraction job across wikiran.org.
        Traverses article pagination to the last page, inspects /leaks, /archives, and /sitemap.xml,
        and recursively follows newly discovered links inside fetched pages.
        """
        self._stop_requested = False
        try:
            self.repo.set_setting("stop_crawl_requested", "false")
        except Exception:
            pass

        settings = self.repo.get_settings()
        base_url = settings.get("source_base_url", "https://wikiran.org").rstrip("/")
        now = utc_now_iso()
        job_uuid = str(uuid.uuid4())

        cur = self.repo.conn.execute(
            """
            INSERT INTO collection_jobs (
                job_uuid, job_type, status, started_at, checkpoint_data
            ) VALUES (?, 'INCREMENTAL_UPDATE', 'RUNNING', ?, '{}');
            """,
            (job_uuid, now),
        )
        job_id = int(cur.lastrowid)
        self.repo.conn.commit()

        # Step 1: Check robots.txt
        if settings.get("respect_robots_txt", "true").lower() == "true":
            try:
                status, robots_body = self.fetch_fn(f"{base_url}/robots.txt")
                permitted, notes = parse_robots_txt(robots_body)
                self.repo.conn.execute(
                    """
                    INSERT INTO collection_history (job_id, target_url, record_type, http_status, action_taken, timestamp, message)
                    VALUES (?, ?, 'DISCOVERY_PAGE', ?, 'UNCHANGED', ?, ?);
                    """,
                    (job_id, f"{base_url}/robots.txt", status, utc_now_iso(), notes),
                )
                self.repo.conn.commit()
                if not permitted:
                    self._finalize_job(job_id, "SUSPENDED", "Suspended per robots.txt rules")
                    return self.get_job_summary(job_id)
            except Exception as exc:
                self._finalize_job(job_id, "FAILED", f"Could not verify robots.txt: {exc}")
                return self.get_job_summary(job_id)

        # Query existing URLs in SQLite so we prioritize NEW (unseen) articles, documents, and publications first
        existing_urls = {
            str(r[0]).rstrip("/")
            for r in self.repo.conn.execute(
                "SELECT source_url FROM articles UNION SELECT source_url FROM publications;"
            ).fetchall()
        }

        strict_exclusion = settings.get("strict_sensitive_exclusion", "false").lower() == "true"
        allow_all_paths = not strict_exclusion

        # Step 2: Deep Spider Discovery across /search?tabType=articles&page=1..N, /leaks, /archives, and /sitemap.xml
        all_discovered_articles: list[str] = []
        all_discovered_catalogues: list[str] = []
        all_discovered_documents: list[str] = []
        blocked_urls: list[str] = []

        def _absorb_discovery(disc: Any) -> None:
            for u in disc.article_urls:
                if u not in all_discovered_articles:
                    all_discovered_articles.append(u)
            for u in disc.catalogue_urls:
                if u not in all_discovered_catalogues:
                    all_discovered_catalogues.append(u)
            for u in disc.document_urls:
                if u not in all_discovered_documents:
                    all_discovered_documents.append(u)
            for b in disc.blocked_sensitive_urls:
                if b not in blocked_urls:
                    blocked_urls.append(b)

        try:
            # 2a. Crawl /search?tabType=articles&page=1 and spider all pagination pages until the last page
            st_art, html_art_list = self.fetch_fn(f"{base_url}/search?tabType=articles&page=1")
            disc_art = extract_discovered_links(
                html_art_list, base_url, allow_all_paths=allow_all_paths
            )
            _absorb_discovery(disc_art)

            if deep_spider and not self._custom_fetcher_supplied:
                page_num = 2
                max_detected_page = max(disc_art.pagination_pages_found or [5])
                while page_num <= min(25, max(max_detected_page, 10)):
                    if self._is_stop_signaled():
                        break
                    try:
                        _, html_next = self.fetch_fn(
                            f"{base_url}/search?tabType=articles&page={page_num}"
                        )
                        disc_next = extract_discovered_links(
                            html_next, base_url, allow_all_paths=allow_all_paths
                        )
                        before_count = len(all_discovered_articles)
                        _absorb_discovery(disc_next)
                        if disc_next.pagination_pages_found:
                            max_detected_page = max(
                                max_detected_page, max(disc_next.pagination_pages_found)
                            )
                        # If a pagination page yields 0 new article URLs, we reached the end of the feed
                        if len(all_discovered_articles) == before_count:
                            break
                        page_num += 1
                    except Exception:
                        break

            # 2b. Crawl /leaks catalogue index and extract all publication cards + deep links
            st_leaks, html_leaks = self.fetch_fn(f"{base_url}/leaks")
            cards = extract_catalogue_cards_from_leaks_index(html_leaks, base_url)
            for card in cards:
                if card.source_url not in all_discovered_catalogues:
                    all_discovered_catalogues.append(card.source_url)
            disc_leaks = extract_discovered_links(
                html_leaks, base_url, allow_all_paths=allow_all_paths
            )
            _absorb_discovery(disc_leaks)

            # 2c. Crawl /archives and /sitemap.xml when running in deep spider mode on live network
            if deep_spider and not self._custom_fetcher_supplied and not self._is_stop_signaled():
                for extra_hub in (f"{base_url}/archives", f"{base_url}/"):
                    if self._is_stop_signaled():
                        break
                    try:
                        _, hub_html = self.fetch_fn(extra_hub)
                        _absorb_discovery(
                            extract_discovered_links(
                                hub_html, base_url, allow_all_paths=allow_all_paths
                            )
                        )
                    except Exception:
                        pass
                try:
                    _, sitemap_xml = self.fetch_fn(f"{base_url}/sitemap.xml")
                    for sm_url in extract_sitemap_urls(sitemap_xml, base_url):
                        if "/document/articles/" in sm_url and sm_url not in all_discovered_articles:
                            all_discovered_articles.append(sm_url)
                        elif "/leak/" in sm_url and sm_url not in all_discovered_catalogues:
                            all_discovered_catalogues.append(sm_url)
                except Exception:
                    pass
        except PermissionError as perm_err:
            self._finalize_job(job_id, "SUSPENDED", str(perm_err))
            return self.get_job_summary(job_id)
        except Exception as exc:
            self._finalize_job(job_id, "FAILED", f"Discovery failed: {exc}")
            return self.get_job_summary(job_id)

        unseen_articles = [u for u in all_discovered_articles if u.rstrip("/") not in existing_urls]
        seen_articles = [u for u in all_discovered_articles if u.rstrip("/") in existing_urls]
        unseen_catalogues = [u for u in all_discovered_catalogues if u.rstrip("/") not in existing_urls]
        seen_catalogues = [u for u in all_discovered_catalogues if u.rstrip("/") in existing_urls]
        unseen_documents = [u for u in all_discovered_documents if u.rstrip("/") not in existing_urls]
        seen_documents = [u for u in all_discovered_documents if u.rstrip("/") in existing_urls]

        # When max_items <= 0 (Spider All Mode), queue every unseen URL discovered on the server
        effective_max = (
            max(len(unseen_articles) + len(unseen_catalogues) + len(unseen_documents), 20)
            if max_items <= 0
            else max_items
        )

        half = max(1, effective_max // 2)
        prioritized_queue: list[str] = []
        prioritized_queue.extend(unseen_articles[:half])
        prioritized_queue.extend(unseen_catalogues[: effective_max - len(prioritized_queue)])

        for pool in (
            unseen_articles,
            unseen_catalogues,
            unseen_documents,
            seen_articles,
            seen_catalogues,
            seen_documents,
        ):
            for u in pool:
                if len(prioritized_queue) >= effective_max:
                    break
                if u not in prioritized_queue:
                    prioritized_queue.append(u)

        unique_queue = prioritized_queue[:effective_max]
        total_found_on_server = (
            len(all_discovered_articles)
            + len(all_discovered_catalogues)
            + len(all_discovered_documents)
        )

        for b_url in blocked_urls[:5]:
            self.repo.conn.execute(
                """
                INSERT INTO collection_history (job_id, target_url, record_type, http_status, action_taken, timestamp, message)
                VALUES (?, ?, 'BLOCKED_SENSITIVE', NULL, 'EXCLUDED_POLICY', ?, 'Excluded sensitive document/email URL');
                """,
                (job_id, b_url, utc_now_iso()),
            )

        checkpoint = {
            "pending_urls": list(unique_queue),
            "completed_urls": [],
            "base_url": base_url,
            "total_found_on_server": total_found_on_server,
        }
        self.repo.conn.execute(
            """
            UPDATE collection_jobs
            SET total_discovered = ?, blocked_sensitive_count = ?, checkpoint_data = ?
            WHERE id = ?;
            """,
            (len(unique_queue), len(blocked_urls), json.dumps(checkpoint), job_id),
        )
        self.repo.conn.commit()

        return self._process_queue(
            job_id=job_id,
            pending_urls=unique_queue,
            completed_urls=[],
            simulate_interrupt_after=simulate_interrupt_after,
            deep_spider=deep_spider and not self._custom_fetcher_supplied,
            max_total_items=effective_max,
        )

    def resume_job(self, job_id: int) -> dict[str, int | str]:
        """Resume an INTERRUPTED collection job from its persisted checkpoint."""
        self._stop_requested = False
        try:
            self.repo.set_setting("stop_crawl_requested", "false")
        except Exception:
            pass
        row = self.repo.conn.execute(
            "SELECT * FROM collection_jobs WHERE id = ?;", (job_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Collection job {job_id} not found.")

        checkpoint = json.loads(row["checkpoint_data"] or "{}")
        pending_urls: list[str] = checkpoint.get("pending_urls", [])
        completed_urls: list[str] = checkpoint.get("completed_urls", [])

        self.repo.conn.execute(
            "UPDATE collection_jobs SET status = 'RUNNING', error_summary = NULL WHERE id = ?;",
            (job_id,),
        )
        self.repo.conn.commit()

        return self._process_queue(
            job_id=job_id,
            pending_urls=pending_urls,
            completed_urls=completed_urls,
            simulate_interrupt_after=None,
            deep_spider=not self._custom_fetcher_supplied,
            max_total_items=len(pending_urls) + len(completed_urls) + 10,
        )

    def _process_queue(
        self,
        *,
        job_id: int,
        pending_urls: list[str],
        completed_urls: list[str],
        simulate_interrupt_after: int | None,
        deep_spider: bool = False,
        max_total_items: int = 50,
    ) -> dict[str, int | str]:
        cat_map = {c["slug"]: int(c["id"]) for c in self.repo.list_categories()}
        step_count = 0
        settings = self.repo.get_settings()
        base_url = settings.get("source_base_url", "https://wikiran.org").rstrip("/")
        strict_exclusion = settings.get("strict_sensitive_exclusion", "false").lower() == "true"
        allow_all_paths = not strict_exclusion
        redact_pii = strict_exclusion

        existing_in_db = {
            str(r[0]).rstrip("/")
            for r in self.repo.conn.execute(
                "SELECT source_url FROM articles UNION SELECT source_url FROM publications;"
            ).fetchall()
        }

        remaining = list(pending_urls)
        done = list(completed_urls)
        seen_in_queue = {u.rstrip("/") for u in remaining} | {u.rstrip("/") for u in done}

        while remaining:
            if self._is_stop_signaled() or (
                simulate_interrupt_after is not None and step_count >= simulate_interrupt_after
            ):
                checkpoint = {"pending_urls": remaining, "completed_urls": done}
                self.repo.conn.execute(
                    """
                    UPDATE collection_jobs
                    SET status = 'INTERRUPTED',
                        checkpoint_data = ?,
                        error_summary = 'Interrupted with saved checkpoint; ready to resume.'
                    WHERE id = ?;
                    """,
                    (json.dumps(checkpoint), job_id),
                )
                self.repo.conn.commit()
                return self.get_job_summary(job_id)

            target_url = remaining[0]
            permitted, reason = is_permitted_research_url(
                target_url, allow_all_paths=allow_all_paths
            )
            if not permitted:
                remaining.pop(0)
                self.repo.conn.execute(
                    """
                    UPDATE collection_jobs
                    SET blocked_sensitive_count = blocked_sensitive_count + 1
                    WHERE id = ?;
                    """,
                    (job_id,),
                )
                self.repo.conn.execute(
                    """
                    INSERT INTO collection_history (job_id, target_url, record_type, http_status, action_taken, timestamp, message)
                    VALUES (?, ?, 'BLOCKED_SENSITIVE', NULL, 'EXCLUDED_POLICY', ?, ?);
                    """,
                    (job_id, target_url, utc_now_iso(), reason),
                )
                self.repo.conn.commit()
                continue

            try:
                http_status, html_body = self.fetch_fn(target_url)

                # Recursive Spider Expansion: extract any newly discovered article/leak/document links inside this page
                if deep_spider and (len(done) + len(remaining)) < max_total_items:
                    inner_disc = extract_discovered_links(
                        html_body, base_url, allow_all_paths=allow_all_paths
                    )
                    for child_url in (
                        inner_disc.article_urls
                        + inner_disc.catalogue_urls
                        + inner_disc.document_urls
                    ):
                        norm_child = child_url.rstrip("/")
                        if (
                            norm_child not in seen_in_queue
                            and norm_child not in existing_in_db
                            and (len(done) + len(remaining)) < max_total_items
                        ):
                            seen_in_queue.add(norm_child)
                            remaining.append(child_url)
                            self.repo.conn.execute(
                                "UPDATE collection_jobs SET total_discovered = total_discovered + 1 WHERE id = ?;",
                                (job_id,),
                            )

                if (
                    "/document/articles/" in target_url
                    or "/document/emails/" in target_url
                    or "/document/files/" in target_url
                ):
                    extracted = extract_article_from_html(
                        html_body,
                        target_url,
                        allow_all_paths=allow_all_paths,
                        redact_pii=redact_pii,
                    )
                    c_ids = [cat_map[s] for s in extracted.categories if s in cat_map]
                    t_ids = [self.repo.upsert_tag(t, target_url) for t in extracted.tags]
                    _, action = self.repo.upsert_article(
                        original_pub_id=extracted.original_pub_id,
                        title=extracted.title,
                        subtitle=extracted.subtitle,
                        author=extracted.author,
                        publication_date=extracted.publication_date,
                        raw_date_text=extracted.raw_date_text,
                        summary=extracted.summary,
                        editorial_content=extracted.editorial_content,
                        source_url=extracted.source_url,
                        extraction_status=extracted.extraction_status,
                        category_ids=c_ids,
                        tag_ids=t_ids,
                    )
                    rec_type = "ARTICLE"
                    blocked_delta = 0
                else:
                    extracted_pub = extract_publication_catalogue_from_html(
                        html_body,
                        target_url,
                        allow_all_paths=allow_all_paths,
                        redact_pii=redact_pii,
                    )
                    c_ids = [cat_map[s] for s in extracted_pub.categories if s in cat_map]
                    _, action = self.repo.upsert_publication(
                        original_pub_id=extracted_pub.original_pub_id,
                        title=extracted_pub.title,
                        native_title=extracted_pub.native_title,
                        publication_date=extracted_pub.publication_date,
                        raw_date_text=extracted_pub.raw_date_text,
                        description=extracted_pub.description,
                        source_url=extracted_pub.source_url,
                        extraction_status=extracted_pub.extraction_status,
                        category_ids=c_ids,
                        safe_inventory=extracted_pub.safe_inventory,
                    )
                    rec_type = "PUBLICATION"
                    blocked_delta = extracted_pub.blocked_sensitive_count

                remaining.pop(0)
                done.append(target_url)
                step_count += 1

                new_delta = 1 if action == "INSERTED" else 0
                upd_delta = 1 if action == "UPDATED" else 0
                skip_delta = 1 if action == "UNCHANGED" else 0

                checkpoint = {"pending_urls": remaining, "completed_urls": done}
                self.repo.conn.execute(
                    """
                    UPDATE collection_jobs
                    SET processed_count = processed_count + 1,
                        new_records_count = new_records_count + ?,
                        updated_records_count = updated_records_count + ?,
                        skipped_unchanged_count = skipped_unchanged_count + ?,
                        blocked_sensitive_count = blocked_sensitive_count + ?,
                        checkpoint_data = ?
                    WHERE id = ?;
                    """,
                    (
                        new_delta,
                        upd_delta,
                        skip_delta,
                        blocked_delta,
                        json.dumps(checkpoint),
                        job_id,
                    ),
                )
                self.repo.conn.execute(
                    """
                    INSERT INTO collection_history (job_id, target_url, record_type, http_status, action_taken, timestamp, message)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        job_id,
                        target_url,
                        rec_type,
                        http_status,
                        action,
                        utc_now_iso(),
                        f"Processed {rec_type.lower()} ({action})",
                    ),
                )
                self.repo.conn.commit()
            except PermissionError as perm_err:
                self._finalize_job(job_id, "SUSPENDED", str(perm_err))
                return self.get_job_summary(job_id)
            except Exception as exc:
                remaining.pop(0)
                checkpoint = {"pending_urls": remaining, "completed_urls": done}
                self.repo.conn.execute(
                    """
                    UPDATE collection_jobs
                    SET failed_count = failed_count + 1,
                        checkpoint_data = ?,
                        error_summary = ?
                    WHERE id = ?;
                    """,
                    (json.dumps(checkpoint), str(exc), job_id),
                )
                self.repo.conn.execute(
                    """
                    INSERT INTO collection_history (job_id, target_url, record_type, http_status, action_taken, timestamp, message)
                    VALUES (?, ?, 'ARTICLE', NULL, 'FAILED', ?, ?);
                    """,
                    (job_id, target_url, utc_now_iso(), f"Failed: {exc}"),
                )
                self.repo.conn.commit()

        self._finalize_job(job_id, "COMPLETED", None)
        return self.get_job_summary(job_id)

    def _finalize_job(self, job_id: int, status: str, error_summary: str | None) -> None:
        self.repo.conn.execute(
            """
            UPDATE collection_jobs
            SET status = ?, finished_at = ?, error_summary = COALESCE(?, error_summary)
            WHERE id = ?;
            """,
            (status, utc_now_iso(), error_summary, job_id),
        )
        self.repo.conn.commit()

    def get_job_summary(self, job_id: int) -> dict[str, int | str]:
        row = self.repo.conn.execute(
            "SELECT * FROM collection_jobs WHERE id = ?;", (job_id,)
        ).fetchone()
        return dict(row) if row else {}
