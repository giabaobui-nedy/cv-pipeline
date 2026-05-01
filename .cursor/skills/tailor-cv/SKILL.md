---
name: tailor-cv
description: >-
  Tailor Gia Bao Bui's CV against a specific job ad by selecting bullets from
  the bullet bank and rendering a job-ad-specific .tex file. Use when the user
  pastes a job description and asks to tailor, customise, generate, or build a
  CV for a specific role, company, or job ad.
---

# Tailor CV

Generate a tailored CV from a pasted job ad using the bullet bank in this repo.

## Primary objective: one page, high signal

The tailored CV **must compile to exactly one page**. At early-career stage,
density of signal beats breadth — every bullet on the page should map to at
least one keyword from the ad. Cut anything that doesn't. If the user
explicitly overrides this and asks for two pages, comply, but default to one.

Signal-density rules:

- Prefer bullets tagged `impact-metric` (quantified outcomes).
- Prefer bullets whose `tags` overlap with the ad's `keywords`.
- Drop bullets that only restate context (`*-overview` bullets) unless the ad
  explicitly asks for the kind of breadth the overview describes.
- Drop a project entirely before keeping a low-signal bullet from it. Two
  strong projects beat three weak ones.
- The `*-stack` bullets are mandatory — they're the keyword anchor for ATS.

## Repo invariants

- **Master CV** lives at `cv/main.tex`. Never modify it from this skill.
- **Bullet bank**: `bullet-bank/{soniq,csiro,projects}.yml`. Source of truth for selectable bullets. Never invent bullets that aren't in the bank — if a relevant bullet is missing, tell the user and offer to invoke the `add-bullet` skill instead.
- **Confidentiality**: obey `BOUNDARIES.md`. No SONIQ source, no internal URLs, no confidential client names, no private metrics unless already in the bank.
- **Generated files** (`outputs/*.tex`, `outputs/*.pdf`) are throwaway. Spec YAMLs in `job-ads/` are the editable artefact.

## Workflow

Track progress with this checklist:

```
- [ ] 1. Load bullet bank + BOUNDARIES.md
- [ ] 2. Parse the job ad
- [ ] 3. Propose a shortlist (await user approval)
- [ ] 4. Write job-ads/<slug>.yml
- [ ] 5. Run the renderer
- [ ] 6. Compile to PDF if possible
- [ ] 7. Offer iteration
```

### 1. Load context

Read these files (in this order):

