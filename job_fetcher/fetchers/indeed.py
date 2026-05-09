"""
fetchers/indeed.py — scraper for Indeed (au.indeed.com).

Indeed is server-side rendered for most listing pages, so requests +
BeautifulSoup works.  We are extra cautious with rate-limiting here because
Indeed is aggressive about bot detection: random delays and User-Agent rotation
are mandatory (both are applied by the base class helpers).

Indeed sometimes redirects bare job IDs to a "ViewJob" URL — we follow
redirects transparently via requests.
"""

from __future__ import annotations

import json
import re

import requests
from bs4 import BeautifulSoup

from ..base import JobFetcher, _polite_delay, _random_headers
from ..models import JobFetchError, JobListing
from ..visa_filter import detect_visa_signals

_INDEED_DOMAINS = ("indeed.com", "au.indeed.com")

# Indeed sometimes embeds longer delays between pages under bot suspicion;
# we use a wider random window to blend in.
_INDEED_MIN_DELAY = 2.0
_INDEED_MAX_DELAY = 5.0


class IndeedFetcher(JobFetcher):
    """Fetches a single job listing from au.indeed.com."""

    def can_handle(self, url: str) -> bool:
        return any(domain in url.lower() for domain in _INDEED_DOMAINS)

    def fetch(self, url: str) -> JobListing:
        _polite_delay(_INDEED_MIN_DELAY, _INDEED_MAX_DELAY)
        try:
            response = requests.get(
                url,
                headers=_random_headers(),
                timeout=15,
                allow_redirects=True,
                verify=True,
            )
            response.raise_for_status()
        except requests.exceptions.SSLError:
            import urllib3, warnings
            warnings.warn("SSL error on Indeed — retrying without verification.", stacklevel=2)
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            try:
                response = requests.get(url, headers=_random_headers(), timeout=15,
                                        allow_redirects=True, verify=False)
                response.raise_for_status()
            except requests.RequestException as exc:
                raise JobFetchError(
                    f"Network error fetching Indeed listing (SSL fallback failed): {exc}", url=url
                ) from exc
        except requests.RequestException as exc:
            raise JobFetchError(
                f"Network error while fetching Indeed listing: {exc}", url=url
            ) from exc

        soup = BeautifulSoup(response.text, "html.parser")

        # Check for CAPTCHA / bot block page.
        if self._is_blocked(soup, response.text):
            raise JobFetchError(
                "Indeed returned a CAPTCHA or bot-detection page. "
                "Try again in a few minutes, or use a different network.",
                url=url,
            )

        # Prefer JSON-LD when available.
        listing = self._parse_json_ld(soup, url)
        if listing:
            return listing

        return self._parse_dom(soup, url)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_blocked(self, soup: BeautifulSoup, raw: str) -> bool:
        """Detect CAPTCHA / block pages heuristically."""
        block_signals = [
            "please verify you are a human",
            "captcha",
            "access denied",
            "bot detection",
            "enable javascript",
        ]
        lower = raw.lower()
        return any(signal in lower for signal in block_signals)

    def _parse_json_ld(self, soup: BeautifulSoup, url: str) -> JobListing | None:
        """Try to extract a JobListing from the page's JSON-LD block."""
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

                org = job_data.get("hiringOrganization", {})
                company = org.get("name", "").strip() if isinstance(org, dict) else ""

                location_obj = job_data.get("jobLocation", {})
                if isinstance(location_obj, list):
                    location_obj = location_obj[0] if location_obj else {}
                address = location_obj.get("address", {}) if isinstance(location_obj, dict) else {}
                location = (
                    address.get("addressLocality", "")
                    or address.get("addressRegion", "")
                ).strip()

                return JobListing(
                    title=job_data.get("title", "").strip(),
                    company=company,
                    location=location,
                    description=description,
                    url=url,
                    source="indeed",
                    salary=_indeed_salary(job_data),
                    work_type=_normalise_work_type(job_data.get("employmentType")),
                    date_posted=job_data.get("datePosted"),
                    visa_eligible=visa_eligible,
                    sponsorship_available=sponsorship,
                )
            except Exception as exc:
                raise JobFetchError(
                    f"Failed to parse Indeed JSON-LD block: {exc}", url=url
                ) from exc

        return None

    def _parse_dom(self, soup: BeautifulSoup, url: str) -> JobListing:
        """DOM-based fallback for when JSON-LD is missing."""
        try:
            # Indeed uses data-testid attributes on modern pages.
            title = _text(soup.select_one('[data-testid="jobsearch-JobInfoHeader-title"]')) \
                    or _text(soup.select_one("h1.jobsearch-JobInfoHeader-title"))

            company = _text(soup.select_one('[data-testid="inlineHeader-companyName"]')) \
                      or _text(soup.select_one("div.icl-u-lg-mr--sm a"))

            location = _text(soup.select_one('[data-testid="job-location"]')) \
                       or _text(soup.select_one("div.icl-u-xs-mt--xs"))

            desc_el = soup.select_one("#jobDescriptionText") \
                      or soup.select_one('[data-testid="job-description"]')
            description = desc_el.get_text(separator="\n").strip() if desc_el else ""

            salary_el = soup.select_one('[data-testid="attribute_snippet_testid"]') \
                        or soup.select_one("span.icl-u-xs-mr--xs")
            salary = salary_el.get_text(strip=True) if salary_el else None

            work_type = _extract_work_type_from_text(description)

            if not title or not company:
                raise JobFetchError(
                    "Could not locate job title or company on the Indeed listing page. "
                    "The page layout may have changed — verify the URL is a direct job link.",
                    url=url,
                )

            visa_eligible, sponsorship = detect_visa_signals(description)

            return JobListing(
                title=title,
                company=company,
                location=location,
                description=description,
                url=url,
                source="indeed",
                salary=salary,
                work_type=work_type,
                visa_eligible=visa_eligible,
                sponsorship_available=sponsorship,
            )
        except JobFetchError:
            raise
        except Exception as exc:
            raise JobFetchError(
                f"Unexpected error while parsing Indeed listing DOM: {exc}", url=url
            ) from exc


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------

def _text(el) -> str:
    return el.get_text(strip=True) if el else ""


def _strip_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["p", "li", "br", "div"]):
        tag.insert_before("\n")
    return re.sub(r"\n{3,}", "\n\n", soup.get_text()).strip()


def _indeed_salary(data: dict) -> str | None:
    base = data.get("baseSalary", {})
    if not isinstance(base, dict):
        return None
    value = base.get("value", {})
    if not isinstance(value, dict):
        return None
    min_val = value.get("minValue")
    max_val = value.get("maxValue")
    currency = base.get("currency", "AUD")
    unit = value.get("unitText", "")
    if min_val and max_val:
        return f"{currency} {min_val}–{max_val} {unit}".strip()
    if min_val:
        return f"{currency} {min_val}+ {unit}".strip()
    return None


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


def _extract_work_type_from_text(text: str) -> str | None:
    lower = text.lower()
    if "full-time" in lower or "full time" in lower:
        return "full-time"
    if "part-time" in lower or "part time" in lower:
        return "part-time"
    if "contract" in lower or "casual" in lower:
        return "contract"
    return None
