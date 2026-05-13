"""
fetchers/seek_search.py — scraper for SEEK search results pages.

Parses a SEEK search URL (e.g. /Junior-Software-Engineer-jobs/in-All-Melbourne-VIC)
and returns a list of ``JobStub`` objects — one per card on the page.

SEEK search pages are server-side rendered and embed a ``window.SEEK_REDUX_DATA``
JSON blob that contains the full job listing metadata (including job IDs) for all
cards on the current page.  We extract this blob rather than fighting fragile
CSS selectors.

Usage
-----
    from job_fetcher.fetchers.seek_search import SeekSearchScraper

    scraper = SeekSearchScraper()
    stubs = scraper.fetch_page("https://au.seek.com/Junior-Software-Engineer-jobs/in-All-Melbourne-VIC")
    for stub in stubs:
        print(stub.title, stub.company, stub.visa_eligible)

    # Paginate automatically:
    all_stubs = scraper.fetch_all_pages(url, max_pages=3)
"""

from __future__ import annotations

import json
import re
from urllib.parse import urljoin, urlparse, urlencode, parse_qs, urlunparse

import requests
from bs4 import BeautifulSoup

from ..base import _polite_delay, _random_headers
from ..models import JobFetchError, JobStub
from ..visa_filter import detect_visa_signals

_SEEK_BASE = "https://www.seek.com.au"
_SEEK_DOMAINS = ("seek.com.au", "au.seek.com")

# SEEK embeds all listing data in a Redux state blob on the page.
_REDUX_RE = re.compile(r"window\.SEEK_REDUX_DATA\s*=\s*(\{.+?\});\s*</script>", re.DOTALL)


