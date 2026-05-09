"""
router.py — auto-detects the job board from a URL and delegates to the right
            JobFetcher implementation.

Extensibility
-------------
To add a new source, create a concrete JobFetcher subclass in fetchers/ and
append an instance to ``JobFetcherRouter.FETCHERS``.  No other file needs
to change — the router picks it up automatically.
"""

from __future__ import annotations

from .base import JobFetcher
from .fetchers.indeed import IndeedFetcher
from .fetchers.linkedin import LinkedInFetcher
from .fetchers.seek import SeekFetcher
from .models import JobFetchError, JobListing


class JobFetcherRouter:
    """Selects the appropriate fetcher for a given URL and runs it.

    Usage
    -----
    >>> router = JobFetcherRouter()
    >>> listing = router.fetch("https://www.seek.com.au/job/12345678")
    """

    # Ordered list of registered fetchers.  ``can_handle`` is tested in order;
    # the first match wins.  Add new fetchers here — no other code changes needed.
    FETCHERS: list[JobFetcher] = [
        SeekFetcher(),
        LinkedInFetcher(),
        IndeedFetcher(),
    ]

    def fetch(self, url: str) -> JobListing:
        """Route *url* to the correct fetcher and return a ``JobListing``.

        Raises
        ------
        JobFetchError
            If no registered fetcher can handle the URL, or if the matched
            fetcher encounters an error during the fetch.
        """
        fetcher = self._resolve(url)
        return fetcher.fetch(url)

    def _resolve(self, url: str) -> JobFetcher:
        """Return the first fetcher that claims to handle *url*."""
        for fetcher in self.FETCHERS:
            if fetcher.can_handle(url):
                return fetcher
        supported = ", ".join(
            type(f).__name__ for f in self.FETCHERS
        )
        raise JobFetchError(
            f"No fetcher registered for this URL. "
            f"Currently supported sources: {supported}.\n"
            f"URL: {url}",
            url=url,
        )

    def register(self, fetcher: JobFetcher) -> None:
        """Register a new fetcher at runtime.

        The new fetcher is prepended so it takes priority over existing ones
        (useful for overriding a source in tests or for specialised variants).
        """
        self.FETCHERS = [fetcher] + self.FETCHERS

    @property
    def supported_sources(self) -> list[str]:
        """Human-readable names of all registered fetchers."""
        return [type(f).__name__ for f in self.FETCHERS]
