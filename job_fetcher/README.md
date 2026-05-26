# job_fetcher

Automated job description fetcher and filter for the CV customiser pipeline.
Give it a keyword (or a URL) and get back a filtered, ranked shortlist of
listings from **SEEK and Indeed** with automatic visa-eligibility detection,
experience-level classification, tech-stack matching, and an interactive
browser-open + `spec.yml` writer at the end.

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

Scrape a search results page directly. Accepts one URL or a comma-separated
list (results are deduplicated by job ID). SEEK and Indeed URLs are both
supported and auto-detected.

```bash
# Single SEEK search page
.venv/bin/python tools/fetch_job.py \
  --list "https://au.seek.com/Junior-Software-Engineer-jobs/in-All-Melbourne-VIC"

# Single Indeed search page
.venv/bin/python tools/fetch_job.py \
  --list "https://au.indeed.com/jobs?q=junior+software+engineer&l=Melbourne+VIC"

# Paginate 3 pages (~60 listings)
.venv/bin/python tools/fetch_job.py \
  --list "https://au.seek.com/Junior-Software-Engineer-jobs/in-All-Melbourne-VIC" \
  --pages 3

# Mix SEEK + Indeed URLs in one run (deduplicated across sources)
.venv/bin/python tools/fetch_job.py \
  --list "https://au.seek.com/Junior-Software-Engineer-jobs/in-All-Melbourne-VIC,https://au.indeed.com/jobs?q=junior+software+engineer&l=Melbourne+VIC"
```

---

### Search by keyword — `--search`

Builds search URLs from a keyword phrase. Use `--source` to control which
job boards to query (default: SEEK only).

```bash
# SEEK only (default)
.venv/bin/python tools/fetch_job.py --search "junior software engineer"

# Indeed only
.venv/bin/python tools/fetch_job.py --search "junior software engineer" --source indeed

# Both SEEK and Indeed in one run (results merged and deduplicated)
.venv/bin/python tools/fetch_job.py --search "junior software engineer" --source seek,indeed

# Different city
.venv/bin/python tools/fetch_job.py --search "junior software engineer" \
  --source seek,indeed --location sydney

# Expand SEEK to all keyword variants + Indeed in parallel
.venv/bin/python tools/fetch_job.py --search "junior software engineer" \
  --variants --source seek,indeed

# Every built-in keyword group at once (SEEK)
.venv/bin/python tools/fetch_job.py --search all --variants --location melbourne

# See all available keyword groups
.venv/bin/python tools/fetch_job.py --list-groups
```

**Location aliases** (used with `--location` for both SEEK and Indeed):

| Alias | SEEK slug | Indeed string |
|---|---|---|
| `melbourne` *(default)* | `All-Melbourne-VIC` | `Melbourne VIC` |
| `sydney` | `All-Sydney-NSW` | `Sydney NSW` |
| `brisbane` | `All-Brisbane-QLD` | `Brisbane QLD` |
| `perth` | `All-Perth-WA` | `Perth WA` |
| `adelaide` | `All-Adelaide-SA` | `Adelaide SA` |
| `canberra` | `All-Canberra-ACT` | `Canberra ACT` |
| `remote` / `australia` | `Australia` | `Remote` / `Australia` |

> **Note on Indeed scraping:** Indeed's page structure changes frequently.
> The scraper tries an embedded JSON blob first, then falls back to DOM
> parsing. If results seem thin, Indeed may be serving a bot-detection page —
> wait a few minutes before retrying.

---

### Filter flags

All filter flags work with `--list` and `--search`. They are AND-ed together.