class SeekSearchScraper:
    """Scrapes SEEK search result pages and returns JobStub lists."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_page(self, url: str, page: int = 1) -> list[JobStub]:
        """Return all job stubs from a single SEEK search results page.

        Parameters
        ----------
        url:   A SEEK search URL (keyword-slug or full URL with query string).
        page:  1-indexed page number to fetch (appended as ``?page=N``).
        """
        paged_url = _inject_page(url, page)
        _polite_delay()
        try:
            resp = requests.get(paged_url, headers=_random_headers(), timeout=15, verify=True)
            resp.raise_for_status()
        except requests.exceptions.SSLError:
            import urllib3, warnings
            warnings.warn("SSL error on SEEK search — retrying without verification.", stacklevel=2)
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            try:
                resp = requests.get(paged_url, headers=_random_headers(), timeout=15, verify=False)
                resp.raise_for_status()
            except requests.RequestException as exc:
                raise JobFetchError(
                    f"Network error fetching SEEK search page {page} (SSL fallback failed): {exc}",
                    url=paged_url,
                ) from exc
        except requests.RequestException as exc:
            raise JobFetchError(
                f"Network error fetching SEEK search page {page}: {exc}", url=paged_url
            ) from exc

        soup = BeautifulSoup(resp.text, "html.parser")

        # Try Redux JSON blob first — richest data source.
        stubs = self._parse_redux(resp.text, paged_url)
        if stubs:
            return stubs

        # Fall back to DOM card parsing.
        return self._parse_dom(soup, paged_url)

    def fetch_all_pages(self, url: str, max_pages: int = 5) -> list[JobStub]:
        """Paginate through SEEK search results, up to ``max_pages`` pages.

        Stops early when a page returns zero results (end of results).
        """
        all_stubs: list[JobStub] = []
        for page in range(1, max_pages + 1):
            stubs = self.fetch_page(url, page=page)
            if not stubs:
                break
            all_stubs.extend(stubs)
            # Don't delay after the last page we actually fetch.
            if len(stubs) < 20:
                break
        return all_stubs

    def fetch_multiple(
        self,
        urls: list[str],
        max_pages: int = 1,
        verbose: bool = False,
    ) -> list[JobStub]:
        """Fetch multiple search URLs and return a deduplicated combined list.

        Results are merged in URL order.  A job appearing in more than one
        search is kept only once (first occurrence wins, preserving order).
        Deduplication key is the job URL (which encodes the unique job ID).

        Parameters
        ----------
        urls      : List of SEEK search URLs to fetch.
        max_pages : Pages to paginate per URL.
        verbose   : Print progress to stderr when True.
        """
        import sys

        seen_urls: set[str] = set()
        combined: list[JobStub] = []

        for i, url in enumerate(urls, 1):
            if verbose:
                label = url.split("/")[-2] if "/" in url else url
                print(
                    f"  [{i}/{len(urls)}] {label} …",
                    end="",
                    flush=True,
                    file=sys.stderr,
                )
            try:
                stubs = self.fetch_all_pages(url, max_pages=max_pages)
            except JobFetchError as exc:
                if verbose:
                    print(f" ✗ {exc}", file=sys.stderr)
                continue

            new = [s for s in stubs if s.url not in seen_urls]
            for s in new:
                seen_urls.add(s.url)
            combined.extend(new)

            if verbose:
                print(
                    f" {len(stubs)} fetched, {len(new)} new"
                    f" (total unique: {len(combined)})",
                    file=sys.stderr,
                )

            # Extra cooldown between URL groups so we don't immediately fire
            # the next batch right after the last page of the current one.
            # Each individual page already waits 1–3 s; this adds another
            # 2–5 s buffer between search keyword variants.
            if i < len(urls):
                _polite_delay(min_s=2.0, max_s=5.0)

        return combined

    @staticmethod
    def can_handle_search(url: str) -> bool:
        """Return True if *url* looks like a SEEK search results page."""
        lower = url.lower()
        is_seek = any(d in lower for d in _SEEK_DOMAINS)
        # Individual job pages end with /job/<id>; search pages don't.
        is_individual = re.search(r"/job/\d+", lower)
        return is_seek and not is_individual

    # ------------------------------------------------------------------
    # Redux JSON extraction (primary)
    # ------------------------------------------------------------------

    def _parse_redux(self, html: str, url: str) -> list[JobStub]:
        """Extract listings from the SEEK Redux state blob embedded in the HTML."""
        match = _REDUX_RE.search(html)
        if not match:
            return []

        try:
            redux = json.loads(match.group(1))
        except json.JSONDecodeError:
            return []

        # Navigate the Redux tree to the jobs array.
        # The path varies slightly across SEEK versions; try common paths.
        jobs_list: list[dict] = (
            _deep_get(redux, "results", "results", "jobs")
            or _deep_get(redux, "jobSearch", "result", "jobs")
            or []
        )

        if not jobs_list:
            return []

        stubs = []
        for job in jobs_list:
            stub = self._redux_job_to_stub(job, url)
            if stub:
                stubs.append(stub)
        return stubs

    def _redux_job_to_stub(self, job: dict, page_url: str) -> JobStub | None:
        """Convert one Redux job dict into a JobStub."""
        try:
            job_id = str(job.get("id", "")).strip()
            if not job_id:
                return None

            title = (job.get("title") or "").strip()
            company = (
                _deep_get(job, "advertiser", "description")
                or job.get("companyName")
                or ""
            ).strip()

            location_parts = [
                job.get("suburb", ""),
                job.get("area", ""),
                job.get("location", ""),
            ]
            location = ", ".join(p for p in location_parts if p).strip(", ")

            salary = _seek_salary_str(job.get("salary"))
            work_type = _normalise_work_type(job.get("workType") or job.get("workArrangement"))
            date_listed = job.get("listingDate") or job.get("listedAt")
            preview = (job.get("teaser") or job.get("abstract") or "").strip()
            is_featured = bool(job.get("isFeatured") or job.get("isPremium"))

            job_url = urljoin(_SEEK_BASE, f"/job/{job_id}")
            visa_eligible, sponsorship = detect_visa_signals(preview)

            return JobStub(
                title=title,
                company=company,
                location=location,
                url=job_url,
                source="seek",
                salary=salary,
                work_type=work_type,
                date_listed=_human_date(date_listed),
                description_preview=preview,
                visa_eligible=visa_eligible,
                sponsorship_available=sponsorship,
                is_featured=is_featured,
            )
        except Exception:
            return None

    # ------------------------------------------------------------------
    # DOM fallback
    # ------------------------------------------------------------------

    def _parse_dom(self, soup: BeautifulSoup, page_url: str) -> list[JobStub]:
        """Parse job cards from the DOM when the Redux blob is absent."""
        stubs: list[JobStub] = []

        # SEEK job cards live inside <article data-card-type="JobCard"> elements.
        cards = soup.select('article[data-card-type="JobCard"]') \
                or soup.select('[data-automation="normalJob"], [data-automation="featuredJob"]')

        for card in cards:
            stub = self._dom_card_to_stub(card, page_url)
            if stub:
                stubs.append(stub)

        return stubs

    def _dom_card_to_stub(self, card, page_url: str) -> JobStub | None:
        """Convert one DOM card element into a JobStub."""
        try:
            # Job link — href="/job/12345678"
            link = card.select_one('a[href*="/job/"]')
            if not link:
                return None
            href = link.get("href", "")
            job_id_match = re.search(r"/job/(\d+)", href)
            if not job_id_match:
                return None
            job_url = urljoin(_SEEK_BASE, f"/job/{job_id_match.group(1)}")

            title = _card_text(card, '[data-automation="jobTitle"]') \
                    or link.get_text(strip=True)
            company = _card_text(card, '[data-automation="jobCompany"]')
            location = _card_text(card, '[data-automation="jobLocation"]') \
                       or _card_text(card, '[data-automation="jobArea"]')
            salary = _card_text(card, '[data-automation="jobSalary"]')
            work_type_raw = _card_text(card, '[data-automation="jobWorkType"]')
            preview = _card_text(card, '[data-automation="jobDescription"]') \
                      or _card_text(card, '[data-automation="jobShortDescription"]')
            date_el = card.select_one('[data-automation="jobListingDate"]') \
                      or card.select_one("time")
            date_listed = date_el.get_text(strip=True) if date_el else None
            is_featured = bool(card.select_one('[data-automation="featuredLabel"]')
                               or "featured" in card.get("class", []))

            work_type = _normalise_work_type(work_type_raw)
            visa_eligible, sponsorship = detect_visa_signals(preview or "")

            return JobStub(
                title=title,
                company=company,
                location=location,
                url=job_url,
                source="seek",
                salary=salary or None,
                work_type=work_type,
                date_listed=date_listed,
                description_preview=preview or None,
                visa_eligible=visa_eligible,
                sponsorship_available=sponsorship,
                is_featured=is_featured,
            )
        except Exception:
            return None


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------

def _deep_get(d: dict, *keys: str):
    """Safely traverse nested dicts; returns None if any key is missing."""
    for key in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(key)
    return d


def _card_text(card, selector: str) -> str:
    el = card.select_one(selector)
    return el.get_text(strip=True) if el else ""


def _seek_salary_str(salary_obj) -> str | None:
    if not salary_obj:
        return None
    if isinstance(salary_obj, str):
        return salary_obj.strip() or None
    if isinstance(salary_obj, dict):
        label = salary_obj.get("label") or salary_obj.get("display")
        return label.strip() if label else None
    return None


def _normalise_work_type(raw: str | None) -> str | None:
    if not raw:
        return None
    lower = raw.lower()
    if "full" in lower:
        return "full-time"
    if "part" in lower:
        return "part-time"
    if "contract" in lower or "casual" in lower or "temp" in lower:
        return "contract"
    return raw.strip() or None


def _human_date(raw: str | None) -> str | None:
    """Keep it as-is; SEEK dates are already human-readable strings."""
    return raw.strip() if raw else None


def _inject_page(url: str, page: int) -> str:
    """Return the URL with ``?page=<N>`` set (or updated if already present)."""
    if page <= 1:
        return url
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    qs["page"] = [str(page)]
    new_query = urlencode({k: v[0] for k, v in qs.items()})
    return urlunparse(parsed._replace(query=new_query))
