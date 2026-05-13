"""
fetchers/linkedin.py — scraper for LinkedIn job listings.

LinkedIn aggressively blocks headless browsers and unauthenticated scrapers, so
this fetcher takes a two-stage approach:

  1. Try Playwright (headless Chromium) with realistic browser fingerprints.
  2. If Playwright is blocked or unavailable, degrade gracefully and ask the
     user to paste the job description manually.

We deliberately never log in — this tool is read-only and must not automate any
application actions.
"""

from __future__ import annotations

import re
import sys

from ..base import JobFetcher, _polite_delay, _random_headers
from ..models import JobFetchError, JobListing
from ..visa_filter import detect_visa_signals

_LINKEDIN_DOMAINS = ("linkedin.com/jobs", "linkedin.com/job")

# Playwright is an optional dependency — import lazily so the rest of the
# package still works even if it isn't installed.
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False


class LinkedInFetcher(JobFetcher):
    """Fetches a single LinkedIn job listing via Playwright (headless Chromium)."""

    def can_handle(self, url: str) -> bool:
        return any(domain in url.lower() for domain in _LINKEDIN_DOMAINS)

    def fetch(self, url: str) -> JobListing:
        if not _PLAYWRIGHT_AVAILABLE:
            return self._manual_fallback(url, reason="playwright is not installed")

        _polite_delay()
        try:
            return self._fetch_with_playwright(url)
        except PlaywrightTimeout:
            return self._manual_fallback(url, reason="page timed out (possible block)")
        except JobFetchError:
            raise
        except Exception as exc:
            # If Playwright itself crashes or is blocked, degrade gracefully.
            return self._manual_fallback(
                url, reason=f"Playwright error: {exc}"
            )

    # ------------------------------------------------------------------
    # Playwright path
    # ------------------------------------------------------------------

    def _fetch_with_playwright(self, url: str) -> JobListing:
        """Navigate to the listing and extract structured data."""
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=_random_headers()["User-Agent"],
                locale="en-AU",
                viewport={"width": 1280, "height": 800},
                # Extra headers to reduce fingerprint divergence from a real browser.
                extra_http_headers={
                    "Accept-Language": "en-AU,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            page = context.new_page()

            try:
                page.goto(url, timeout=20_000, wait_until="domcontentloaded")
                _polite_delay(1.5, 3.0)

                # Expand the "Show more" button if LinkedIn truncates the description.
                try:
                    page.click(
                        "button.show-more-less-html__button--more",
                        timeout=3_000,
                    )
                    _polite_delay(0.5, 1.0)
                except Exception:
                    pass  # Button not present — description is already fully visible.

                # Detect hard block pages ("Join LinkedIn", sign-in gate, etc.).
                if self._is_blocked(page):
                    browser.close()
                    return self._manual_fallback(
                        url, reason="LinkedIn returned a sign-in or CAPTCHA gate"
                    )

                title = _pw_text(page, "h1.top-card-layout__title") or \
                        _pw_text(page, "h1.jobs-unified-top-card__job-title")
                company = _pw_text(page, "a.topcard__org-name-link") or \
                          _pw_text(page, "span.jobs-unified-top-card__company-name")
                location = _pw_text(page, "span.topcard__flavor--bullet") or \
                           _pw_text(page, "span.jobs-unified-top-card__bullet")

                desc_el = page.query_selector(".show-more-less-html__markup") or \
                          page.query_selector(".jobs-description__content")
                description = desc_el.inner_text().strip() if desc_el else ""

                work_type = _extract_work_type_from_text(description)
                date_posted = _pw_text(page, "span.posted-time-ago__text") or \
                              _pw_text(page, "time.job-posted-date")

            finally:
                browser.close()

        if not title or not company:
            raise JobFetchError(
                "Could not extract title or company from LinkedIn listing. "
                "The page structure may have changed.",
                url=url,
            )

        visa_eligible, sponsorship = detect_visa_signals(description)

        return JobListing(
            title=title,
            company=company,
            location=location or "",
            description=description,
            url=url,
            source="linkedin",
            work_type=work_type,
            date_posted=date_posted or None,
            visa_eligible=visa_eligible,
            sponsorship_available=sponsorship,
        )

    def _is_blocked(self, page) -> bool:
        """Heuristic: check whether LinkedIn is redirecting to a gate."""
        body_text = page.locator("body").inner_text()
        gate_signals = [
            "join linkedin",
            "sign in",
            "log in to see",
            "captcha",
        ]
        lower = body_text.lower()
        return any(signal in lower for signal in gate_signals)

    # ------------------------------------------------------------------
    # Manual fallback
    # ------------------------------------------------------------------

    def _manual_fallback(self, url: str, reason: str) -> JobListing:
        """Prompt the user to paste the job description when scraping fails."""
        print(
            f"\n[LinkedInFetcher] Automated fetch not possible ({reason}).\n"
            f"Please copy the full job description from:\n  {url}\n"
            "Then paste it below and press Enter twice when done:\n",
            file=sys.stderr,
        )

        lines: list[str] = []
        consecutive_blanks = 0
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line == "":
                consecutive_blanks += 1
                if consecutive_blanks >= 2:
                    break
            else:
                consecutive_blanks = 0
            lines.append(line)

        description = "\n".join(lines).strip()
        if not description:
            raise JobFetchError(
                f"No job description provided for LinkedIn listing ({reason}).",
                url=url,
            )

        # Best-effort parse of the pasted text.
        title = _extract_first_line(description) or "Unknown Title"
        visa_eligible, sponsorship = detect_visa_signals(description)

        return JobListing(
            title=title,
            company="Unknown (manual paste)",
            location="",
            description=description,
            url=url,
            source="linkedin",
            visa_eligible=visa_eligible,
            sponsorship_available=sponsorship,
        )


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------

def _pw_text(page, selector: str) -> str:
    """Return trimmed inner text for the first matching element, or ''."""
    el = page.query_selector(selector)
    return el.inner_text().strip() if el else ""


def _extract_work_type_from_text(text: str) -> str | None:
    lower = text.lower()
    if "full-time" in lower or "full time" in lower:
        return "full-time"
    if "part-time" in lower or "part time" in lower:
        return "part-time"
    if "contract" in lower or "casual" in lower:
        return "contract"
    return None


def _extract_first_line(text: str) -> str:
    """Return the first non-empty line of pasted text as a best-guess title."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:120]
    return ""