| Flag | What it does |
|---|---|
| `--pages N` | Paginate N pages per URL (default: 1, ~20 listings/page on SEEK, ~10 on Indeed) |
| `--source SOURCES` | Comma-separated job boards to query. Values: `seek`, `indeed`. Default: `seek`. |
| `--level LEVELS` | Keep only listings whose detected level is in this comma-separated set. Values: `intern`, `graduate`, `junior`, `mid`, `senior`, `unknown` |
| `--stack KEYWORDS` | Keep listings that mention at least one of these tech keywords in title or preview. Example: `typescript,python,react,aws`. Also useful as an industry filter — adding generic terms like `software,developer,engineer` blocks off-domain noise (e.g. "Associate Dentist" sneaking in via the `associate` → junior signal on Indeed). |
| `--min-salary AUD` | Drop listings whose advertised minimum is below this value. Listings with no salary are kept. |
| `--arrangement MODES` | Keep listings matching at least one mode. Values: `remote`, `hybrid`, `on-site`. Listings with no arrangement signal are always kept. |
| `--exclude PHRASES` | Drop any listing whose title or preview contains any of these comma-separated phrases (case-insensitive). |
| `--title KEYWORDS` | Keep only listings whose **title** contains at least one of these words (whole-word, case-insensitive). Essential for Indeed where searches like "junior software engineer" return retail, food-service, and trade roles. Example: `--title software,developer,engineer,devops,programmer`. |
| `--visa-only` | Drop listings explicitly restricted to citizens/PR (`visa_eligible = False`). |
| `--deep` | Fetch the full description for every `?`-visa listing. Re-runs **visa detection**, **seniority re-classification** (e.g. "3+ years required" → mid), and improves stack + arrangement matching. One extra request per unknown listing. |
| `--show-excluded` | Print every excluded listing with the exact reason it was dropped. |
| `--json` | Output matched + excluded results as JSON instead of the terminal table. |

#### Level classification rules

`classify_level` uses a **two-pass title-first** strategy:

| Title signal | Description signal | Result |
|---|---|---|
| "Junior …" or "Junior/Mid …" | anything | `junior` — title entry-level signal wins |
| "Senior Associate …" | — | `senior` — senior overrides entry-level qualifier |
| "Software Developer" | "3+ years required" | `mid` — no title signal, YoE from description |
| "Software Developer" | "5+ years required" | `senior` |
| "Engineering Manager" | — | `senior` — management roles mapped to senior |
| "Software Developer" | (none) | `unknown` |

**Flexible "Junior to Mid" roles:** these are classified as `junior` so they
pass through `--level junior,graduate,unknown`. If you also want strict mid
roles, add `mid` to the filter: `--level junior,graduate,mid,unknown`.

---

### Recommended workflow

**Step 1 — broad sweep across SEEK + Indeed**

```bash
.venv/bin/python tools/fetch_job.py \
  --search "junior software engineer" \
  --source seek,indeed \
  --variants \
  --pages 2 \
  --level junior,graduate,unknown \
  --stack typescript,python,react,aws \
  --title "software,developer,engineer,devops,programmer" \
  --exclude "clearance,nv1,defence,10+ years,C#" \
  --visa-only
```

Fetches up to ~200 SEEK listings (across keyword variants) + Indeed results,
deduplicates across sources, filters, and prints a single ranked table.

**Step 2 — `--deep`: resolve visa signals AND re-check seniority**

```bash
.venv/bin/python tools/fetch_job.py \
  --search "junior software engineer" \
  --source seek \       
  --variants \
  --level junior,graduate,unknown \
  --stack typescript,python,react,aws \     
  --visa-only
  --deep
```

For every `?`-visa listing the full description is fetched and the stub is
updated with:

- **Resolved visa signal** (`?` → `✓` or `✗`)
- **Re-classified seniority** — a stub with no title signal (unknown) that
  says "3+ years required" in the body is bumped to `mid` and excluded
- **Better stack + arrangement matching** from the full text

Progress is shown inline:

```
  [3/12] Software Developer @ Acme …  ✓ open  level 'unknown'→'mid'
  [7/12] Platform Engineer @ Axsys …  ✗ restricted
```

**Step 3 — interactive picker: browse then write specs**

After the table prints in a live terminal, two prompts appear automatically:

```
  Open in browser  (1-24, ranges like 2-5, 'a'=all, Enter=skip): 1 4 7
  → https://seek.com.au/job/111
  → https://au.indeed.com/viewjob?jk=abc123
  → https://seek.com.au/job/777

  Tabs opened.  Read them, then come back here.

  Write spec.yml for which?  (1-24, ranges like 2-5, 'a'=all, Enter=skip): 1 7
  Fetching Software Engineer @ Forest One …
  ✓ wrote job-ads/forest-one/spec.yml
    next: tools/compile.sh forest-one
```

- Prompt 1 opens tabs instantly (non-blocking). You read at your own pace.
- Prompt 2 fetches the full listing + writes `job-ads/<slug>/spec.yml`.
- Input: space-separated numbers (`1 3 5`), ranges (`2-5`), `a`=all, Enter=skip.
- Prompts are skipped when output is piped or `--json` is active.
- Pass `--force` to overwrite an existing spec.

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

