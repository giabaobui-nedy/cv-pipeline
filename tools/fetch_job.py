#!/usr/bin/env python3
"""Fetch a job listing or search results page from SEEK, LinkedIn, or Indeed.

Single listing
--------------
    .venv/bin/python tools/fetch_job.py <url>
    .venv/bin/python tools/fetch_job.py <url> --json
    .venv/bin/python tools/fetch_job.py <url> --write
    .venv/bin/python tools/fetch_job.py <url> --write --slug my-slug --force

Search — single URL
--------------------
    .venv/bin/python tools/fetch_job.py --list <search-url>
    .venv/bin/python tools/fetch_job.py --list <search-url> --pages 3

Search — keyword shorthand (builds SEEK URL automatically)
-----------------------------------------------------------
    .venv/bin/python tools/fetch_job.py --search "junior software engineer"
    .venv/bin/python tools/fetch_job.py --search "junior software engineer" --location sydney
    .venv/bin/python tools/fetch_job.py --search "junior software engineer" --variants
    .venv/bin/python tools/fetch_job.py --search all --variants   # every group
    .venv/bin/python tools/fetch_job.py --list-groups             # show all keyword groups

Filter flags (work with --list and --search)
---------------------------------------------
    --pages N             paginate N pages per URL (default: 1)
    --source seek,indeed  sources to search (default: seek)
    --level junior,graduate
    --stack typescript,python,react,aws
    --min-salary 80000
    --arrangement hybrid,remote
    --exclude "clearance,defence,nv1"
    --visa-only
    --show-excluded
    --deep                fetch each listing's full description to resolve ? visa signals
                          AND re-classify seniority (e.g. "3+ years" → mid)
    --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import webbrowser
from dataclasses import asdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

try:
    from job_fetcher import JobFetcherRouter, is_visa_friendly
    from job_fetcher.models import JobFetchError, JobListing, JobStub
    from job_fetcher.fetchers.seek_search import SeekSearchScraper
    from job_fetcher.fetchers.indeed_search import (
        IndeedSearchScraper, build_indeed_url, INDEED_LOCATIONS,
    )
    from job_fetcher.filters import JobFilter, FilterResult, filter_stubs, classify_level
    from job_fetcher.seek_variants import (
        build_variant_urls, build_seek_url, expand_keywords,
        LOCATIONS, DEFAULT_LOCATION, list_groups,
    )
except ImportError:
    sys.exit(
        "job_fetcher package not found. Make sure you are running from cv-pipeline/ "
        "and that requirements.txt has been installed."
    )

# ---------------------------------------------------------------------------
# ANSI colours (no extra deps; gracefully stripped when stdout is not a tty)
# ---------------------------------------------------------------------------
_IS_TTY = sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _IS_TTY else text

BOLD   = lambda t: _c("1", t)
DIM    = lambda t: _c("2", t)
GREEN  = lambda t: _c("32", t)
YELLOW = lambda t: _c("33", t)
RED    = lambda t: _c("31", t)
CYAN   = lambda t: _c("36", t)


# ---------------------------------------------------------------------------
# Visa badge helpers (shared between single listing + search list)
# ---------------------------------------------------------------------------

def _visa_badge(visa_eligible) -> str:
    if visa_eligible is True:
        return GREEN("✓ open")
    if visa_eligible is False:
        return RED("✗ restricted")
    return YELLOW("? unknown")

def _sponsor_badge(sponsorship_available) -> str:
    if sponsorship_available:
        return GREEN("✓ sponsor")
    return DIM("—")


# ---------------------------------------------------------------------------
# Pretty-printer — single JobListing
# ---------------------------------------------------------------------------

def _field(label: str, value: str | None, fallback: str = "—") -> str:
    return f"  {BOLD(label + ':')} {value or DIM(fallback)}"

def pretty_print_listing(job: JobListing) -> None:
    source_tag = CYAN(f"[{job.source.upper()}]")
    print()
    print(f"{source_tag} {BOLD(job.title)}")
    print(f"  {job.company}  ·  {job.location or '—'}")
    print()
    print(_field("Salary",    job.salary))
    print(_field("Work type", job.work_type))
    print(_field("Posted",    job.date_posted))
    print()
    print(f"  {BOLD('Visa:')}    {_visa_badge(job.visa_eligible)}")
    print(f"  {BOLD('Sponsor:')} {_sponsor_badge(job.sponsorship_available)}")
    print()
    preview = job.description[:400].strip()
    if len(job.description) > 400:
        preview += DIM(" …")
    print(BOLD("Description preview:"))
    for line in preview.splitlines():
        print(f"  {line}")
    print()
    print(DIM(f"  URL: {job.url}"))
    print()


# ---------------------------------------------------------------------------
# Pretty-printer — search results list
# ---------------------------------------------------------------------------

_VISA_COL  = {True: GREEN("✓"), False: RED("✗"), None: YELLOW("?")}
_LEVEL_COL = {
    "intern":   DIM("I"),
    "graduate": CYAN("G"),
    "junior":   GREEN("J"),
    "mid":      YELLOW("M"),
    "senior":   RED("S"),
    "unknown":  DIM("·"),
}
_WORK_ABBR = {"full-time": "FT", "part-time": "PT", "contract": "CT"}


def pretty_print_stubs(
    result: "FilterResult",
    show_excluded: bool = False,
) -> None:
    stubs = result.matched

    print()
    header = (
        f"  {'#':>3}  {'V':1}  {'Sp':2}  {'Lv':2}  {'Tp':2}  "
        f"{'SALARY':<22}  {'COMPANY':<26}  TITLE"
    )
    print(BOLD(header))
    print(DIM("  " + "─" * 112))

    for i, stub in enumerate(stubs, 1):
        v    = _VISA_COL.get(stub.visa_eligible, YELLOW("?"))
        sp   = GREEN("✓") if stub.sponsorship_available else DIM("·")
        lv   = _LEVEL_COL.get(classify_level(stub), DIM("·"))
        wt   = _WORK_ABBR.get(stub.work_type or "", DIM("  "))
        sal  = _truncate(stub.salary or "", 22)
        co   = _truncate(stub.company, 26)
        ti   = _truncate(stub.title, 55)
        feat = CYAN(" ★") if stub.is_featured else ""
        print(f"  {i:>3}  {v}  {sp}   {lv}   {wt:<2}  {sal:<22}  {co:<26}  {ti}{feat}")

    print()
    summary = GREEN(f"  {len(stubs)} matched")
    if result.excluded:
        summary += DIM(f"  ·  {len(result.excluded)} excluded")
    summary += DIM(f"  ·  {result.total} total")
    print(summary)
    print()

    if show_excluded and result.excluded:
        print(DIM("  Excluded listings:"))
        for stub, reason in result.excluded:
            print(DIM(f"    ✗ {_truncate(stub.title, 45):<45}  @ {_truncate(stub.company, 26):<26}  [{reason}]"))
        print()

    print(DIM("  Legend — Visa: ✓open  ✗restricted  ?unknown"))
    print(DIM("  Level:  G=graduate  J=junior  M=mid  S=senior  I=intern  ·=unknown"))
    print(DIM("  Sponsor: ✓  |  Type: FT=full-time  PT=part-time  CT=contract  |  ★=featured"))
    print()


def _truncate(s: str, n: int) -> str:
    s = s.replace("\n", " ").strip()
    return s[:n - 1] + "…" if len(s) > n else s


# ---------------------------------------------------------------------------
# spec.yml bootstrap  (thin shim over create_spec logic)
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "application"

def write_spec(job: JobListing, slug: str, force: bool) -> None:
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML not installed. Run: pip install -r requirements.txt")

    import datetime as dt
    import importlib.util
    import tempfile

    spec_mod_path = REPO / "tools" / "create_spec.py"
    spec = importlib.util.spec_from_file_location("create_spec", spec_mod_path)
    cs = importlib.util.module_from_spec(spec)   # type: ignore[arg-type]
    spec.loader.exec_module(cs)                  # type: ignore[union-attr]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as fh:
        fh.write(job.description)
        tmp_path = Path(fh.name)

    try:
        ns = argparse.Namespace(
            company=job.company,
            role=job.title,
            source_url=job.url,
            date=dt.date.today().isoformat(),
            ad=tmp_path,
            slug=slug,
            write=False,
            force=force,
        )
        spec_dict = cs.build_spec(ns)
    finally:
        tmp_path.unlink(missing_ok=True)

    spec_dict["ad_raw"] = job.description
    notes: dict = {}
    if job.salary:
        notes["salary"] = job.salary
    if job.work_type:
        notes["work_type"] = job.work_type
    if job.visa_eligible is not None:
        notes["visa_eligible"] = job.visa_eligible
    if job.sponsorship_available:
        notes["sponsorship_available"] = True
    if notes:
        spec_dict["notes"] = notes

    rendered = yaml.dump(
        spec_dict,
        Dumper=cs.LiteralDumper,
        sort_keys=False,
        allow_unicode=True,
        width=88,
    )

    out = REPO / "job-ads" / slug / "spec.yml"
    if out.exists() and not force:
        sys.exit(
            f"Spec already exists: {out}\n"
            f"Pass --force to overwrite, or --slug <name> for a different slug."
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered)
    print(GREEN(f"✓ wrote {out.relative_to(REPO)}"))
    print(f"  next: {BOLD(f'tools/compile.sh {slug}')}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="fetch_job.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "url",
        nargs="?",
        help="Job listing or search results URL (SEEK, LinkedIn, or Indeed)",
    )

    # ── search results mode ──────────────────────────────────────────────
    ap.add_argument(
        "--list",
        metavar="SEARCH_URL",
        help=(
            "SEEK search results URL(s). Accepts a single URL or a "
            "comma-separated list to fetch multiple searches at once "
            "(results are deduplicated by job ID)."
        ),
    )
    ap.add_argument(
        "--search",
        metavar="KEYWORD",
        help=(
            "Build a SEEK search URL from a keyword phrase. "
            "Example: --search 'junior software engineer'. "
            "Use --variants to expand to related terms. "
            "Use --search all --variants for every built-in group."
        ),
    )
    ap.add_argument(
        "--location",
        metavar="LOCATION",
        default="melbourne",
        help=(
            "Location for --search. Named alias or raw SEEK location slug. "
            f"Named aliases: {', '.join(LOCATIONS)}. "
            "Default: melbourne"
        ),
    )
    ap.add_argument(
        "--variants",
        action="store_true",
        help=(
            "Expand --search to all related keyword variants and fetch them all. "
            "Results are deduplicated."
        ),
    )
    ap.add_argument(
        "--list-groups",
        action="store_true",
        help="Print all built-in keyword groups and exit.",
    )
    ap.add_argument(
        "--pages",
        type=int,
        default=1,
        metavar="N",
        help="Number of search result pages to fetch per URL (default: 1)",
    )
    ap.add_argument(
        "--source",
        metavar="SOURCES",
        default="seek",
        help=(
            "Comma-separated job sources to search. "
            "Values: seek, indeed. "
            "Default: seek. "
            "Example: --source seek,indeed"
        ),
    )

    # Filters (all used with --list)
    ap.add_argument(
        "--level",
        metavar="LEVELS",
        default="",
        help=(
            "Comma-separated experience levels to keep. "
            "Values: intern, graduate, junior, mid, senior, unknown. "
            "Example: --level junior,graduate"
        ),
    )
    ap.add_argument(
        "--stack",
        metavar="KEYWORDS",
        default="",
        help=(
            "Comma-separated tech keywords — keep listings that mention at least one. "
            "Example: --stack typescript,python,react,aws"
        ),
    )
    ap.add_argument(
        "--min-salary",
        type=float,
        default=None,
        metavar="AUD",
        help="Drop listings whose advertised minimum is below this value. Example: --min-salary 80000",
    )
    ap.add_argument(
        "--arrangement",
        metavar="MODES",
        default="",
        help=(
            "Comma-separated work arrangements to keep. "
            "Values: remote, hybrid, on-site. "
            "Listings with no arrangement signal are always kept. "
            "Example: --arrangement hybrid,remote"
        ),
    )
    ap.add_argument(
        "--exclude",
        metavar="PHRASES",
        default="",
        help=(
            "Comma-separated phrases — drop any listing whose title or preview "
            "contains any of them (case-insensitive). "
            "Example: --exclude 'clearance,defence,nv1'"
        ),
    )
    ap.add_argument(
        "--visa-only",
        action="store_true",
        help="Alias for --level with visa_friendly=True (shorthand)",
    )
    ap.add_argument(
        "--show-excluded",
        action="store_true",
        help="Print excluded listings with the reason they were dropped",
    )
    ap.add_argument(
        "--deep",
        action="store_true",
        help=(
            "Fetch each matched listing's full description to resolve ? visa signals "
            "AND re-classify seniority level (e.g. '3+ years required' → mid). "
            "Also improves stack and arrangement matching. "
            "Slower — one extra request per unknown-visa listing."
        ),
    )

    # ── single listing mode ──────────────────────────────────────────────
    ap.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of the pretty summary",
    )
    ap.add_argument(
        "--write",
        action="store_true",
        help="Bootstrap job-ads/<slug>/spec.yml from the fetched listing",
    )
    ap.add_argument(
        "--slug",
        default="",
        help="Override the auto-derived directory slug (used with --write)",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing spec.yml (used with --write)",
    )
    return ap


def _csv_set(raw: str) -> set[str]:
    """Split a comma-separated CLI string into a lowercase set, ignoring blanks."""
    return {s.strip().lower() for s in raw.split(",") if s.strip()}


def resolve_visa_signals(stubs: list[JobStub], router: "JobFetcherRouter") -> list[JobStub]:
    """Fetch the full listing for every stub whose visa_eligible is None.

    For each fetched listing we update the stub with:
    - Resolved visa_eligible / sponsorship_available from the full description.
    - The complete description text stored in description_preview so that the
      subsequent re-filter pass can use it for:
        • classify_level   — picks up "3+ years required" → mid, etc.
        • stub_matches_stack — broader keyword matching against full text.
        • detect_arrangement — finds hybrid/remote signals in the body.

    Stubs that are already True/False for visa are passed through untouched.
    Stubs that fail to fetch are left unchanged with a warning.
    """
    import dataclasses
    from job_fetcher.visa_filter import detect_visa_signals
    from job_fetcher.filters import classify_level

    unknown = [s for s in stubs if s.visa_eligible is None]
    if not unknown:
        return stubs

    # Indeed individual listing pages are blocked by Cloudflare even with
    # Playwright — skip them upfront with a single note rather than showing
    # N individual "skipped" lines.
    indeed_skipped = [s for s in unknown if s.source == "indeed"]
    fetchable     = [s for s in unknown if s.source != "indeed"]

    if indeed_skipped:
        print(
            YELLOW(f"  --deep: skipping {len(indeed_skipped)} Indeed listing(s) "
                   f"— Cloudflare blocks individual viewjob pages even with Playwright."),
            file=sys.stderr,
        )

    if not fetchable:
        print(file=sys.stderr)
        return stubs

    print(
        DIM(f"  --deep: fetching {len(fetchable)} full listings "
            f"(visa + seniority + stack) …"),
        file=sys.stderr,
    )

    stub_map = {s.url: s for s in stubs}

    for i, stub in enumerate(fetchable, 1):
        print(
            DIM(f"  [{i}/{len(fetchable)}] {_truncate(stub.title, 45)}"
                f" @ {_truncate(stub.company, 25)} …"),
            end="", flush=True, file=sys.stderr,
        )
        try:
            listing = router.fetch(stub.url)
            visa, sponsor = detect_visa_signals(listing.description)

            # Store the full description so re-filter sees complete text.
            updated = dataclasses.replace(
                stub,
                visa_eligible=visa,
                sponsorship_available=sponsor,
                description_preview=listing.description,  # full text, not 300-char slice
            )
            stub_map[stub.url] = updated

            # Report visa badge + any seniority change detected in full text.
            visa_badge = (
                GREEN("✓ open") if visa is True
                else RED("✗ restricted") if visa is False
                else YELLOW("?")
            )
            old_level = classify_level(stub)
            new_level = classify_level(updated)
            level_note = (
                f"  {DIM(f'level {old_level!r}→{new_level!r}')}"
                if new_level != old_level else ""
            )
            print(f" {visa_badge}{level_note}", file=sys.stderr)
        except JobFetchError as e:
            print(DIM(f" skipped ({e})"), file=sys.stderr)

    print(file=sys.stderr)
    # Return stubs in original order with updates applied.
    return [stub_map[s.url] for s in stubs]


# ---------------------------------------------------------------------------
# Interactive post-search picker
# ---------------------------------------------------------------------------

def _parse_picks(raw: str, n: int) -> list[int]:
    """Parse a user pick string into 0-based indices.

    Accepts:  "1 3 5"  |  "2-5"  |  "a" (all)  |  "" (skip)
    Out-of-range values are silently dropped.  Duplicates removed.
    """
    raw = raw.strip().lower()
    if not raw or raw in ("q", "n"):
        return []
    if raw == "a":
        return list(range(n))

    seen: set[int] = set()
    result: list[int] = []
    for token in raw.replace(",", " ").split():
        if "-" in token:
            parts = token.split("-", 1)
            try:
                lo, hi = int(parts[0]) - 1, int(parts[1]) - 1
                for i in range(lo, hi + 1):
                    if 0 <= i < n and i not in seen:
                        seen.add(i)
                        result.append(i)
            except ValueError:
                pass
        else:
            try:
                i = int(token) - 1
                if 0 <= i < n and i not in seen:
                    seen.add(i)
                    result.append(i)
            except ValueError:
                pass
    return result


def _interactive_picker(stubs: list["JobStub"], force: bool = False) -> None:
    """Post-search interactive prompts — only called in a live terminal session.

    Step 1: pick rows to open in the browser (non-blocking).
    Step 2: pick rows to fetch fully and write as spec.yml stubs.
    """
    if not stubs:
        return

    n = len(stubs)
    hint = f"1-{n}, ranges like 2-5, 'a'=all, Enter=skip"

    # ── Step 1: open in browser ──────────────────────────────────────────────
    print(BOLD(f"\n  Open in browser  ({hint}): "), end="", flush=True)
    try:
        raw = input().strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    picks = _parse_picks(raw, n)
    if picks:
        print()
        for i in picks:
            url = stubs[i].url
            print(f"  → {url}")
            webbrowser.open(url)
        print()
        print(DIM("  Tabs opened.  Read them, then come back here."))

    # ── Step 2: write spec.yml ───────────────────────────────────────────────
    print(BOLD(f"\n  Write spec.yml for which?  ({hint}): "), end="", flush=True)
    try:
        raw2 = input().strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    spec_picks = _parse_picks(raw2, n)
    if not spec_picks:
        print()
        return

    router = JobFetcherRouter()
    print()
    for i in spec_picks:
        stub = stubs[i]
        slug = _slugify(stub.company)
        out = REPO / "job-ads" / slug / "spec.yml"
        if out.exists() and not force:
            print(
                YELLOW(f"  ⚠  {out.relative_to(REPO)} already exists — "
                       f"skipping  (re-run with --force to overwrite)")
            )
            continue
        print(
            DIM(f"  Fetching {_truncate(stub.title, 40)}"
                f" @ {_truncate(stub.company, 25)} …"),
            end="", flush=True,
        )
        try:
            job = router.fetch(stub.url)
            print()
            write_spec(job, slug, force=force)
        except JobFetchError as exc:
            print(RED(f" failed ({exc})"))
    print()


def main() -> None:
    ap = build_parser()
    args = ap.parse_args()

    # ── list keyword groups and exit ─────────────────────────────────────
    if args.list_groups:
        print(BOLD("\nBuilt-in SEEK keyword groups:\n"))
        print(list_groups())
        print()
        print(DIM("  Use with: --search <group-name> --variants"))
        print(DIM(f"  Locations: {', '.join(LOCATIONS)}"))
        print()
        return

    # ── resolve search URLs from --list or --search ──────────────────────
    # Keyed by source name so we can dispatch to the right scraper.
    source_urls: dict[str, list[str]] = {}   # {"seek": [...], "indeed": [...]}
    sources = _csv_set(args.source) or {"seek"}

    if args.list:
        # Raw URL list — infer source from the URL itself.
        for u in (u.strip() for u in args.list.split(",") if u.strip()):
            src = "indeed" if "indeed.com" in u.lower() else "seek"
            source_urls.setdefault(src, []).append(u)

    elif args.search:
        if "seek" in sources:
            loc_slug = LOCATIONS.get(args.location.lower().replace(" ", "-"), args.location)
            if args.variants:
                keywords = expand_keywords(args.search)
                source_urls["seek"] = [build_seek_url(kw, loc_slug) for kw in keywords]
            else:
                source_urls["seek"] = [build_seek_url(args.search, loc_slug)]

        if "indeed" in sources:
            indeed_loc = INDEED_LOCATIONS.get(
                args.location.lower().replace(" ", "-"),
                args.location,
            )
            if args.variants:
                keywords = expand_keywords(args.search)
                source_urls["indeed"] = [build_indeed_url(kw, indeed_loc) for kw in keywords]
            else:
                source_urls["indeed"] = [build_indeed_url(args.search, indeed_loc)]

    if source_urls:
        all_search_urls = [u for urls in source_urls.values() for u in urls]
        total_requests = len(all_search_urls) * args.pages
        est_min = total_requests * 1
        est_max = total_requests * 9   # 5 s delay + 4 s inter-URL (Indeed is slower)

        # ── Pre-flight summary + polite-use warnings ─────────────────────
        print(file=sys.stderr)
        if len(all_search_urls) == 1:
            src_name = next(iter(source_urls))
            print(DIM(f"  [{src_name.upper()}] Scraping: {all_search_urls[0]}"), file=sys.stderr)
        else:
            src_labels = " + ".join(
                f"{len(v)} {k.upper()} URL{'s' if len(v) > 1 else ''}"
                for k, v in source_urls.items()
            )
            print(
                BOLD(f"  Fetching {src_labels} ({args.pages} page(s) each) …"),
                file=sys.stderr,
            )
            print(
                DIM(f"  ≈ {total_requests} requests  ·  est. {est_min}–{est_max} s"
                    f"  ·  spacing ~1–5 s per page + cooldown between URLs"),
                file=sys.stderr,
            )

        if args.pages > 3:
            print(
                YELLOW(
                    f"  ⚠  --pages {args.pages} will make {total_requests} requests."
                    f" Keep --pages ≤ 3 to be respectful of their servers."
                ),
                file=sys.stderr,
            )
        if total_requests > 30:
            print(
                YELLOW(
                    "  ⚠  Large batch — please don't repeat this run frequently."
                ),
                file=sys.stderr,
            )
        print(file=sys.stderr)

        # ── Fetch each source ─────────────────────────────────────────────
        stubs: list[JobStub] = []
        seen_urls: set[str] = set()

        for src, urls in source_urls.items():
            if src == "seek":
                scraper = SeekSearchScraper()
            elif src == "indeed":
                scraper = IndeedSearchScraper()
            else:
                print(YELLOW(f"  ⚠  Unknown source '{src}' — skipping."), file=sys.stderr)
                continue

            if len(urls) == 1:
                try:
                    new_stubs = scraper.fetch_all_pages(urls[0], max_pages=args.pages)
                    print(
                        DIM(f"  [{src.upper()}] {len(new_stubs)} listings fetched"),
                        file=sys.stderr,
                    )
                except JobFetchError as e:
                    print(RED(f"  [{src.upper()}] Error: {e}"), file=sys.stderr)
                    new_stubs = []
            else:
                new_stubs = scraper.fetch_multiple(
                    urls, max_pages=args.pages, verbose=True
                )

            # Deduplicate across sources by URL.
            for s in new_stubs:
                if s.url not in seen_urls:
                    seen_urls.add(s.url)
                    stubs.append(s)

        print(file=sys.stderr)
        if not stubs:
            print(YELLOW("No listings found."), file=sys.stderr)
            sys.exit(0)

        # Build filter from CLI args.
        f = JobFilter(
            levels=_csv_set(args.level),
            stack=_csv_set(args.stack),
            min_salary=args.min_salary,
            arrangements=_csv_set(args.arrangement),
            visa_friendly=args.visa_only,
            exclude_keywords=_csv_set(args.exclude),
        )
        result = filter_stubs(stubs, f)

        # --deep: fetch full listings for matched stubs with unknown visa signals,
        # then re-filter (some unknowns may now resolve to restricted).
        if args.deep and result.matched:
            router = JobFetcherRouter()
            resolved = resolve_visa_signals(result.matched, router)
            result = filter_stubs(resolved, f)

        if args.json:
            out = {
                "matched": [asdict(s) for s in result.matched],
                "excluded": [
                    {"stub": asdict(s), "reason": r}
                    for s, r in result.excluded
                ],
                "summary": result.summary(),
                "urls_searched": all_search_urls,
                "sources": list(source_urls.keys()),
                "deep": args.deep,
            }
            print(json.dumps(out, indent=2, default=str))
            return

        pretty_print_stubs(result, show_excluded=args.show_excluded)

        # Interactive browser-open + spec-write picker (live terminal only).
        if _IS_TTY and sys.stdin.isatty() and result.matched:
            _interactive_picker(result.matched, force=args.force)

        return

    # ── single listing mode ──────────────────────────────────────────────
    if not args.url:
        ap.error("Provide a URL, --list <search-url>, or --search <keyword>")

    router = JobFetcherRouter()
    print(DIM(f"Fetching {args.url} …"), file=sys.stderr)

    try:
        job = router.fetch(args.url)
    except JobFetchError as e:
        print(RED(f"Error: {e}"), file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(asdict(job), indent=2, default=str))
        return

    pretty_print_listing(job)

    if args.write:
        slug = args.slug or _slugify(job.company)
        write_spec(job, slug, args.force)


if __name__ == "__main__":
    main()
