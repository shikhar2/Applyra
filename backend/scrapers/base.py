"""Base scraper interface with adaptive rate limiting."""
import asyncio
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger


@dataclass
class ScrapedJob:
    external_id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    apply_url: str
    source: str
    easy_apply: bool = False
    remote: bool = False
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    job_type: str = "full-time"
    experience_level: str = ""
    posted_at: Optional[datetime] = None
    extra_data: Dict = field(default_factory=dict)


class RateLimiter:
    """
    Adaptive rate limiter per domain.
    Backs off exponentially on HTTP 429 / 403 / connection errors.
    Resets to base delay after a successful request.
    """

    def __init__(self, base_delay: float = 2.0, max_delay: float = 60.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._current_delay = base_delay
        self._consecutive_errors = 0
        self._last_request_time: float = 0.0

    async def wait(self):
        """Wait the appropriate amount before the next request."""
        elapsed = time.monotonic() - self._last_request_time
        wait_for = self._current_delay - elapsed
        if wait_for > 0:
            # Add jitter (±20%) so requests don't arrive in lockstep
            jitter = wait_for * random.uniform(-0.2, 0.2)
            await asyncio.sleep(wait_for + jitter)
        self._last_request_time = time.monotonic()

    def success(self):
        """Call after a successful request — resets backoff."""
        self._consecutive_errors = 0
        self._current_delay = self.base_delay

    def failure(self, status_code: int = 0):
        """Call after a rate-limit or server error — doubles delay up to max."""
        self._consecutive_errors += 1
        if status_code in (429, 403, 503):
            # Hard rate-limit: back off aggressively
            self._current_delay = min(self._current_delay * 2.5, self.max_delay)
            logger.warning(
                f"Rate limited (HTTP {status_code}). "
                f"Backing off to {self._current_delay:.1f}s"
            )
        else:
            self._current_delay = min(self._current_delay * 1.5, self.max_delay)

    @property
    def is_blocked(self) -> bool:
        """True when we've hit the max delay — caller should stop and retry later."""
        return self._consecutive_errors >= 5 and self._current_delay >= self.max_delay


class BaseScraper(ABC):
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.rate_limiter = RateLimiter(
            base_delay=float(self.config.get("delay", 2.0)),
            max_delay=float(self.config.get("max_delay", 60.0)),
        )

    @abstractmethod
    async def search_jobs(
        self, query: str, location: str = "Remote", max_results: int = 50, days: int = 7
    ) -> List[ScrapedJob]:
        pass

    @abstractmethod
    async def get_job_details(self, job_url: str) -> Dict[str, Any]:
        pass

    def normalize_location(self, location: str) -> tuple[bool, str]:
        """Returns (is_remote, normalized_location)."""
        loc_lower = (location or "").lower()
        remote_kw = ["remote", "work from home", "wfh", "anywhere", "distributed"]
        is_remote = any(k in loc_lower for k in remote_kw)
        return is_remote, location

    async def _safe_get(self, client, url: str, **kwargs):
        """
        httpx GET with adaptive rate limiting.
        Returns the response, or raises on persistent failure.
        """
        await self.rate_limiter.wait()
        try:
            resp = await client.get(url, **kwargs)
            if resp.status_code >= 400:
                self.rate_limiter.failure(resp.status_code)
                if resp.status_code in (429, 503):
                    await asyncio.sleep(self.rate_limiter._current_delay)
            else:
                self.rate_limiter.success()
            return resp
        except Exception as e:
            self.rate_limiter.failure(0)
            raise