| Source | Domain | Individual fetch | Search scraping |
|---|---|---|---|
| SEEK | `seek.com.au`, `au.seek.com` | Playwright (Cloudflare) | `requests` + BS4 (Redux JSON blob → DOM) |
| Indeed | `au.indeed.com` | `requests` + BS4 (JSON-LD → DOM) | Playwright fallback when `requests` hits 403 (Mosaic JS → DOM) |
| LinkedIn | `linkedin.com/jobs` | Playwright → manual paste fallback | ✗ (login wall / aggressive bot detection) |

Use `--source seek,indeed` to query both boards in one run. LinkedIn can be
searched manually by opening `https://www.linkedin.com/jobs/search/?keywords=<query>&location=<location>` in your browser.

---

## How Indeed search was added (extending the architecture)

The architecture uses the **Strategy Pattern** — every job board is its own
class, and the CLI/router never needs to change when a new source is added.
Adding Indeed search required only three steps:

### 1. New scraper class — `fetchers/indeed_search.py`

Mirrors the structure of `SeekSearchScraper` exactly:

```
SeekSearchScraper                    IndeedSearchScraper
──────────────────                   ───────────────────
fetch_page(url, page)       →        fetch_page(url, page)
fetch_all_pages(url, n)     →        fetch_all_pages(url, n)
fetch_multiple(urls, …)     →        fetch_multiple(urls, …)
_parse_redux_json(html)     →        _parse_mosaic_json(html)   ← different blob key
_parse_dom(soup)            →        _parse_dom(soup)           ← different CSS selectors
```

**Key difference — bot detection:**
Indeed returns `403 Forbidden` to plain `requests`. `fetch_page` handles
this transparently with a two-stage strategy:

```
Stage 1: requests (fast, no overhead)
  ├─ 200 OK + no CAPTCHA → parse Mosaic JSON blob from HTML
  │                         fall back to DOM card parsing
  └─ 403 / CAPTCHA ──────────────────────────────────────────┐
                                                              ▼
Stage 2: Playwright (headless Chromium)
  ├─ page.evaluate() extracts window.mosaic.providerData["mosaic-provider-jobcards"]
  │  directly from the live JS state — richer and more reliable than HTML regex
  └─ DOM parse of fully-rendered HTML as final fallback
```

### 2. URL builder — `build_indeed_url()` + `INDEED_LOCATIONS`

```python
# fetchers/indeed_search.py
def build_indeed_url(query: str, location: str) -> str:
    return f"https://au.indeed.com/jobs?q={quote_plus(query)}&l={quote_plus(location)}&sort=date"

INDEED_LOCATIONS = {
    "melbourne": "Melbourne VIC",
    "sydney":    "Sydney NSW",
    ...
}
```

The same `--location` aliases used for SEEK now also map to Indeed location
strings via `INDEED_LOCATIONS`.

### 3. CLI dispatch — `--source` flag in `tools/fetch_job.py`

The CLI builds a `source_urls` dict keyed by source name and instantiates
the right scraper for each:

```python
if src == "seek":
    scraper = SeekSearchScraper()
elif src == "indeed":
    scraper = IndeedSearchScraper()

new_stubs = scraper.fetch_all_pages(url, max_pages=args.pages)
```

Results from both scrapers are merged and deduplicated by URL before
filtering. The rest of the pipeline (filters, `--deep`, interactive picker,
`write_spec`) is **source-agnostic** and required no changes.

### Adding another source in the future

To add, say, Glassdoor:

1. Create `fetchers/glassdoor_search.py` with the same three public methods
2. Add `build_glassdoor_url()` and a location map
3. Add `"glassdoor"` to the `--source` dispatch block in `fetch_job.py`

