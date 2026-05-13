"""
fetchers/seek.py — scraper for SEEK (seek.com.au / au.seek.com).

SEEK individual listing pages are protected by Cloudflare Bot Management, so
plain requests returns HTTP 403.  We use Playwright (headless Chromium) as the
primary fetch path — it executes the Cloudflare JS challenge automatically.

Extraction priority:
  1. JSON-LD <script type="application/ld+json"> JobPosting block
  2. data-automation DOM selectors
"""

from __future__ import annotations

import json
import re

import requests
from bs4 import BeautifulSoup

from ..base import JobFetcher, _polite_delay, _random_headers
from ..models import JobFetchError, JobListing
from ..visa_filter import detect_visa_signals

_SEEK_DOMAINS = ("seek.com.au", "au.seek.com")

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False


class SeekFetcher(JobFetcher):
    """Fetches a single job listing from seek.com.au using Playwright."""

    def can_handle(self, url: str) -> bool:
        return any(d in url.lower() for d in _SEEK_DOMAINS)

    def fetch(self, url: str) -> JobListing:
        if _PLAYWRIGHT_AVAILABLE:
            try:
                return self._fetch_playwright(url)
            except PlaywrightTimeout:
                raise JobFetchError(
                    "SEEK listing page timed out. The site may be slow or blocking headless browsers.",
                    url=url,
                )
            except JobFetchError:
                raise
            except Exception as exc:
                raise JobFetchError(
                    f"Playwright error fetching SEEK listing: {exc}", url=url
                ) from exc
        else:
            raise JobFetchError(
                "Playwright is not installed — it is required to fetch SEEK listings "
                "because SEEK uses Cloudflare bot protection. "
                "Install it with: playwright install chromium",
                url=url,
            )

    # ------------------------------------------------------------------
    # Playwright fetch
    # ------------------------------------------------------------------

    def _fetch_playwright(self, url: str) -> JobListing:
        _polite_delay()
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
                page.goto(url, timeout=25_000, wait_until="domcontentloaded")
                _polite_delay(1.0, 2.0)

                # Wait for either the job title or an error indicator.
                try:
                    page.wait_for_selector(
                        '[data-automation="job-detail-title"], h1',
                        timeout=8_000,
                    )
                except Exception:
                    pass

                html = page.content()
            finally:
                browser.close()

        soup = BeautifulSoup(html, "html.parser")

        listing = self._parse_json_ld(soup, url)
        if listing:
            return listing
        return self._parse_dom(soup, url)

    # ------------------------------------------------------------------
    # Parsers (work on the HTML regardless of how it was fetched)
    # ------------------------------------------------------------------

    def _parse_json_ld(self, soup: BeautifulSoup, url: str) -> JobListing | None:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue

            if isinstance(data, list):
                job_data = next(
                    (d for d in data if d.get("@type") == "JobPosting"), None
                )
            elif data.get("@type") == "JobPosting":
                job_data = data
            else:
                continue

            if not job_data:
                continue

            try:
                description = _strip_html(job_data.get("description", ""))
                visa_eligible, sponsorship = detect_visa_signals(description)
                return JobListing(
                    title=job_data.get("title", "").strip(),
                    company=_nested_get(job_data, "hiringOrganization", "name", default="").strip(),
                    location=(
                        _nested_get(job_data, "jobLocation", "address", "addressLocality", default="")
                        or _nested_get(job_data, "jobLocation", "address", "addressRegion", default="")
                    ).strip(),
                    description=description,
                    url=url,
                    source="seek",
                    salary=_seek_salary(job_data),
                    work_type=_seek_work_type(job_data),
                    date_posted=job_data.get("datePosted"),
                    visa_eligible=visa_eligible,
                    sponsorship_available=sponsorship,
                )
            except Exception as exc:
                raise JobFetchError(
                    f"Failed to parse SEEK JSON-LD block: {exc}", url=url
                ) from exc

        return None

    def _parse_dom(self, soup: BeautifulSoup, url: str) -> JobListing:
        try:
            title    = _text(soup.select_one('[data-automation="job-detail-title"]'))
            company  = _text(soup.select_one('[data-automation="advertiser-name"]'))
            location = _text(soup.select_one('[data-automation="job-detail-location"]'))

            desc_el     = soup.select_one('[data-automation="jobAdDetails"]')
            description = desc_el.get_text(separator="\n").strip() if desc_el else ""

            salary_el   = soup.select_one('[data-automation="job-detail-salary"]')
            salary      = salary_el.get_text(strip=True) if salary_el else None

            wt_el     = soup.select_one('[data-automation="job-detail-work-type"]')
            work_type = _normalise_work_type(wt_el.get_text(strip=True) if wt_el else None)

            date_el     = soup.select_one('[data-automation="job-detail-date"]')
            date_posted = date_el.get_text(strip=True) if date_el else None

            if not title or not company:
                raise JobFetchError(
                    "Could not locate job title or company on the SEEK listing page. "
                    "Cloudflare may still be blocking — try again in a moment.",
                    url=url,
                )

            visa_eligible, sponsorship = detect_visa_signals(description)
            return JobListing(
                title=title,
                company=company,
                location=location,
                description=description,
                url=url,
                source="seek",
                salary=salary,
                work_type=work_type,
                date_posted=date_posted,
                visa_eligible=visa_eligible,
                sponsorship_available=sponsorship,
            )
        except JobFetchError:
            raise
        except Exception as exc:
            raise JobFetchError(
                f"Unexpected error parsing SEEK listing: {exc}", url=url
            ) from exc


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------

def _text(el) -> str:
    return el.get_text(strip=True) if el else ""


def _nested_get(d: dict, *keys: str, default: str = "") -> str:
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key, {})
    return d if isinstance(d, str) else default


def _strip_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["p", "li", "br", "div"]):
        tag.insert_before("\n")
    return re.sub(r"\n{3,}", "\n\n", soup.get_text()).strip()


def _seek_salary(data: dict) -> str | None:
    base  = data.get("baseSalary", {})
    value = base.get("value", {})
    min_val  = value.get("minValue")
    max_val  = value.get("maxValue")
    currency = base.get("currency", "AUD")
    unit     = value.get("unitText", "")
    if min_val and max_val:
        return f"{currency} {min_val}–{max_val} {unit}".strip()
    if min_val:
        return f"{currency} {min_val}+ {unit}".strip()
    return None


def _seek_work_type(data: dict) -> str | None:
    return _normalise_work_type(data.get("employmentType", ""))


def _normalise_work_type(raw: str | None) -> str | None:
    if not raw:
        return None
    lower = raw.lower()
    if "full" in lower:
        return "full-time"
    if "part" in lower:
        return "part-time"
    if "contract" in lower or "casual" in lower:
        return "contract"
    return raw.strip() or None


def _requests_get(url: str) -> requests.Response:
    """Lightweight requests fallback for non-Cloudflare pages (e.g. search results).

    Not used by SeekFetcher.fetch() — kept here for SeekSearchScraper.
    """
    try:
        resp = requests.get(url, headers=_random_headers(), timeout=15)
        resp.raise_for_status()
        return resp
    except requests.exceptions.SSLError:
        import urllib3, warnings
        warnings.warn("SSL error — retrying without verification (pin urllib3<2 to fix).")
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        resp = requests.get(url, headers=_random_headers(), timeout=15, verify=False)
        resp.raise_for_status()
        return resp
