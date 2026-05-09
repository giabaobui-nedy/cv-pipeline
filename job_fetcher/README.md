# job_fetcher

Automated job description fetcher and filter for the CV customiser pipeline.
Give it a SEEK URL (or a keyword) and get back structured listings with
automatic visa-eligibility detection, experience-level classification, and
tech-stack filtering.

---

## Installation

```bash
# From the cv-pipeline/ directory
pip install -r requirements.txt

# One-time Playwright setup — required for SEEK and LinkedIn (Cloudflare/JS)
.venv/bin/playwright install chromium
```

---

## CLI — `tools/fetch_job.py`

All commands are run from `cv-pipeline/`:

```bash
.venv/bin/python tools/fetch_job.py [options]
```

### Fetch a single listing

```bash
# Pretty-print a listing with visa badge
.venv/bin/python tools/fetch_job.py https://www.seek.com.au/job/91968438

# Raw JSON output (pipe-friendly)
.venv/bin/python tools/fetch_job.py https://www.seek.com.au/job/91968438 --json

# Fetch + immediately bootstrap job-ads/<slug>/spec.yml
.venv/bin/python tools/fetch_job.py https://www.seek.com.au/job/91968438 --write

# Override the folder slug
.venv/bin/python tools/fetch_job.py https://www.seek.com.au/job/91968438 --write --slug ucom-grad-swe

# Overwrite an existing spec
.venv/bin/python tools/fetch_job.py https://www.seek.com.au/job/91968438 --write --force
```

---

### Search results — `--list`

Scrape a SEEK search results page directly. Accepts one URL or a
comma-separated list (results are deduplicated by job ID).

```bash
# Single search page
.venv/bin/python tools/fetch_job.py \
  --list "https://au.seek.com/Junior-Software-Engineer-jobs/in-All-Melbourne-VIC"

# Paginate 3 pages (~60 listings)
.venv/bin/python tools/fetch_job.py \
  --list "https://au.seek.com/Junior-Software-Engineer-jobs/in-All-Melbourne-VIC" \
  --pages 3

# Multiple search URLs in one run (deduplicated)
.venv/bin/python tools/fetch_job.py \
  --list "https://au.seek.com/Junior-Software-Engineer-jobs/in-All-Melbourne-VIC,https://au.seek.com/Graduate-Software-Engineer-jobs/in-All-Melbourne-VIC"
```

---

### Search by keyword — `--search`

Builds the SEEK URL for you from a keyword phrase.

```bash
# Single keyword search, Melbourne (default location)
.venv/bin/python tools/fetch_job.py --search "junior software engineer"

# Different city
.venv/bin/python tools/fetch_job.py --search "junior software engineer" --location sydney

# Expand to all related keyword variants (Junior Developer, Graduate SWE, etc.)
# and deduplicate across all searches
.venv/bin/python tools/fetch_job.py --search "junior software engineer" --variants

# Every built-in keyword group at once
.venv/bin/python tools/fetch_job.py --search all --variants --location melbourne

# See all available keyword groups
.venv/bin/python tools/fetch_job.py --list-groups
```

**Location aliases** (use with `--location`):

| Alias | SEEK slug |
|---|---|
| `melbourne` *(default)* | `All-Melbourne-VIC` |
| `melbourne-cbd` | `Melbourne-CBD-Melbourne-VIC-3000` |
| `sydney` | `All-Sydney-NSW` |
| `brisbane` | `All-Brisbane-QLD` |
| `perth` | `All-Perth-WA` |
| `adelaide` | `All-Adelaide-SA` |
| `canberra` | `All-Canberra-ACT` |
| `remote` / `australia` | `Australia` |

---

### Filter flags

All filter flags work with `--list` and `--search`. They are AND-ed together.

| Flag | What it does |
|---|---|
| `--pages N` | Paginate N pages per URL (default: 1, ~20 listings/page) |
| `--level LEVELS` | Keep only listings whose detected level is in this comma-separated set. Values: `intern`, `graduate`, `junior`, `mid`, `senior`, `unknown` |
| `--stack KEYWORDS` | Keep listings that mention at least one of these tech keywords in title or preview. Example: `typescript,python,react,aws` |
| `--min-salary AUD` | Drop listings whose advertised minimum is below this value. Listings with no salary are kept. |
| `--arrangement MODES` | Keep listings matching at least one mode. Values: `remote`, `hybrid`, `on-site`. Listings with no arrangement signal are always kept. |
| `--exclude PHRASES` | Drop any listing whose title or preview contains any of these comma-separated phrases (case-insensitive). |
| `--visa-only` | Drop listings explicitly restricted to citizens/PR (`visa_eligible = False`). |
| `--deep` | Fetch each matched listing's full description to resolve `?` visa signals. One extra request per unknown — slower but accurate. |
| `--show-excluded` | Print every excluded listing with the exact reason it was dropped. |
| `--json` | Output matched + excluded results as JSON instead of the terminal table. |

