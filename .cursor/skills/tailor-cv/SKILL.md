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

## Cross-cutting principles (read first)

Read `../../../PRINCIPLES.md` (at repo root) before drafting. Three rules that
override anything below if they conflict:

1. **Honesty over keywords.** Bullet bank is the source of truth. No
   fabrication, no scope inflation, no keyword-stuffing the narration with
   things the underlying achievement doesn't support. If the bank can't
   honestly cover an ad requirement, surface the gap to the user.
2. **Optimise for ATS *and* the manual screen.** Big-tech AU recruiters skim
   in ~8 seconds: name + work rights → most recent role → first 1–2 bullets
   → profile sentence one → education credential. Lead each role with the
   strongest matching `impact-metric` bullet. Profile sentence one must
   mirror the ad's primary technical signal.
3. **Visa 485.** State Australian work rights explicitly in the contact
   block. Detect PR-only gates and flag them before drafting. See
   `PRINCIPLES.md` §3 for phrasing.

### Pivot rule for big-tech tailoring (from Principle 2)

The user is pivoting from SONIQ (digital signage CMS) to big tech. Apply by
default:

- **Omit `soniq-overview` for big-tech tailoring.** Its "digital signage CMS"
  framing reads as small-company. Let `*-stack` + impact bullets carry the
  signal. Re-include only if the target actually works in media/CMS/AdTech.
- **Lead with engineering substance, not product domain.** Cost optimisation,
  TypeScript migration, event-driven integration, infrastructure scheduling
  — these are the foreground bullets. "Digital signage" stays background.

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

## Section order

