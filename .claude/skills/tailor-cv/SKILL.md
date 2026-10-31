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
   in ~8 seconds: name → most recent role → first 1–2 bullets
   → profile sentence one → education credential. Lead each role with the
   strongest matching `impact-metric` bullet. Profile sentence one must
   mirror the ad's primary technical signal.
3. **Visa 485.** The CV carries no work-rights line (`PRINCIPLES.md` §3.1).
   The cover letter header and the application form carry it. Detect
   PR-only gates and flag them before drafting. Answer work-rights form
   questions truthfully, using the §3 "now or in the future" guidance.

### Pivot rule for big-tech tailoring (from Principle 2)

The user is pivoting from SONIQ (digital signage CMS) to big tech. Apply by
default:

- **Omit `soniq-overview` for big-tech tailoring.** Its "digital signage CMS"
  framing reads as small-company. Let `*-stack` + impact bullets carry the
  signal. Re-include only if the target actually works in media/CMS/AdTech.
- **Lead with engineering substance, not product domain.** Cost optimisation,
  TypeScript migration, event-driven integration, infrastructure scheduling
  — these are the foreground bullets. "Digital signage" stays background.

## Hard rules — verify before writing any file

These are the most commonly violated rules. Check every one mechanically before
writing `spec.yml`. A spec that violates any of them is invalid, regardless of
how good the bullet selection is.

