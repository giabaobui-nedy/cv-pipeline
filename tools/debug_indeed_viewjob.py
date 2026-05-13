#!/usr/bin/env python3
"""Debug script: open an Indeed viewjob URL with Playwright and dump what we see.

Usage:
    .venv/bin/python tools/debug_indeed_viewjob.py [url]

Default URL: https://au.indeed.com/viewjob?jk=293dbce22f025c9e
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from job_fetcher.base import _random_headers

URL = sys.argv[1] if len(sys.argv) > 1 else "https://au.indeed.com/viewjob?jk=293dbce22f025c9e"

JS_PROBE = """
() => {
    const out = {};
    // What top-level keys exist on window?
    out.windowKeys = Object.keys(window).filter(k =>
        k.startsWith('_') || k.startsWith('mosaic') || k.startsWith('next') ||
        ['initialData','reactInitialState','APP_INITIALDATA','_initialData'].includes(k)
    );
    // Try common job-data paths
    try { out._initialData_keys = Object.keys(window._initialData || {}); } catch(e) {}
    try { out.mosaic_keys = Object.keys(window.mosaic?.providerData || {}); } catch(e) {}
    try {
        const d = window._initialData;
        out.jobModel = (
            d?.jobInfoWrapperModel?.jobInfoModel
            || d?.viewJobData?.jobInfoWrapperModel?.jobInfoModel
            || null
        );
    } catch(e) {}
    // Page title + first <h1>
    out.pageTitle = document.title;
    const h1 = document.querySelector('h1');
    out.firstH1 = h1 ? h1.innerText : null;
    // Do key selectors exist?
    out.selectors = {
        jobDescriptionText: !!document.querySelector('#jobDescriptionText'),
        jobInfoHeader: !!document.querySelector('[data-testid="jobsearch-JobInfoHeader-title"]'),
        jobDescription: !!document.querySelector('[data-testid="job-description"]'),
        h1JobTitle: !!document.querySelector('h1.jobsearch-JobInfoHeader-title'),
    };
    return out;
}
"""

print(f"\nOpening: {URL}\n")

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(
        user_agent=_random_headers()["User-Agent"],
        locale="en-AU",
        viewport={"width": 1280, "height": 900},
        extra_http_headers={
            "Accept-Language": "en-AU,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    page = ctx.new_page()

    print("Navigating (wait_until=load) …")
    page.goto(URL, timeout=30_000, wait_until="load")

    print("Waiting 3s for React to hydrate …")
    import time; time.sleep(3)

    print("Evaluating JS probe …")
    result = page.evaluate(JS_PROBE)
    print("\n── JS probe result ──────────────────────────────")
    print(json.dumps(result, indent=2, default=str))

    html = page.content()
    out_path = REPO / "tools" / "debug_indeed_viewjob.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"\n── HTML saved → {out_path.relative_to(REPO)}  ({len(html):,} bytes)")
    print("   Open it in a browser or grep for keywords.\n")

    browser.close()