Default for tailored CVs: **Profile → Experience → Projects → Skills → Education**. With 1+ year of paid SWE work already on the CV, Experience-first is the conventional order; Education is verification, not differentiation, and lives at the bottom (the section header still carries "Highest Achieving Graduate" and GPA so the credibility signal isn't lost).

Override per spec via the optional `section_order:` key — a list naming any subset/reordering of `[profile, experience, projects, skills, education]`. Use this when the ad explicitly screens on academics — e.g. `section_order: [profile, education, experience, projects, skills]`. Omitting a section drops it entirely, so be deliberate.

### "Graduate role" vs "Graduate program" — don't confuse them

The word "graduate" in a job title is **not** a signal to put Education first. Distinguish:

- **Graduate role** (default — keep Experience-first): a regular hire onto a real product team where the title just means "open to recent grads". Conserve It's "Graduate Software Developer" is exactly this — they want demonstrable code, not GPA. Phrases like *"show code you have worked on will put you at the top of the list"* or a long list of technical essentials with the degree buried near the bottom confirm this. Treat these the same as any junior SWE role.
- **Graduate program** (flip Education up): a structured, often rotational scheme (Atlassian Grad, Canva Grad, NAB Grad, ATO Grad, government grad schemes, Big-4 grad consulting). These typically screen on academics first.

Signals that warrant flipping `section_order` to surface Education early:

1. The role is named "Graduate Program", "Graduate Scheme", or "Cadetship" (capitalised, structured).
2. Explicit GPA / WAM / degree-class cutoffs in the ad ("minimum WAM 75", "Distinction average").
3. Research roles (CSIRO, DSTG, universities, national labs) where thesis/publications matter.
4. The ad lists "academic excellence" / "recent graduate" as a *hiring criterion* in its own right, not just "Bachelor of X required" as a baseline.

If none of those apply, keep the default order even when the title contains the word "graduate". The Profile paragraph (which always carries "Highest Achieving Graduate in Computer Science") already gives recruiters the academic credential within the first 8-second skim — Education at the bottom becomes verification, not discovery.

## Repo invariants

- **Master CV** lives at `cv/main.tex`. Never modify it from this skill.
- **Bullet bank**: `bullet-bank/{soniq,csiro,projects}.yml`. Source of truth for selectable bullets. Never invent bullets that aren't in the bank — if a relevant bullet is missing, tell the user and offer to invoke the `add-bullet` skill instead.
- **Confidentiality**: obey `BOUNDARIES.md`. No SONIQ source, no internal URLs, no confidential client names, no private metrics unless already in the bank.
- **Generated files** (`outputs/<slug>/*.tex`, `outputs/<slug>/*.pdf`) are throwaway. Spec YAMLs in `job-ads/<slug>/spec.yml` are the editable artefact.

## Workflow

Track progress with this checklist:

```
- [ ] 1. Load bullet bank + BOUNDARIES.md
- [ ] 2. Parse the job ad
- [ ] 3. Propose a shortlist (await user approval)
- [ ] 4. Write job-ads/<slug>/spec.yml
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
5. `job-ads/_example/spec.yml` (only if you've never seen the spec format before)

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

- SONIQ: **4 bullets** + `soniq-stack` (mandatory). 5 is borderline.
- CSIRO: **3–4 bullets** + `csiro-stack` (mandatory).
- Projects: **2 projects**, **1–2 bullets each**. Pick projects whose `tags` mirror the ad's stack.
- Education bullets: **always explicitly set `education_bullets` in the spec** — never leave it unset (unset defaults to all 3, which wastes space on the scholarship and database-paper lines). Default for every engineering role: **Highest Achieving Graduate only** (1 bullet). Add the database-paper bullet only when `database`, `schema`, `sql`, or similar is a keyword in the ad. Always drop the scholarship line for engineering roles. Experience and projects always take priority over education lines.
- `*-overview` bullets: **default to omitting them**. Include only if the ad emphasises breadth the overview captures and there is page room left.

Total `\resumeItem` count target: **≤ 13** (including stack lines, education, and project bullets). **Empirically, 14+ overflows to a second page** — and `\resumeItem` count alone is a misleading proxy: a single long bullet (~50 words like `csiro-overview` or `csiro-fullstack-leadership`) wraps to 3–4 visual lines and eats the budget of three short bullets. Track **visual lines**, not just bullet count.

**Heavy bullets to handle with care** (each consumes 3–4 visual lines):

- `csiro-overview` (the lab-automation overview)
- `csiro-fullstack-leadership`
- `soniq-shopify-eventbridge`
- `tbrgs-dl-search`

If you include one of these, drop one short bullet elsewhere to compensate. The `*-stack` bullets are also typically 2 visual lines — count them as such.

Present the shortlist as a markdown table, then **wait for user approval or edits** before writing any files:

```
| Section | Bullet ID | Why | Keyword(s) hit |
|---|---|---|---|
| SONIQ | soniq-cost-optimisation | Quantified AWS cost win | aws, cost, serverless |
| ...   | ...                     | ...                     | ...                    |
```

Also propose:

- A **2–3 sentence `profile` paragraph** (≤ ~50 words) that mirrors the ad's vocabulary and culture signals. Adapt the master profile in `cv/main.tex` — do not rewrite from scratch. Cut filler ("Motivated by…") if it doesn't directly mirror the ad.
- A **reordered, pruned `skills` block** (structured YAML): keep the master's structure, move ad-relevant categories to the top, and **drop categories that would be noise** for this role. Better to have 3 dense lines than 6 thin ones.

### 4. Write the spec

Slugify the company: lowercase, dashes, ASCII only (e.g. `Conserve It` → `conserve-it`).

Write to `job-ads/<slug>/spec.yml` using the schema from `job-ads/_example/spec.yml`. Required keys:

```yaml
company: ...
role: ...
source_url: ...        # ask user if not in the ad
date_saved: YYYY-MM-DD
ad_raw: |
  <verbatim paste of the ad>
keywords: [...]
section_order:         # optional; defaults to [profile, experience, projects, skills, education].
  - profile
  - experience
  - projects
  - skills
  - education
education_bullets:     # ALWAYS set explicitly — never leave unset (unset defaults to all 3).
  - Recognised as \textbf{Highest Achieving Graduate} in the Bachelor of Computer Science (Professional) cohort.
  # Only add the database-paper line when database/schema/sql are ad keywords.
  # Never include the scholarship line for engineering roles.
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
skills:
  - category: <Category>
    items: [<item1>, <item2>]
```

If `job-ads/<slug>/spec.yml` already exists, **do not overwrite without confirmation** — show a diff summary first.

### 5. Render + compile

Prefer the one-shot script:

```bash
tools/compile.sh job-ads/<slug>/spec.yml
```

This renders `job-ads/<slug>/spec.yml` → `outputs/<slug>/cv.tex`, compiles to
`outputs/<slug>/cv.pdf` via Tectonic, and prints a page-count warning if
> 1 page. Surface any `warn:` lines from stderr to the user (typically: a
referenced bullet ID is missing).

If `tools/compile.sh` isn't available or fails, fall back to:

```bash
.venv/bin/python tools/render_tailored.py job-ads/<slug>/spec.yml
tectonic outputs/<slug>/cv.tex --outdir outputs
# or, if Tectonic isn't installed:
latexmk -pdf -outdir=outputs outputs/<slug>/cv.tex
```

If no LaTeX toolchain is on PATH, tell the user to `brew install tectonic` but do not fail the flow — the .tex output is still useful.

When you cannot compile, apply a **conservative heuristic** to estimate one-page fit before handing off:

- Total `\resumeItem{...}` lines in the rendered .tex should be **≤ 13** (14+ has been observed to overflow). Beware: long bullets count as multiple visual lines — see the "Heavy bullets" list above.
- Sum of words across all `text` fields in the spec should be **≤ ~280**.
- `profile` paragraph should be **≤ 50 words**.
- `skills` block should have **≤ 5 category lines**.

If any threshold is exceeded, prune (using the priority order in the next step) and re-render before declaring done.

If compiled, report the PDF page count and **enforce one page**:

- **= 1 page**: report success, show the chosen shortlist, hand off to step 7.
- **> 1 page**: enter a prune loop. Drop bullets in this priority order until the PDF fits. **Education is the lowest-priority section** — cut it before touching projects or experience. **Within experience and projects, projects are less important than experience bullets** — projects exist to colour gaps experience doesn't fill.
  1. Any `*-overview` bullet still in the spec.
  2. The scholarship education bullet (if `education_bullets` wasn't already locked to Highest Achieving Graduate only).
  3. The database-paper education bullet, if `database`/`schema`/`sql` aren't ad keywords.
  4. The weakest project's bullets, then the project itself.
  5. The lowest-signal experience bullet (fewest keyword hits, no `impact-metric` tag).
  6. The longest single bullet in the lowest-priority role.
  Re-render and re-compile after each prune. After 3 unsuccessful prune passes, stop and tell the user which bullets you'd cut and ask them to choose. Never strip the `*-stack` bullets, the role overview structure, or the contact header.
- **< 1 page** (rare): suggest 1–2 strong bullets to add back, drawn from the bank's unused IDs that match remaining keywords. Don't pad with low-signal content just to fill space — a slightly short, dense page beats a full-but-watery one.

### 7. Offer iteration

Ask the user for one of:

- "Swap bullet X for Y."
- "Shorten the profile."
- "It's too long — drop N bullets."
- "Change the skills order."
- "Looks good — commit it."

Each tweak should be a small edit to `job-ads/<slug>/spec.yml` followed by a re-render. Never edit `outputs/<slug>/cv.tex` directly.

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
