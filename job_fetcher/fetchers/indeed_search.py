"""
fetchers/indeed_search.py — scraper for Indeed (au.indeed.com) search result pages.

Indeed protects its search pages with Cloudflare and bot-detection, so a plain
``requests`` call usually returns 403.  We use a two-stage strategy:

  Stage 1 — requests (fast, no overhead)
      Tried first.  If the response is 200 and not a CAPTCHA page we parse the
      ``window.mosaic.providerData`` JSON blob embedded in the HTML, falling
      back to CSS-selector DOM parsing.

  Stage 2 — Playwright (headless Chromium)
      Triggered automatically on a 403 / CAPTCHA response.  We navigate with a
      real browser, pull ``window.mosaic.providerData`` directly from the live
      JavaScript state via ``page.evaluate()``, and fall back to DOM parsing of
      the rendered HTML if the JS object is unavailable.

Each job is identified by an ``&jk=`` key, from which we construct the
canonical ``https://au.indeed.com/viewjob?jk=...`` URL.

Usage
-----
    from job_fetcher.fetchers.indeed_search import IndeedSearchScraper

    scraper = IndeedSearchScraper()
    stubs = scraper.fetch_page("https://au.indeed.com/jobs?q=junior+software+engineer&l=Melbourne+VIC")
    stubs = scraper.fetch_all_pages(url, max_pages=3)
"""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

import requests
from bs4 import BeautifulSoup

from ..base import _polite_delay, _random_headers
from ..models import JobFetchError, JobStub
from ..visa_filter import detect_visa_signals

_INDEED_BASE = "https://au.indeed.com"

# Indeed uses longer, more realistic delays to avoid triggering rate limits.
_MIN_DELAY = 2.0
_MAX_DELAY = 5.0

# Playwright is optional — import lazily so the package works without it.
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False

# Regex to find common Indeed data blobs embedded in <script> tags.
_MOSAIC_RE = re.compile(
    r'window\.mosaic\.providerData\["mosaic-provider-jobcards"\]\s*=\s*(\{.+?\});',
    re.DOTALL,
)
_INITIAL_DATA_RE = re.compile(
    r'window\._initialData\s*=\s*(\{.+?\});',
    re.DOTALL,
)

# JavaScript snippet that extracts the mosaic job-cards provider from the live
# page state — more reliable than regex-parsing the raw HTML.
_JS_EXTRACT_MOSAIC = """
() => {
    try {
        return window.mosaic?.providerData?.["mosaic-provider-jobcards"] ?? null;
    } catch (e) {
        return null;
    }
}
"""