| # | Rule | Common failure mode |
|---|---|---|
| H1 | **`education_bullets` must be set explicitly — never omit, never leave `[]`.** Default (also the renderer's default if unset): Highest Achieving Graduate only. Add the database-paper line only when `sql`/`database`/`schema` are ad keywords. Never include the scholarship line for engineering roles. | Auto-tools write `education_bullets: []`, silently dropping the credential. |
| H2 | **Skills block must use structured `category`/`items` YAML, and every item must be proved by a selected bullet or stack line.** Never use a raw LaTeX string. The renderer warns on any unbacked item; drop it or swap in a bullet that proves it. | Models copy skills from the master or the ad without evidence on the page. |
| H3 | **Profile opening: start with the title of the most recent role on the CV (`experience[0].title`).** Never substitute a different title ("Full-stack Engineer", "Cloud Engineer", "Software Developer"). The actual current role title is the ceiling for self-description. | Models infer the target role title from the ad and use that instead. |
| H4 | **`soniq-stack` and `csiro-stack` are mandatory** in their respective role sections. Never omit them — they are the primary ATS keyword anchors. A spec-level `stack:` string on an experience entry is rendered as an extra stack line; use it only when you also drop the bank's `*-stack` bullet. | Dropped when trimming for page length. Stack lines must be the last to go. |
| H5 | **Never invent bullet IDs.** Only IDs present in `bullet-bank/*.yml` may appear in `bullets:` lists. If a relevant bullet is missing, invoke `add-bullet` or flag the gap to the user. The renderer refuses unknown IDs, `status: outdated` bullets, and two bullets from one `variant_group`. | Models hallucinate plausible-sounding IDs. |
| H6 | **Output must compile within its `page_mode` (default one page) and pass the text-layer check.** Always run the compile step. If over the limit, enter the prune loop. If `compile.sh` reports a text-layer error, fix it before handing off, because ATS parsers read that text. | Models write the spec but skip the compile verification. |
| H7 | **YoE qualifier must describe duration only — never attach domain-specific claims to it.** Write "<YoE> of commercial experience building and supporting production systems", not "<YoE> of commercial experience in cloud-native infrastructure, CI/CD, and X". The YoE spans several roles with different domains; claiming the full duration covered a specific domain is false. Domain-specific skills belong in the second profile sentence without a duration attached. | Models mirror the ad's language by writing "X years of experience in [ad keyword]", over-claiming scope. |
| H9 | **Read every selected bullet's `note` and keep the CV inside it.** Notes carry honesty limits ("dev only, never production", "never write led"). The renderer prints each note as a `warn:` line; check each one before handing off. Respect `env` (no production claim unless `prod` is listed) and `ownership`. | Notes ignored, so a profile or skills line overclaims what the bullet allows. |
| H8 | **Fill the page before declaring done.** After the first clean 1-page compile, check whether the CV is visibly sparse (roughly fewer than 11 `\resumeItem` content lines, excluding stack and education). If it is, enter the fill loop (see §5 below) and add bullets until the page is dense or the 13-item ceiling is approaching. A sparse 1-page CV wastes signal and looks unpolished. | First clean compile declared success without checking space usage. |

## Primary objective: one page, high signal

The tailored CV **must compile to exactly one page**. At early-career stage,
density of signal beats breadth — every bullet on the page should map to at
least one keyword from the ad. Cut anything that doesn't. If the user
explicitly overrides this and asks for two pages, comply, but default to one.

### page_mode

Set `page_mode:` in the spec. `one` (default) suits AU tech companies, startups and US-headquartered firms. `two` suits AU enterprise, banks, consulting and public-sector roles, where SEEK and recruiters expect two pages. Use `two` only when the ad or employer type fits, never to avoid pruning. `compile.sh` enforces the limit.

Signal-density rules:

- Prefer bullets tagged `impact-metric` (quantified outcomes).
- Prefer bullets whose `tags` overlap with the ad's `keywords`.
- Drop bullets that only restate context (`*-overview` bullets) unless the ad
  explicitly asks for the kind of breadth the overview describes.
- Drop a project entirely before keeping a low-signal bullet from it.
- Pick at most one version per `variant_group`. Prefer the `-compact` version when space is tight.
- Use at most 2 bullets from one `story` (for example the outbox or design-system work).
- The `*-stack` bullets are mandatory — they're the keyword anchor for ATS.

## Section order

Default for tailored CVs: **Profile → Experience → Projects → Skills → Education**. With 2+ years of paid SWE work already on the CV, Experience-first is the conventional order; Education is verification, not differentiation, and lives at the bottom (the section header still carries "Highest Achieving Graduate" and GPA so the credibility signal isn't lost).

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

- **Master CV** is `cv/master.yml`, rendered from the whole bank by `tools/compile.sh master`. Never modify it from this skill. `cv/archive/` holds the retired hand-edited `main.tex`; never read it as a source.
- **Bullet bank**: `bullet-bank/*.yml` (one file per employer, plus `projects.yml`). Field meanings are in `bullet-bank/README.md`; tag vocabulary and ad-phrase synonyms are in `bullet-bank/tags.yml`. Source of truth for selectable bullets. Never invent bullets that aren't in the bank — if a relevant bullet is missing, tell the user and offer to invoke the `add-bullet` skill instead.
- **Confidentiality**: obey `BOUNDARIES.md`. No SONIQ source, no internal URLs, no confidential client names, no private metrics unless already in the bank.
- **Generated files** (`outputs/<slug>/*.tex`, `outputs/<slug>/*.pdf`) are throwaway. Spec YAMLs in `job-ads/<slug>/spec.yml` are the editable artefact.

## Workflow

Track progress with this checklist:

```
- [ ] 1. Load bullet bank + BOUNDARIES.md; run tools/lint_bank.py
- [ ] 2. Parse the job ad (basic vs preferred qualifications)
- [ ] 3. Coverage table + shortlist (await user approval)
- [ ] 4. Write job-ads/<slug>/spec.yml
- [ ] 5. Run the renderer
- [ ] 6. Compile to PDF if possible
- [ ] 6a. If > 1 page: prune loop until 1 page
- [ ] 6b. If < 1 page (sparse): fill loop until dense or ceiling reached
- [ ] 7. Offer iteration
```

### 1. Load context

Read these files (in this order):

1. `BOUNDARIES.md`
2. Every `bullet-bank/*.yml` file, including `tags.yml` and `bullet-bank/README.md`
3. `job-ads/<slug>/research.md` if it exists. Use its "Ad facts" block (title, qualifications, screening questions, ATS vendor) and its eligibility result.
4. `cv/master.yml` for the master profile and skills block
5. `job-ads/_example/spec.yml` (only if you've never seen the spec format before)

Run `python3 tools/lint_bank.py`. Stop and report any `error:` line. Mention `metric not verified` warnings when a shortlisted bullet carries one.

### 2. Parse the ad

Extract from the ad text:

- `company` and `role` (best guess from the ad).
- `seniority` (intern / junior / mid / senior).
- `basic_qualifications`: the ad's required items, each as the ad's exact noun phrase ("experience with AWS Lambda", "PostgreSQL"). Workday HiredScore grades each basic qualification separately, so one missing item lowers the whole grade.
- `preferred_qualifications`: nice-to-haves, same format.
- `keywords`: 8–15 short tokens that mirror the ad's vocabulary (e.g. `aws`, `event-driven`, `react`, `iac`, `observability`). Map each ad phrase to a bank tag through `tags.yml` `synonyms`, but write the ad's own phrase in the profile and skills block.
- `culture_signals`: 1–3 phrases hinting at team style (e.g. "small team", "ownership", "scientific rigour"). Used to shape the `profile` paragraph.

### 3. Coverage table, then shortlist (REQUIRED before writing files)

First show a coverage table. Each basic qualification gets the bullet ID that proves it in its rendered text, or `gap`:

```
| Basic qualification (ad wording) | Proved by | Exact phrase on the CV? |
|---|---|---|
| Experience with AWS serverless | soniq-cost-optimisation | yes ("AWS Lambda") |
| Kubernetes | gap | no |
```

Report every `gap` to the user before rendering (Principle 1: never paper over it). Then make sure each covered qualification's exact phrase appears once on the page, in a bullet, the profile or the skills block. Spell out an abbreviation once ("infrastructure as code (IaC)"). Use each keyword at most 3 times; the renderer warns past 4.

Then pick bullets by **tag overlap** with `keywords`, breaking ties by impact (`impact-metric` tagged bullets win) and recency (newest employer first). For AI-forward roles prefer `ai_framing: builder` bullets; for conservative employers use at most one `ai_framing: user` bullet.

**For client-facing roles (FDE, consulting, professional services, solutions engineering):** when two CSIRO bullets score similarly on tag overlap, prefer the one that shows *delivery + communication* over *communication only*. A bullet showing multi-stakeholder collaboration on a real commissioned system (e.g. `csiro-collaboration`) is stronger evidence of client-facing capability than a bullet about presenting or demonstrating (e.g. `csiro-demos`). Recruiters for these roles want to see ownership and delivery alongside communication — one-way presentation bullets underdeliver on the ownership half.

**Budget for one page** (start here, prune harder if compilation overflows):

- Canonical (from 3 Nov 2026): the role heading plus `canonical-overview` until achievement bullets exist. It costs about 2 lines but puts the strongest employer name first. Once the user has been there a few months, move SONIQ to 3 bullets.
- SONIQ: **4 bullets** + `soniq-stack` (mandatory). 5 is borderline.
- CSIRO: **3–4 bullets** + `csiro-stack` (mandatory).
- Projects: **0–1 project, 1–2 bullets** (experience-first policy, Aug 2026 — see `PRINCIPLES.md` §2). A project earns its place only if it hits an ad keyword that **zero** experience bullets cover; if every project bullet is redundant with experience, drop the Projects section entirely and spend the space on more SONIQ bullets. Uni-era projects (`weekly-planner`, `tbrgs`, `planner-diary`, `decentralised-trading`, `battery-digital-twin`) age out first — they read increasingly junior next to production work. `cv-pipeline` is the exception: current, self-owned, real engineering; it stays viable for AI-forward roles specifically. A second project is justified only when it covers a *second* uncovered ad requirement — apply the test strictly: for Unity Care (Aug 2026), `weekly-planner-orm-tests` ("validate AI-generated code") was cut because `soniq-architectural-validation` already carried that signal, and the space went to an extra SONIQ bullet instead. (That bullet is now `status: outdated`; the test itself still applies.)
- Education bullets: **always explicitly set `education_bullets` in the spec** — never leave it unset, so the choice is visible in the spec (the renderer falls back to Highest Achieving Graduate only). Default for every engineering role: **Highest Achieving Graduate only** (1 bullet). Add the database-paper bullet only when `database`, `schema`, `sql`, or similar is a keyword in the ad. Always drop the scholarship line for engineering roles. Experience and projects always take priority over education lines.
- `*-overview` bullets: **default to omitting them**. Include only if the ad emphasises breadth the overview captures and there is page room left.

Total `\resumeItem` count target: **≤ 13** (including stack lines, education, and project bullets). **Empirically, 14+ overflows to a second page**. Count is a weak proxy, so budget by **words**: the renderer prints the total bullet words after each render. Aim for about 280 bullet words on one page. Run `python3 tools/lint_bank.py --words` to see each bullet's length. Any bullet over 30 words wraps to 3 or more lines; when space is tight, swap it for the `-compact` version in its `variant_group`. The `*-stack` bullets are about 2 visual lines each.

### Bullet anti-patterns — default avoid list

These bullets are often selected by mistake. Check your shortlist against this
table before proposing:

| Bullet ID | Why to avoid by default | Include only when… |
|---|---|---|
| `csiro-firmware-abstraction` | Modbus/hardware abstraction layer — reads as embedded/industrial, not SWE | Role explicitly involves hardware, firmware, or embedded systems |
| `csiro-oop-hardware` | Hardware communication OOP — same framing problem | Same as above |
| `csiro-locks-deployment` | "Three-month continuous operation in a live laboratory" — industrial/lab context | Reliability, SRE, or safety-critical roles |
| `csiro-overview` | 52-word lab automation summary — very heavy (3–4 visual lines) and CSIRO-domain-specific | Research, science, or automation-adjacent roles with page room to spare |
| `soniq-overview` | Names "digital signage CMS" explicitly — small-company framing | Media, CMS, AdTech, or digital signage roles |
| `soniq-responsive-redesign` | CSS layout/mobile-first redesign — low signal for backend/fullstack/cloud roles | Roles explicitly asking for responsive design, CSS, or mobile UI work |
| `soniq-portrait-landscape` | IoT screen orientations — very domain-specific, narrow signal | Signage, IoT, or display technology roles only |
| `csiro-demos` | One-way presentation (demos to audiences) — thin evidence for client-facing roles that require ownership + delivery. Prefer `csiro-collaboration` for consulting/FDE/professional-services roles. | Roles where public communication or teaching is the primary function (DevRel, advocacy, academic) |

Present the shortlist as a markdown table, then **wait for user approval or edits** before writing any files:

```
| Section | Bullet ID | Why | Keyword(s) hit |
|---|---|---|---|
| SONIQ | soniq-cost-optimisation | Quantified AWS cost win | aws, cost, serverless |
| ...   | ...                     | ...                     | ...                    |
```

Also propose:

- A **2–3 sentence `profile` paragraph** (≤ ~50 words) that mirrors the ad's vocabulary and culture signals. Adapt the master profile in `cv/master.yml` — do not rewrite from scratch. Cut filler ("Motivated by…") if it doesn't directly mirror the ad.

  **Profile YoE structure — follow this pattern exactly:**

  ```
  Sentence 1: "<experience[0].title> and Highest Achieving Graduate in Computer Science
               with <YoE> of commercial experience [general description of work nature]."
  Sentence 2: "Hands-on in [skill A], [skill B], and [skill C], with [outcome pattern]."
  ```

  - **Compute `<YoE>` from role dates on every run.** Sum the whole months of every `experience[]` entry using each bank's `role.start` / `role.end` (no `end` = today). Under 24 months: "nearly 2 years". 24 to 35: "2+ years". 36 to 47: "3+ years". Never round up. Example: CSIRO Mar 2024 to Jun 2025 (16) + SONIQ Feb 2026 to Oct 2026 (9) = 25 months, so "2+ years". Canonical (from Nov 2026) adds to this.
  - Sentence 1 uses the YoE qualifier with a **general** work description only ("building and supporting production systems", "across fullstack and backend engineering"). Never attach a role-specific domain here. The YoE spans several roles, which covered different things.
  - Sentence 2 carries the **role-specific** technical vocabulary without a duration claim. Skills named here must appear in at least one bullet from each role or both stack lines — not just one role.
  - Bad: `"2+ years of commercial experience in cloud-native infrastructure and CI/CD"` (falsely implies every role covered this)
  - Good: `"2+ years of commercial experience building and supporting production systems. Hands-on in Python, Docker, and CI/CD automation…"`
- A **reordered, pruned `skills` block** (structured YAML): keep the master's structure, move ad-relevant categories to the top, and **drop categories that would be noise** for this role. Better to have 3 dense lines than 6 thin ones.

### 4. Write the spec

Slugify the company: lowercase, dashes, ASCII only (e.g. `Conserve It` → `conserve-it`).

Write to `job-ads/<slug>/spec.yml` using the schema from `job-ads/_example/spec.yml`. Role headings (title, employer, dates, location) come from each bank's `role:` block, so an experience entry needs only `bank` and `bullets`. Add a field only to override it. Required keys:

```yaml
company: ...
role: ...
source_url: ...        # ask user if not in the ad
date_saved: YYYY-MM-DD
ad_raw: |
  <verbatim paste of the ad>
keywords: [...]
basic_qualifications: [...]   # the ad's exact phrases; used for the coverage table
page_mode: one                # one | two (see "page_mode")
section_order:         # optional; defaults to [profile, experience, projects, skills, education].
  - profile
  - experience
  - projects
  - skills
  - education
education_bullets:     # ALWAYS set explicitly so the choice is visible in the spec.
  - Recognised as \textbf{Highest Achieving Graduate} in the Bachelor of Computer Science (Professional) cohort.
  # Only add the database-paper line when database/schema/sql are ad keywords.
  # Never include the scholarship line for engineering roles.
profile: >-
  <3-sentence tailored profile>
experience:             # newest first; headings come from bullet-bank/<bank>.yml role:
  - bank: canonical
    bullets: [canonical-overview]
  - bank: soniq
    bullets: [..., soniq-stack]
  - bank: csiro
    bullets: [..., csiro-stack]
projects:
  - id: <project-id>
    bullets: [...]
skills:
  - category: <Category>
    items: [<item1>, <item2>]
referees:              # optional; only when the ad or portal asks for named referees
  - { name: ..., title: ..., organisation: ..., email: ..., relationship: ... }
```

**Referees.** Default: no Referees section (AU convention is "available on request"). Add `referees` and put `referees` in `section_order` only when the ad or portal asks for named referees (universities, public sector). Ask the user for the referee details; keep two ready, at least one based in Australia.

If `job-ads/<slug>/spec.yml` already exists, **do not overwrite without confirmation** — show a diff summary first.

### 5. Render + compile

Prefer the one-shot script:

```bash
tools/compile.sh job-ads/<slug>/spec.yml
```

This lints the bank, renders `job-ads/<slug>/spec.yml` → `outputs/<slug>/cv.tex`,
compiles to `outputs/<slug>/cv.pdf` (A4) via Tectonic, warns if the page count
exceeds `page_mode`, and checks the PDF text layer with `pdftotext`. Surface
every `warn:` and `error:` line to the user. Renderer warnings cover notes on
selected bullets, unbacked skills items, overused keywords, repeated opening
verbs, more than 2 bullets from one story, and em dashes.

If `tools/compile.sh` isn't available or fails, fall back to:

```bash
python3 tools/render_tailored.py job-ads/<slug>/spec.yml
tectonic outputs/<slug>/cv.tex --outdir outputs
# or, if Tectonic isn't installed:
latexmk -pdf -outdir=outputs outputs/<slug>/cv.tex
```

If no LaTeX toolchain is on PATH, tell the user to `brew install tectonic` but do not fail the flow — the .tex output is still useful.

When you cannot compile, apply a **conservative heuristic** to estimate one-page fit before handing off:

- Total `\resumeItem{...}` lines in the rendered .tex should be **≤ 13** (14+ has been observed to overflow). Long bullets count as multiple visual lines; use the word totals the renderer prints.
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
- **< 1 page — actively fill the space.** This is not rare; it happens whenever the initial shortlist was conservative. A visibly sparse CV wastes signal and looks unpolished. Enter the fill loop:
  1. Add the highest-keyword-overlap unused experience bullet (SONIQ first, then CSIRO). Never add a bullet that scores zero keyword hits.
  2. Add a second bullet to an existing project before adding a new project.
  3. Add a new project from the bank if the project section is sparse and a strong candidate exists.
  4. `*-overview` bullets only if all stronger options are exhausted and the page still has room.
  Re-compile after each addition. Stop when the page looks visually dense (few obvious gaps) or the 13-item ceiling is within 1–2 items. **Never pad with zero-signal bullets** — if the only remaining options don't hit any ad keyword, stop and report that the page is as full as the bank can honestly fill.

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
- Never modify `cv/master.yml` from this skill. If the user wants a master-CV change, switch to the `add-bullet` skill.
- Never include confidential content (see `BOUNDARIES.md`).
- The renderer normalises whitespace inside `text` automatically — multi-line YAML scalars are fine.

## Example trigger phrases

- "Tailor my CV for this Conserve It role: «ad»"
- "Customise the CV against this ad"
- "Generate a CV for this job"
- "Build a tailored version for «Company»"
