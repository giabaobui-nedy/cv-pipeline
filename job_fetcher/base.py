"""
base.py — abstract base class that every concrete fetcher must implement.
"""

from __future__ import annotations

import random
import time
from abc import ABC, abstractmethod

from fake_useragent import UserAgent

from .models import JobListing

# Shared UserAgent pool — instantiated once so it can be reused across fetchers.
_UA = UserAgent()


def _random_headers() -> dict[str, str]:
    """Return a minimal browser-like header dict with a rotated User-Agent."""
    return {
        "User-Agent": _UA.random,
        "Accept-Language": "en-AU,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def _polite_delay(min_s: float = 1.0, max_s: float = 3.0) -> None:
    """Sleep for a random interval to avoid hammering servers."""
    time.sleep(random.uniform(min_s, max_s))


class JobFetcher(ABC):
    """Strategy interface — implement one concrete subclass per job board."""

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return True if this fetcher knows how to scrape the given URL."""

    @abstractmethod
    def fetch(self, url: str) -> JobListing:
        """Fetch the job listing at *url* and return a populated JobListing.

        Implementations must:
        - Call ``_polite_delay()`` before each HTTP request.
        - Use ``_random_headers()`` on every request session.
        - Raise ``JobFetchError`` (not raw exceptions) for all recoverable
          failures, with a clear, human-readable message.
        """

    # Make the helpers available on subclasses as protected methods.
    _random_headers = staticmethod(_random_headers)
    _polite_delay = staticmethod(_polite_delay)