class IndeedSearchScraper:
    """Scrapes Indeed search result pages and returns JobStub lists."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_page(self, url: str, page: int = 1) -> list[JobStub]:
        """Return all job stubs from one Indeed search results page.

        Parameters
        ----------
        url  : An Indeed jobs search URL (with ``q`` and ``l`` params).
        page : 1-indexed page number (Indeed uses ``&start=N*10``).
        """
        paged_url = _inject_page(url, page)
        _polite_delay(_MIN_DELAY, _MAX_DELAY)

        # ── Stage 1: plain requests (fast) ───────────────────────────────
        html: str | None = None
        try:
            resp = requests.get(
                paged_url,
                headers=_indeed_headers(),
                timeout=20,
                allow_redirects=True,
                verify=True,
            )
            if resp.status_code not in (403, 429) and not _is_blocked(resp.text):
                resp.raise_for_status()
                html = resp.text
        except requests.exceptions.SSLError:
            import urllib3, warnings
            warnings.warn(
                "SSL error on Indeed search — retrying without verification.",
                stacklevel=2,
            )
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            try:
                resp = requests.get(
                    paged_url,
                    headers=_indeed_headers(),
                    timeout=20,
                    allow_redirects=True,
                    verify=False,
                )
                if resp.status_code not in (403, 429) and not _is_blocked(resp.text):
                    html = resp.text
            except requests.RequestException:
                pass  # Will fall through to Playwright below.
        except requests.RequestException:
            pass  # Will fall through to Playwright below.

        if html:
            stubs = self._parse_mosaic_json(html, paged_url)
            if stubs:
                return stubs
            soup = BeautifulSoup(html, "html.parser")
            stubs = self._parse_dom(soup, paged_url)
            if stubs:
                return stubs
            # Got a page but parsed nothing — may be an empty results page.
            # Don't try Playwright if the page loaded fine; just return [].
            if not _is_blocked(html):
                return []

        # ── Stage 2: Playwright (handles Cloudflare / bot-detection) ────
        if not _PLAYWRIGHT_AVAILABLE:
            raise JobFetchError(
                "Indeed search returned 403/CAPTCHA and Playwright is not installed. "
                "Run: playwright install chromium",
                url=paged_url,
            )
        return self._fetch_with_playwright(paged_url)

    def fetch_all_pages(self, url: str, max_pages: int = 3) -> list[JobStub]:
        """Paginate through Indeed search results up to *max_pages* pages.

        Stops early when a page returns zero results or < 10 (last page).
        """
        all_stubs: list[JobStub] = []
        for page in range(1, max_pages + 1):
            stubs = self.fetch_page(url, page=page)
            if not stubs:
                break
            all_stubs.extend(stubs)
            if len(stubs) < 10:
                break
        return all_stubs

    def _fetch_with_playwright(self, url: str) -> list[JobStub]:
        """Navigate Indeed search with a headless browser and extract job stubs.

        Pulls ``window.mosaic.providerData["mosaic-provider-jobcards"]``
        directly from the live JavaScript state, falling back to DOM parsing
        of the fully-rendered HTML if the JS object is unavailable.
        """
        import sys
        print(
            "  [Indeed] 403 detected — retrying with Playwright …",
            end="", flush=True, file=sys.stderr,
        )

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=_random_headers()["User-Agent"],
                locale="en-AU",
                viewport={"width": 1280, "height": 900},
                extra_http_headers={
                    "Accept-Language": "en-AU,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            page = context.new_page()

            try:
                page.goto(url, timeout=30_000, wait_until="domcontentloaded")
                _polite_delay(2.0, 4.0)   # let JS hydrate

                # Try to extract mosaic data from the live JS state.
                mosaic_data = page.evaluate(_JS_EXTRACT_MOSAIC)

                if mosaic_data and isinstance(mosaic_data, dict):
                    print(" ✓ (mosaic JS)", file=sys.stderr)
                    stubs: list[JobStub] = []
                    tiles = (
                        _deep_get(mosaic_data, "metaData", "mosaicProviderJobCardsModel", "tiles")
                        or mosaic_data.get("tiles")
                        or []
                    )
                    for tile in tiles:
                        stub = self._tile_to_stub(tile, url)
                        if stub:
                            stubs.append(stub)
                    return stubs

                # Fall back to DOM parsing of the rendered HTML.
                html = page.content()
                print(" ✓ (DOM fallback)", file=sys.stderr)
            except PlaywrightTimeout:
                print(" ✗ (timeout)", file=sys.stderr)
                raise JobFetchError(
                    "Playwright timed out loading Indeed search page.",
                    url=url,
                )
            except JobFetchError:
                raise
            except Exception as exc:
                print(f" ✗ ({exc})", file=sys.stderr)
                raise JobFetchError(
                    f"Playwright error fetching Indeed search: {exc}",
                    url=url,
                )
            finally:
                browser.close()

        # Parse from rendered HTML.
        stubs_html = self._parse_mosaic_json(html, url)
        if stubs_html:
            return stubs_html
        soup = BeautifulSoup(html, "html.parser")
        return self._parse_dom(soup, url)

    def fetch_multiple(
        self,
        urls: list[str],
        max_pages: int = 1,
        verbose: bool = False,
    ) -> list[JobStub]:
        """Fetch multiple search URLs and return a deduplicated combined list."""
        import sys

        seen: set[str] = set()
        combined: list[JobStub] = []

        for i, url in enumerate(urls, 1):
            if verbose:
                label = _url_label(url)
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

            new = [s for s in stubs if s.url not in seen]
            for s in new:
                seen.add(s.url)
            combined.extend(new)

            if verbose:
                print(
                    f" {len(stubs)} fetched, {len(new)} new"
                    f" (total unique: {len(combined)})",
                    file=sys.stderr,
                )

            # Extra cooldown between URL groups.
            if i < len(urls):
                _polite_delay(3.0, 6.0)

        return combined

    # ------------------------------------------------------------------
    # JSON blob extraction (primary)
    # ------------------------------------------------------------------

    def _parse_mosaic_json(self, html: str, url: str) -> list[JobStub]:
        """Extract job stubs from the embedded Mosaic / initialData JSON blob."""

        raw_json: str | None = None

        # Try the modern Mosaic provider data first.
        m = _MOSAIC_RE.search(html)
        if m:
            raw_json = m.group(1)
        else:
            # Older / fallback format.
            m = _INITIAL_DATA_RE.search(html)
            if m:
                raw_json = m.group(1)

        if not raw_json:
            return []

        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            return []

        # Navigate the mosaic structure to reach the job tiles/cards list.
        # Path: data -> metaData -> mosaicProviderJobCardsModel -> tiles
        tiles = (
            _deep_get(data, "metaData", "mosaicProviderJobCardsModel", "tiles")
            or _deep_get(data, "jobsInResultSet")
            or _deep_get(data, "jobResults")
            or []
        )

        stubs: list[JobStub] = []
        for tile in tiles:
            stub = self._tile_to_stub(tile, url)
            if stub:
                stubs.append(stub)
        return stubs

    def _tile_to_stub(self, tile: dict, page_url: str) -> JobStub | None:
        """Convert one Mosaic tile dict into a JobStub."""
        try:
            job_key = (
                tile.get("jobkey")
                or tile.get("jobKey")
                or _deep_get(tile, "jobCard", "jobkey")
                or ""
            ).strip()
            if not job_key:
                return None

            job_url = f"{_INDEED_BASE}/viewjob?jk={job_key}"

            title = (
                _deep_get(tile, "jobCard", "title")
                or tile.get("title")
                or ""
            ).strip()

            company = (
                _deep_get(tile, "jobCard", "company")
                or tile.get("company")
                or ""
            ).strip()

            location = (
                _deep_get(tile, "jobCard", "formattedLocation")
                or _deep_get(tile, "jobCard", "location")
                or tile.get("formattedLocation")
                or tile.get("location")
                or ""
            ).strip()

            salary = _extract_salary_tile(tile)
            work_type = _extract_work_type_tile(tile)
            date_listed = (
                _deep_get(tile, "jobCard", "formattedRelativeTime")
                or tile.get("formattedRelativeTime")
                or _deep_get(tile, "jobCard", "datePublished")
                or None
            )
            preview = (
                _deep_get(tile, "jobCard", "snippet")
                or tile.get("snippet")
                or ""
            ).strip()
            # Strip HTML from snippet.
            preview = re.sub(r"<[^>]+>", " ", preview).strip()

            visa_eligible, sponsorship = detect_visa_signals(preview)

            return JobStub(
                title=title,
                company=company,
                location=location,
                url=job_url,
                source="indeed",
                salary=salary,
                work_type=work_type,
                date_listed=date_listed,
                description_preview=preview or None,
                visa_eligible=visa_eligible,
                sponsorship_available=sponsorship,
                is_featured=bool(tile.get("sponsored") or tile.get("isSponsor")),
            )
        except Exception:
            return None

    # ------------------------------------------------------------------
    # DOM fallback
    # ------------------------------------------------------------------

    def _parse_dom(self, soup: BeautifulSoup, page_url: str) -> list[JobStub]:
        """Parse job cards from the rendered DOM when the JSON blob is absent."""
        stubs: list[JobStub] = []

        # Indeed job cards: <div data-jk="..."> or <div class="job_seen_beacon">
        cards = (
            soup.select("div[data-jk]")
            or soup.select("div.job_seen_beacon")
            or soup.select("td.resultContent")
        )

        for card in cards:
            stub = self._dom_card_to_stub(card, page_url)
            if stub:
                stubs.append(stub)

        return stubs

    def _dom_card_to_stub(self, card, page_url: str) -> JobStub | None:
        """Convert one DOM job card into a JobStub."""
        try:
            # Job key lives on the card root or its closest ancestor.
            job_key = (
                card.get("data-jk")
                or (card.find_parent(attrs={"data-jk": True}) or {}).get("data-jk")
                or ""
            ).strip()
            if not job_key:
                return None

            job_url = f"{_INDEED_BASE}/viewjob?jk={job_key}"

            title = (
                _card_text(card, "h2.jobTitle a")
                or _card_text(card, "a[data-jk]")
                or _card_text(card, "h2[data-testid='jobTitle']")
                or _card_text(card, "h2 span[title]")
            )

            company = (
                _card_text(card, "[data-testid='company-name']")
                or _card_text(card, "span.companyName")
                or _card_text(card, "a[data-tn-element='companyName']")
            )

            location = (
                _card_text(card, "[data-testid='text-location']")
                or _card_text(card, "div.companyLocation")
                or _card_text(card, "span.companyLocation")
            )

            salary_raw = (
                _card_text(card, "[data-testid='attribute_snippet_testid']")
                or _card_text(card, "div.salary-snippet-container")
                or _card_text(card, "span.salaryText")
            )
            salary = _parse_salary_text(salary_raw)

            preview = (
                _card_text(card, "div.job-snippet")
                or _card_text(card, "[data-testid='jobsnippet']")
            )

            date_el = card.select_one(".date") or card.select_one("span.date")
            date_listed = date_el.get_text(strip=True) if date_el else None

            work_type = _extract_work_type_text(salary_raw + " " + preview)
            visa_eligible, sponsorship = detect_visa_signals(preview or "")

            is_sponsored = bool(
                card.select_one(".sponsoredJob")
                or card.select_one("[data-testid='sponsored-label']")
            )

            if not title:
                return None

            return JobStub(
                title=title,
                company=company or "",
                location=location or "",
                url=job_url,
                source="indeed",
                salary=salary,
                work_type=work_type,
                date_listed=date_listed,
                description_preview=preview or None,
                visa_eligible=visa_eligible,
                sponsorship_available=sponsorship,
                is_featured=is_sponsored,
            )
        except Exception:
            return None


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------

def build_indeed_url(query: str, location: str) -> str:
    """Build an au.indeed.com jobs search URL from a query and location string.

    Example
    -------
        build_indeed_url("junior software engineer", "Melbourne VIC")
        # → https://au.indeed.com/jobs?q=junior+software+engineer&l=Melbourne+VIC&sort=date
    """
    from urllib.parse import quote_plus
    return (
        f"{_INDEED_BASE}/jobs"
        f"?q={quote_plus(query)}"
        f"&l={quote_plus(location)}"
        f"&sort=date"
    )


# Mapping of our CLI location aliases to Indeed-friendly location strings.
INDEED_LOCATIONS: dict[str, str] = {
    "melbourne":    "Melbourne VIC",
    "sydney":       "Sydney NSW",
    "brisbane":     "Brisbane QLD",
    "perth":        "Perth WA",
    "adelaide":     "Adelaide SA",
    "canberra":     "Canberra ACT",
    "remote":       "Remote",
    "australia":    "Australia",
}


def _indeed_headers() -> dict[str, str]:
    """Return request headers that look like a real Chrome browser."""
    base = _random_headers()
    base["Accept-Encoding"] = "gzip, deflate, br"
    base["Connection"] = "keep-alive"
    base["Upgrade-Insecure-Requests"] = "1"
    return base


def _is_blocked(html: str) -> bool:
    lower = html.lower()
    return any(
        signal in lower
        for signal in (
            "please verify you are a human",
            "captcha",
            "access denied",
            "bot detection",
            "unusual traffic",
        )
    )


def _deep_get(d: dict, *keys: str):
    for key in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(key)
    return d


def _card_text(card, selector: str) -> str:
    el = card.select_one(selector)
    return el.get_text(strip=True) if el else ""


def _extract_salary_tile(tile: dict) -> str | None:
    """Pull salary from a Mosaic tile's various possible fields."""
    for path in (
        ("jobCard", "extractedSalary", "formattedRange"),
        ("jobCard", "salarySnippet", "text"),
        ("jobCard", "salary"),
        ("extractedSalary", "formattedRange"),
        ("salarySnippet", "text"),
    ):
        val = _deep_get(tile, *path)
        if val and isinstance(val, str):
            return val.strip()
    return None


