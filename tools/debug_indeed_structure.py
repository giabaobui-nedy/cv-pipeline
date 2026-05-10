#!/usr/bin/env python3
"""
One-shot debug script — dumps the shape of Indeed's mosaic data so we can
fix the tile extraction path.

Run:
    .venv/bin/python tools/debug_indeed_structure.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from job_fetcher.base import _polite_delay, _random_headers

URL = (
    "https://au.indeed.com/jobs"
    "?q=junior+software+developer"
    "&l=melbourne+vic"
    "&sort=date"
)

JS_DUMP = """
() => {
    const d = window.mosaic?.providerData?.["mosaic-provider-jobcards"];
    if (!d) return { found: false, allProviders: Object.keys(window.mosaic?.providerData ?? {}) };

    const topKeys = Object.keys(d);

    const meta = d.metaData ?? {};
    const metaKeys = Object.keys(meta);

    // Walk every key in metaData and find arrays
    const arrays = {};
    for (const [k, v] of Object.entries(meta)) {
        if (Array.isArray(v)) arrays[k] = v.length;
        else if (v && typeof v === "object") {
            const subArrays = {};
            for (const [k2, v2] of Object.entries(v)) {
                if (Array.isArray(v2)) subArrays[k2] = v2.length;
            }
            if (Object.keys(subArrays).length) arrays[`metaData.${k}`] = subArrays;
        }
    }

    // Also check root-level arrays
    const rootArrays = {};
    for (const [k, v] of Object.entries(d)) {
        if (Array.isArray(v)) rootArrays[k] = v.length;
    }

    // Grab one sample item from whatever looks most like a job list
    let sample = null;
    const model = meta.mosaicProviderJobCardsModel ?? meta.jobCardsModel ?? {};
    const candidates = [model.results, model.tiles, d.results, d.tiles, d.jobsInResultSet];
    for (const c of candidates) {
        if (Array.isArray(c) && c.length > 0) {
            sample = Object.keys(c[0]);
            break;
        }
    }

    return {
        found: true,
        topKeys,
        metaKeys,
        rootArrays,
        nestedArrays: arrays,
        firstItemKeys: sample,
    };
}
"""

from playwright.sync_api import sync_playwright

print(f"\nFetching: {URL}\n")
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(
        user_agent=_random_headers()["User-Agent"],
        locale="en-AU",
        viewport={"width": 1280, "height": 900},
        extra_http_headers={"Accept-Language": "en-AU,en;q=0.9"},
    )
    page = ctx.new_page()
    page.goto(URL, timeout=30_000, wait_until="domcontentloaded")
    _polite_delay(3.0, 5.0)
    result = page.evaluate(JS_DUMP)
    browser.close()

print(json.dumps(result, indent=2))
print("\n--- paste this output back to diagnose the tile path ---\n")