---

### Recommended workflow

**Step 1 — broad sweep, fast**

```bash
.venv/bin/python tools/fetch_job.py \
  --search "junior software engineer" \
  --variants \
  --pages 2 \
  --level junior,graduate,unknown \
  --stack typescript,python,react,aws,node \
  --arrangement hybrid,remote \
  --exclude "clearance,nv1,defence,10+ years" \
  --visa-only \
  --show-excluded
```

This fetches up to ~200 listings across 10 URL variants, deduplicates,
filters, and shows you the shortlist in one table.

**Step 2 — resolve the `?` visa signals**

```bash
# Re-run the same command with --deep added
.venv/bin/python tools/fetch_job.py \
  --search "junior software engineer" \
  --variants \
  --level junior,graduate,unknown \
  --stack typescript,python,react,aws,node \
  --visa-only \
  --deep
```

`--deep` fetches the full description of every `?` listing, re-runs visa
detection, and drops any newly-resolved citizen/PR-only roles automatically.

**Step 3 — pick, browse, and write specs interactively**

When the search results table prints in a live terminal, you'll get two prompts automatically:

```
  Open in browser  (1-24, ranges like 2-5, 'a'=all, Enter=skip): 1 4 7
  → https://seek.com.au/job/111
  → https://seek.com.au/job/444
  → https://seek.com.au/job/777

  Tabs opened.  Read them, then come back here.

  Write spec.yml for which?  (1-24, ranges like 2-5, 'a'=all, Enter=skip): 1 7
  Fetching Software Engineer @ Forest One …
  ✓ wrote job-ads/forest-one/spec.yml
    next: tools/compile.sh forest-one
  Fetching Graduate Engineer @ Twilio …
  ✓ wrote job-ads/twilio/spec.yml
    next: tools/compile.sh twilio
```

- Prompt 1 opens the selected rows in your browser (non-blocking — tabs appear instantly).
- You read the ads at your own pace, then come back.
- Prompt 2 fetches the full listing for each chosen row and writes `job-ads/<slug>/spec.yml`.
- Both prompts accept: space-separated numbers (`1 3 5`), ranges (`2-5`), `a` for all, or Enter to skip.
- Prompts are skipped automatically when output is piped or `--json` is used.

Use `--force` to overwrite an existing spec.

---

### Table output legend

```
  #   V  Sp  Lv  Tp  SALARY                  COMPANY                     TITLE
  ───────────────────────────────────────────────────────────────────────────────
    1  ?  ·    J  FT  $105,000–$125,000        Energetica                  Software Engineer ★
    2  ✓  ✓    G  FT  $70,000                  UCOM                        Graduate Software Engineer
   16  ✗  ·    ·  CT                           AJQ                         Software Engineer
```

| Column | Values |
|---|---|
| `V` (Visa) | `✓` open · `✗` restricted · `?` unknown — use `--deep` to resolve |
| `Sp` (Sponsor) | `✓` sponsorship offered · `·` none detected |
| `Lv` (Level) | `G` graduate · `J` junior · `M` mid · `S` senior · `I` intern · `·` unknown |
| `Tp` (Type) | `FT` full-time · `PT` part-time · `CT` contract |
| `★` | Featured listing |

---

## Python API

### Fetch a single listing

```python
from job_fetcher import JobFetcherRouter, is_visa_friendly
from job_fetcher.models import JobFetchError

router = JobFetcherRouter()
try:
    job = router.fetch("https://www.seek.com.au/job/91968438")
except JobFetchError as e:
    print(f"Failed: {e}")  # e.url contains the failing URL
    raise

print(job.title, "@", job.company)
print("visa_eligible:", job.visa_eligible)   # True | False | None
if is_visa_friendly(job):
    print("Worth applying!")
```

### Scrape search results

```python
from job_fetcher.fetchers.seek_search import SeekSearchScraper
from job_fetcher.seek_variants import build_variant_urls, LOCATIONS

scraper = SeekSearchScraper()

# Single page
stubs = scraper.fetch_page(
    "https://au.seek.com/Junior-Software-Engineer-jobs/in-All-Melbourne-VIC"
)

# Paginate
stubs = scraper.fetch_all_pages(url, max_pages=3)

# Multiple URLs, deduplicated
urls = build_variant_urls("junior software engineer", LOCATIONS["melbourne"])
stubs = scraper.fetch_multiple(urls, max_pages=2, verbose=True)
```

### Filter a stub list