def _extract_work_type_tile(tile: dict) -> str | None:
    raw = (
        _deep_get(tile, "jobCard", "jobType")
        or _deep_get(tile, "jobType")
        or ""
    )
    return _normalise_work_type(raw)


def _parse_salary_text(raw: str) -> str | None:
    """Return the salary portion of a text snippet, or None if not salary-like."""
    if not raw:
        return None
    # Salary strings contain $ or "per year/hour" signals.
    if "$" in raw or "per year" in raw.lower() or "per hour" in raw.lower():
        return raw.strip()
    return None


def _extract_work_type_text(text: str) -> str | None:
    lower = text.lower()
    if "full-time" in lower or "full time" in lower:
        return "full-time"
    if "part-time" in lower or "part time" in lower:
        return "part-time"
    if "contract" in lower or "casual" in lower or "temporary" in lower:
        return "contract"
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


def _inject_page(url: str, page: int) -> str:
    """Append/update Indeed's ``start=`` offset parameter (10 results per page)."""
    if page <= 1:
        return url
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    qs["start"] = [str((page - 1) * 10)]
    new_query = urlencode({k: v[0] for k, v in qs.items()})
    return urlunparse(parsed._replace(query=new_query))


def _url_label(url: str) -> str:
    """Short human-readable label for progress output."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    q = qs.get("q", ["?"])[0]
    l = qs.get("l", [""])[0]
    return f"{q} @ {l}" if l else q
