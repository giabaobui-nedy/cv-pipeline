"""
models.py — shared data structures for the job fetching pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class JobListing:
    """Normalised output schema produced by every JobFetcher implementation."""

    title: str
    company: str
    location: str
    description: str
    url: str
    # "seek" | "linkedin" | "indeed"
    source: str

    salary: str | None = None
    # "full-time" | "part-time" | "contract"
    work_type: str | None = None
    date_posted: str | None = None

    # None  → unknown / not checked yet
    # True  → description suggests the role is open to visa holders
    # False → description explicitly restricts to citizens / PR holders
    visa_eligible: bool | None = None

    # True if the employer explicitly offers visa sponsorship
    sponsorship_available: bool | None = None

    def __repr__(self) -> str:
        return (
            f"JobListing({self.source!r}: {self.title!r} @ {self.company!r}, "
            f"visa_eligible={self.visa_eligible}, "
            f"sponsorship_available={self.sponsorship_available})"
        )


@dataclass
class JobStub:
    """Lightweight summary extracted from a search results page.

    Contains enough information to triage a listing (title, company, visa
    signal, salary) without fetching the full job description.  Call
    ``JobFetcherRouter().fetch(stub.url)`` to upgrade to a full ``JobListing``.
    """

    title: str
    company: str
    location: str
    url: str
    # "seek" | "linkedin" | "indeed"
    source: str

    salary: str | None = None
    work_type: str | None = None
    date_listed: str | None = None
    description_preview: str | None = None

    # Scanned from the short preview text — may be None until full fetch.
    visa_eligible: bool | None = None
    sponsorship_available: bool | None = None

    is_featured: bool = False

    def __repr__(self) -> str:
        return (
            f"JobStub({self.source!r}: {self.title!r} @ {self.company!r}, "
            f"visa_eligible={self.visa_eligible})"
        )


class JobFetchError(Exception):
    """Raised by any JobFetcher when a fetch or parse step fails.

    Carries a human-readable ``message`` and an optional ``url`` so callers
    can surface exactly which listing caused the problem.
    """

    def __init__(self, message: str, url: str = "") -> None:
        super().__init__(message)
        self.url = url

    def __str__(self) -> str:
        if self.url:
            return f"{super().__str__()} (url={self.url!r})"
        return super().__str__()