```python
from job_fetcher.filters import JobFilter, filter_stubs, classify_level

f = JobFilter(
    levels={"junior", "graduate", "unknown"},
    stack={"typescript", "python", "react", "aws"},
    min_salary=70_000,
    arrangements={"hybrid", "remote"},
    visa_friendly=True,
    exclude_keywords={"clearance", "nv1", "defence"},
)
result = filter_stubs(stubs, f)

print(result.summary())   # "12 matched / 8 excluded / 20 total"
for stub in result.matched:
    level = classify_level(stub)
    print(f"[{level}] {stub.title} @ {stub.company}")
```

### Build SEEK URLs

```python
from job_fetcher.seek_variants import (
    build_seek_url, build_variant_urls,
    expand_keywords, LOCATIONS, list_groups,
)

# Single URL
url = build_seek_url("Junior Software Engineer", "All-Melbourne-VIC")

# All variants for a keyword
urls = build_variant_urls("junior software engineer", LOCATIONS["sydney"])

# What keywords expand to
print(expand_keywords("fullstack"))
# → ["Junior Full Stack Developer", "Junior Full Stack Engineer", ...]

# See all groups
print(list_groups())
```

---

## Supported sources

| Source | Domain | Fetch technique |
|---|---|---|
| SEEK listings | `seek.com.au`, `au.seek.com` | **Playwright** (Cloudflare requires real browser) |
| SEEK search | `seek.com.au` search URLs | `requests` + BeautifulSoup (Redux JSON blob) |
| LinkedIn | `linkedin.com/jobs` | Playwright → manual paste fallback |
| Indeed | `au.indeed.com` | `requests` + BeautifulSoup (JSON-LD → DOM) |

---

## Visa detection reference

Evaluation order: **restricted beats open** — a "no sponsorship" phrase
cannot accidentally trigger the open path.

**`visa_eligible = False` — restricted signals**

| Phrase pattern | Example |
|---|---|
| Citizenship requirement | "must be an Australian citizen" |
| PR or citizenship | "Australian citizen or permanent resident" |
| Working rights + qualifier | "full Australian working rights (PR or Citizenship)" |
| Open-only phrasing | "This role is open only to Australian citizens or permanent residents" |
| Security clearance | "must hold NV1 / baseline clearance" (implies citizenship) |
| Temporary visa exclusion | "Temporary work visas are not available" |

**`visa_eligible = True` — open signals**

| Phrase pattern | Example |
|---|---|
| Explicit welcome | "open to all work rights" |
| International | "international applicants welcome" |
| Visa sponsorship | "visa sponsorship available / provided / considered" |
| Sponsorship offer | "sponsorship available for the right candidate" |
| Specific visas | "482 / TSS / 457 visa considered" |
| Temp residents | "temporary residents welcome" |

**`visa_eligible = None` — ambiguous (kept, not auto-excluded)**

| Phrase | Why it's ambiguous |
|---|---|
| "full working rights required" | A 485 holder has full work rights — may still be eligible |
| "sponsorship is not available" alone | Doesn't exclude 485 holders who already have work rights |

---

## Architecture

### How the modules connect