The filter, visa detection, level classification, and interactive picker are
all unchanged.

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
  │   JobFetcherRouter      │   │   build_variant_urls()   (SEEK)     │
  │                         │   │   build_indeed_url()     (Indeed)   │
  │   can_handle(url) ──────┼──►│   KEYWORD_GROUPS / LOCATIONS        │
  │   delegates to ▼        │   └──────────────┬──────────────────────┘
  └─────────────────────────┘                  │ list[url]  per source
                │                              ▼
                │          ┌─────────────────────────────────────────────┐
                │          │   --source seek,indeed dispatch              │
                │          │                                             │
                │          │  ┌────────────────────┐ ┌─────────────────┐ │
                │          │  │ seek_search.py      │ │ indeed_search.py│ │
                │          │  │ SeekSearchScraper   │ │ IndeedScraper   │ │
                │          │  │                     │ │                 │ │
                │          │  │ requests + BS4      │ │ requests first  │ │
                │          │  │ Redux JSON blob     │ │ → Playwright if │ │
                │          │  │ → DOM fallback      │ │   403 detected  │ │
                │          │  │                     │ │ Mosaic JS blob  │ │
                │          │  │ fetch_multiple()    │ │ → DOM fallback  │ │
                │          │  └────────┬────────────┘ └──────┬──────────┘ │
                │          │           └──────────┬──────────┘            │
                │          │                      │ merged + dedup by URL │
                │          └──────────────────────┼───────────────────────┘
                │                                 │ list[JobStub]
                │                                 ▼
                │                ┌─────────────────────────────────────┐
                │                │   filters.py                        │
                │                │   filter_stubs(stubs, JobFilter)    │
                │                │                                     │
                │                │   • classify_level()                │
                │                │       Pass 1: title only            │
                │                │         (junior beats mid in title) │
                │                │       Pass 2: full text (YoE etc.)  │
                │                │   • stub_matches_stack()            │
                │                │   • _parse_salary_min()             │
                │                │   • detect_arrangement()            │
                │                └──────────────┬──────────────────────┘
                │                               │ FilterResult
                │                               │ (matched / excluded)
                │                               │
                │          ┌────────────────────┘
                │          │  --deep: for each stub with visa = ?
                │          │    fetch full listing → re-run visa + level
                │          ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  fetchers/  (individual listing fetchers — source-agnostic router)  │
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
    ├─► --search / --list / --variants   (with --source seek,indeed)
    │       │
    │       ├─► seek_variants.py  builds SEEK search URLs from keyword
    │       │   build_indeed_url()  builds Indeed search URLs
    │       │
    │       ├─► SeekSearchScraper.fetch_multiple()     ─┐
    │       │       requests + BS4 (Redux JSON → DOM)   │ merged +
    │       ├─► IndeedSearchScraper.fetch_multiple()   ─┤ deduplicated
    │       │       requests → Playwright fallback       │ by URL
    │       │       (Mosaic JS blob → DOM)              ─┘
    │       │       returns list[JobStub]  ← preview text only
    │       │
    │       ├─► filter_stubs(stubs, JobFilter)
    │       │       level / stack / salary / arrangement / visa / exclude
    │       │       classify_level() — two-pass, title-first
    │       │       returns FilterResult(matched, excluded)
    │       │
    │       ├─► --deep: for each stub with visa_eligible = None
    │       │       JobFetcherRouter.fetch(stub.url)  ← full description
    │       │       detect_visa_signals(full_text)   → resolve visa
    │       │       classify_level(stub_with_full_desc) → resolve seniority
    │       │       re-filter
    │       │
    │       └─► interactive picker (live terminal only)
    │               prompt 1: open selected rows in browser
    │               prompt 2: fetch full listing + write spec.yml
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
├── __init__.py              # Public exports
├── models.py                # JobListing, JobStub, JobFetchError dataclasses
├── base.py                  # JobFetcher ABC + _random_headers() + _polite_delay()
├── visa_filter.py           # detect_visa_signals() + is_visa_friendly()
├── filters.py               # JobFilter, filter_stubs(), classify_level()
├── seek_variants.py         # SEEK URL builder + keyword expansion groups
├── router.py                # JobFetcherRouter — URL → fetcher dispatch
└── fetchers/
    ├── seek.py              # SeekFetcher           (Playwright — Cloudflare)
    ├── seek_search.py       # SeekSearchScraper     (requests + BS4, Redux JSON)
    ├── linkedin.py          # LinkedInFetcher       (Playwright → paste fallback)
    ├── indeed.py            # IndeedFetcher         (requests + BS4, JSON-LD)
    └── indeed_search.py     # IndeedSearchScraper   (requests → Playwright fallback, Mosaic JSON)

tools/
├── fetch_job.py             # CLI entry point
└── debug_indeed_structure.py  # One-shot Playwright script to dump Indeed's mosaic key structure
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