1. `BOUNDARIES.md`
2. `bullet-bank/soniq.yml`
3. `bullet-bank/csiro.yml`
4. `bullet-bank/projects.yml`
5. `job-ads/_example.yml` (only if you've never seen the spec format before)

### 2. Parse the ad

Extract from the ad text:

- `company` and `role` (best guess from the ad).
- `seniority` (intern / junior / mid / senior).
- `must_haves`: hard requirements (years of X, specific stacks).
- `nice_to_haves`: preferred extras.
- `keywords`: 8–15 short tokens that mirror the ad's vocabulary (e.g. `aws`, `event-driven`, `react`, `iac`, `observability`). Prefer tokens that already exist as `tags` in the bullet bank.
- `culture_signals`: 1–3 phrases hinting at team style (e.g. "small team", "ownership", "scientific rigour"). Used to shape the `profile` paragraph.

### 3. Propose a shortlist (REQUIRED before writing files)

Pick bullets by **tag overlap** with `keywords`, breaking ties by impact (`impact-metric` tagged bullets win) and recency (SONIQ over CSIRO when both fit).

**Budget for one page** (start here, prune harder if compilation overflows):

- SONIQ: **4–5 bullets** + `soniq-stack` (mandatory).
- CSIRO: **3–4 bullets** + `csiro-stack` (mandatory).
- Projects: **2 projects**, **1–2 bullets each**. Pick projects whose `tags` mirror the ad's stack.
- `*-overview` bullets: **default to omitting them**. Include only if the ad emphasises breadth the overview captures and there is page room left.

Total bullet count target: **≤ 16** (including stack lines, education, and project bullets). Above this, the page almost always overflows.

Present the shortlist as a markdown table, then **wait for user approval or edits** before writing any files:

```
| Section | Bullet ID | Why | Keyword(s) hit |
|---|---|---|---|
| SONIQ | soniq-cost-optimisation | Quantified AWS cost win | aws, cost, serverless |
| ...   | ...                     | ...                     | ...                    |
```

Also propose:

- A **2–3 sentence `profile` paragraph** (≤ ~50 words) that mirrors the ad's vocabulary and culture signals. Adapt the master profile in `cv/main.tex` — do not rewrite from scratch. Cut filler ("Motivated by…") if it doesn't directly mirror the ad.
- A **reordered, pruned `skills` block** (LaTeX): keep the master's structure, move ad-relevant categories to the top, and **drop categories that would be noise** for this role. Better to have 3 dense lines than 6 thin ones.

### 4. Write the spec

Slugify the company: lowercase, dashes, ASCII only (e.g. `Conserve It` → `conserve-it`).

Write to `job-ads/<slug>.yml` using the schema from `job-ads/_example.yml`. Required keys:

```yaml
company: ...
role: ...
source_url: ...        # ask user if not in the ad
date_saved: YYYY-MM-DD
ad_raw: |
  <verbatim paste of the ad>
keywords: [...]
profile: >-
  <3-sentence tailored profile>
experience:
  - bank: soniq
    title: Junior Software Engineer
    dates: Feb 2026 -- Present
    employer: SONIQ Digital
    location: Richmond, VIC
    bullets: [..., soniq-stack]
  - bank: csiro
    title: Software Engineering Intern / Casual Software Engineer
    dates: Mar 2024 -- Jun 2025
    employer: CSIRO
    location: Clayton, VIC
    bullets: [..., csiro-stack]
projects:
  - id: <project-id>
    bullets: [...]
skills: |
  <LaTeX skills block, reordered>
```

If `job-ads/<slug>.yml` already exists, **do not overwrite without confirmation** — show a diff summary first.

### 5. Render + compile

Prefer the one-shot script:

```bash
tools/compile.sh job-ads/<slug>.yml
```

This renders `job-ads/<slug>.yml` → `outputs/<slug>.tex`, compiles to
`outputs/<slug>.pdf` via Tectonic, and prints a page-count warning if
> 1 page. Surface any `warn:` lines from stderr to the user (typically: a
referenced bullet ID is missing).

If `tools/compile.sh` isn't available or fails, fall back to:

```bash
.venv/bin/python tools/render_tailored.py job-ads/<slug>.yml
tectonic outputs/<slug>.tex --outdir outputs
# or, if Tectonic isn't installed:
latexmk -pdf -outdir=outputs outputs/<slug>.tex
```

If no LaTeX toolchain is on PATH, tell the user to `brew install tectonic` but do not fail the flow — the .tex output is still useful.

When you cannot compile, apply a **conservative heuristic** to estimate one-page fit before handing off:

- Total `\resumeItem{...}` lines in the rendered .tex should be **≤ 16**.
- Sum of words across all `text` fields in the spec should be **≤ ~280**.
- `profile` paragraph should be **≤ 50 words**.
- `skills` block should have **≤ 5 category lines**.

If any threshold is exceeded, prune (using the priority order in the next step) and re-render before declaring done.

If compiled, report the PDF page count and **enforce one page**:

- **= 1 page**: report success, show the chosen shortlist, hand off to step 7.
- **> 1 page**: enter a prune loop. Drop bullets in this priority order until the PDF fits:
  1. Any `*-overview` bullet still in the spec.
  2. The lowest-signal bullet (fewest keyword hits, no `impact-metric` tag).
  3. The weakest project's bullets, then the project itself.
  4. The longest single bullet in the lowest-priority role.
  Re-render and re-compile after each prune. After 3 unsuccessful prune passes, stop and tell the user which bullets you'd cut and ask them to choose. Never strip the `*-stack` bullets, the role overview structure, or the contact header.
- **< 1 page** (rare): suggest 1–2 strong bullets to add back, drawn from the bank's unused IDs that match remaining keywords. Don't pad with low-signal content just to fill space — a slightly short, dense page beats a full-but-watery one.

### 7. Offer iteration

Ask the user for one of:

- "Swap bullet X for Y."
- "Shorten the profile."
- "It's too long — drop N bullets."
- "Change the skills order."
- "Looks good — commit it."

Each tweak should be a small edit to `job-ads/<slug>.yml` followed by a re-render. Never edit `outputs/<slug>.tex` directly.

## Constraints

- Never invent bullets. Only IDs that exist in the bank may appear in `experience[*].bullets` or `projects[*].bullets`.
- Never modify `cv/main.tex` from this skill. If the user wants a master-CV change, switch to the `add-bullet` skill.
- Never include confidential content (see `BOUNDARIES.md`).
- The renderer normalises whitespace inside `text` automatically — multi-line YAML scalars are fine.

## Example trigger phrases

- "Tailor my CV for this Conserve It role: «ad»"
- "Customise the CV against this ad"
- "Generate a CV for this job"
- "Build a tailored version for «Company»"