```
╔══════════════════════════════════════════════════════════════════════════╗
║  tools/fetch_job.py  (CLI entry point)                                   ║
║                                                                          ║
║  ┌─────────────────────────┐   ┌──────────────────────────────────────┐ ║
║  │  Single listing mode    │   │  Search / list mode                  │ ║
║  │  fetch_job.py <url>     │   │  --search / --list / --variants      │ ║
║  └────────────┬────────────┘   └─────────────┬────────────────────────┘ ║
╚═══════════════╪═════════════════════════════╪══════════════════════════╝
                │                             │
                ▼                             ▼
  ┌─────────────────────────┐   ┌─────────────────────────────────────┐
  │   router.py             │   │   seek_variants.py                  │
  │   JobFetcherRouter      │   │   build_variant_urls()              │
  │                         │   │   expand_keywords()                 │
  │   can_handle(url) ──────┼──►│   KEYWORD_GROUPS / LOCATIONS        │
  │   delegates to ▼        │   └──────────────┬──────────────────────┘
  └─────────────────────────┘                  │ list[url]
                │                              ▼
                │                ┌─────────────────────────────────────┐
                │                │   fetchers/seek_search.py           │
                │                │   SeekSearchScraper                 │
                │                │                                     │
                │                │   fetch_page()                      │
                │                │   fetch_all_pages()                 │
                │                │   fetch_multiple() ─► dedup by URL  │
                │                │                                     │
                │                │   parse: Redux JSON blob            │
                │                │          → DOM card fallback        │
                │                └──────────────┬──────────────────────┘
                │                               │ list[JobStub]
                │                               ▼
                │                ┌─────────────────────────────────────┐
                │                │   filters.py                        │
                │                │   filter_stubs(stubs, JobFilter)    │
                │                │                                     │
                │                │   • classify_level()  (title regex) │
                │                │   • stub_matches_stack()            │
                │                │   • _parse_salary_min()             │
                │                │   • detect_arrangement()            │
                │                └──────────────┬──────────────────────┘
                │                               │ FilterResult
                │                               │ (matched / excluded)
                │                               │
                │          ┌────────────────────┘
                │          │  --deep flag: fetch full listing
                │          │  for each stub with visa_eligible = None
                │          ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  fetchers/                                                          │
  │                                                                     │
  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
  │  │  seek.py         │  │  linkedin.py     │  │  indeed.py       │  │
  │  │  SeekFetcher     │  │  LinkedInFetcher │  │  IndeedFetcher   │  │
  │  │                  │  │                  │  │                  │  │
  │  │  Playwright      │  │  Playwright      │  │  requests + BS4  │  │
  │  │  (Cloudflare CF) │  │  → paste prompt  │  │  JSON-LD → DOM   │  │
  │  │  JSON-LD → DOM   │  │  if blocked      │  │  fallback        │  │
  │  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
  └───────────┼────────────────────┼─────────────────────┼─────────────┘
              │                    │                      │
              └────────────────────┴──────────────────────┘
                                   │ JobListing
                                   ▼
              ┌────────────────────────────────────────────┐
              │  visa_filter.py                            │
              │  detect_visa_signals(description)          │
              │                                            │
              │  Priority order (restrictions win):        │
              │    1. _CITIZEN_ONLY_RE  → (False, None)   │
              │    2. _SPONSORSHIP_RE   → (True,  True)   │
              │    3. _OPEN_RE          → (True,  None)   │
              │    4. fallback          → (None,  None)   │
              └────────────────────┬───────────────────────┘
                                   │ visa_eligible, sponsorship_available
                                   ▼
              ┌────────────────────────────────────────────┐
              │  models.py                                 │
              │                                            │
              │  JobListing  — full description + metadata │
              │  JobStub     — search result preview only  │
              │  JobFetchError — structured error + url    │
              └────────────────────────────────────────────┘
```

### Data flow summary

```
User runs CLI
    │
    ├─► --search / --list / --variants
    │       │
    │       ├─► seek_variants.py  builds list of SEEK search URLs
    │       │
    │       ├─► SeekSearchScraper.fetch_multiple()
    │       │       fetches search result pages (requests + BS4)
    │       │       returns list[JobStub]  ← preview text only
    │       │
    │       ├─► filter_stubs(stubs, JobFilter)
    │       │       level / stack / salary / arrangement / visa / exclude
    │       │       returns FilterResult(matched, excluded)
    │       │
    │       └─► --deep: for each stub with visa_eligible = None
    │               JobFetcherRouter.fetch(stub.url)  ← full description
    │               detect_visa_signals(full_text)
    │               re-filter
    │
    └─► <url>  (single listing)
            │
            ├─► JobFetcherRouter.fetch(url)
            │       can_handle() picks SeekFetcher / LinkedInFetcher / IndeedFetcher
            │       returns JobListing  ← full description + visa signals
            │
            └─► --write: create_spec.py  →  job-ads/<slug>/spec.yml
```

### Module structure

```
job_fetcher/
├── __init__.py          # Public exports
├── models.py            # JobListing, JobStub, JobFetchError dataclasses
├── base.py              # JobFetcher ABC + _random_headers() + _polite_delay()
├── visa_filter.py       # detect_visa_signals() + is_visa_friendly()
├── filters.py           # JobFilter, filter_stubs(), classify_level()
├── seek_variants.py     # SEEK URL builder + keyword expansion groups
├── router.py            # JobFetcherRouter — URL → fetcher dispatch
└── fetchers/
    ├── seek.py          # SeekFetcher        (Playwright)
    ├── seek_search.py   # SeekSearchScraper  (requests + BS4)
    ├── linkedin.py      # LinkedInFetcher    (Playwright → paste fallback)
    └── indeed.py        # IndeedFetcher      (requests + BS4)
```

## Error handling

Every fetcher raises `JobFetchError` on failure — never a raw exception.

| Situation | Error message |
|---|---|
| SEEK HTTP 403 (Cloudflare) | "SEEK blocked the request — try again or check Playwright is installed" |
| LinkedIn sign-in gate | Degrades to interactive paste prompt (no crash) |
| Playwright not installed | Clear install instruction in the error |
| Indeed CAPTCHA | "Try again in a few minutes" |
| No fetcher for URL | Lists all registered fetchers |
| Job removed (404/410) | "listing may have been removed" |
