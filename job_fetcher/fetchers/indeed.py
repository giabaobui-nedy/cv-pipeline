"""
fetchers/indeed.py — scraper for individual Indeed (au.indeed.com) job listings.

Indeed's viewjob pages block plain HTTP requests with Cloudflare bot-detection
(403), so we use Playwright (headless Chromium) to render the page and then
apply the same JSON-LD → DOM parsing pipeline as before.
"""

from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from ..base import JobFetcher, _polite_delay, _random_headers
from ..models import JobFetchError, JobListing
from ..visa_filter import detect_visa_signals

_INDEED_DOMAINS = ("indeed.com", "au.indeed.com")

_INDEED_MIN_DELAY = 2.0
_INDEED_MAX_DELAY = 5.0

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False


class IndeedFetcher(JobFetcher):
    """Fetches a single job listing from au.indeed.com via Playwright."""

    def can_handle(self, url: str) -> bool:
        return any(domain in url.lower() for domain in _INDEED_DOMAINS)

    def fetch(self, url: str) -> JobListing:
        if not _PLAYWRIGHT_AVAILABLE:
            raise JobFetchError(
                "Playwright is required for Indeed listings but is not installed. "
                "Run: playwright install chromium",
                url=url,
            )

        _polite_delay(_INDEED_MIN_DELAY, _INDEED_MAX_DELAY)

        html, js_model = self._fetch_html_and_state(url)
        soup = BeautifulSoup(html, "html.parser")

        # Preferred path: JS state model (most reliable, not affected by DOM changes).
        if js_model and isinstance(js_model, dict):
            listing = self._parse_js_model(js_model, url)
            if listing:
                return listing

        # Standard paths: JSON-LD block → DOM selectors.
        listing = self._parse_json_ld(soup, url)
        if listing:
            return listing
        return self._parse_dom(soup, url)

    # JS snippet to pull job data from Indeed's client-side state.
    # viewjob pages expose the full job posting in window._initialData.
    _JS_EXTRACT_JOB = """
    () => {
        try {
            const d = window._initialData;
            if (!d) return null;
            // Try common paths Indeed has used across versions.
            return (
                d?.jobInfoWrapperModel?.jobInfoModel
                || d?.viewJobData?.jobInfoWrapperModel?.jobInfoModel
                || null
            );
        } catch(e) { return null; }
    }
    """

    def _fetch_html_and_state(self, url: str) -> tuple[str, dict | None]:
        """Render the Indeed viewjob page and return (html, js_model).

        Indeed's viewjob is a React SPA.  We use ``networkidle`` so the
        browser waits until the JS bundle has finished executing before we
        snapshot the page, guaranteeing the DOM is fully hydrated.

        Also extracts ``window._initialData`` from the live JS state — this
        is the most reliable source and survives DOM selector changes.
        """
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
                # "load" fires after scripts execute; networkidle times out on
                # Indeed because they have continuous background requests.
                page.goto(url, timeout=30_000, wait_until="load")

                # Wait for any job-content element to appear (React has mounted).
                for sel in (
                    "#jobDescriptionText",
                    '[data-testid="job-description"]',
                    '[data-testid="jobsearch-JobInfoHeader-title"]',
                    "h1.jobsearch-JobInfoHeader-title",
                ):
                    try:
                        page.wait_for_selector(sel, timeout=8_000)
                        break
                    except PlaywrightTimeout:
                        continue

                js_model = page.evaluate(self._JS_EXTRACT_JOB)
                html = page.content()
                return html, js_model
            except PlaywrightTimeout:
                raise JobFetchError(
                    "Playwright timed out loading Indeed listing page.", url=url
                )
            except Exception as exc:
                raise JobFetchError(
                    f"Playwright error fetching Indeed listing: {exc}", url=url
                )
            finally:
                browser.close()

    def _parse_js_model(self, model: dict, url: str) -> JobListing | None:
        """Build a JobListing from Indeed's ``window._initialData`` job model."""
        try:
            title = (model.get("jobTitle") or model.get("title") or "").strip()
            company = (
                model.get("companyName")
                or model.get("company")
                or ""
            ).strip()
            if not title or not company:
                return None

            location = (model.get("formattedLocation") or model.get("location") or "").strip()

            # Description: may be HTML — strip tags.
            raw_desc = (
                model.get("sanitizedJobDescription")
                or model.get("jobDescription")
                or model.get("description")
                or ""
            )
            description = _strip_html(raw_desc) if "<" in raw_desc else raw_desc.strip()

            salary = (model.get("salaryInfoModel", {}) or {}).get("formattedRange") or None
            work_type = _normalise_work_type(
                model.get("jobType") or model.get("employmentType")
            )
            date_posted = model.get("datePosted") or model.get("pubDate") or None
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
                date_posted=date_posted,
                visa_eligible=visa_eligible,
                sponsorship_available=sponsorship,
            )
        except Exception:
            return None

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
