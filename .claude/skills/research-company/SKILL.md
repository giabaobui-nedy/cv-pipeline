---
name: research-company
description: >-
  Research a target employer in five concentric layers — company → division →
  team → product/project → tech stack — and produce a structured, cited
  research file the tailor-cv and cover-letter skills can both consume. Use
  when the user pastes a job ad and asks to research the company, says "tell
  me about [Company]", asks "what does [Company] actually do?", wants to go
  deeper before drafting, or explicitly asks for layer-by-layer research.
---

# Research Company

Produce structured, cited research on a target employer **before** any tailoring or cover-letter drafting happens. The output is a markdown file at `job-ads/<slug>.research.md` that lives next to the job-ad spec and is read by the other skills.

The pattern is concentric: zoom in one layer at a time. Each layer answers a question the next layer depends on.

```
Company       — who they are
   ↓
Division      — which arm of them is hiring
   ↓
Team          — which team inside that arm
   ↓
Project       — what the team ships
   ↓
Tech stack    — how the team ships it
```

Skipping layers produces generic cover letters. Doing all five produces references no other candidate has.

## Cross-cutting principles

See `PRINCIPLES.md`. Specifically: only record what you can cite. **Never** invent details or paraphrase confidently from low-confidence sources — mark uncertainty explicitly so downstream skills don't trust it as fact.

## When to invoke

- Always before `cover-letter` for any company the agent doesn't already know cold.
- Optionally before `tailor-cv` when the ad's vocabulary is thin and the bullet selection benefits from product/domain context.
- Standalone when the user is deciding whether to apply, or preparing for an interview.

## Workflow

```
- [ ] 1. Resolve the company (slug, domain, official site)
- [ ] 2. Layer 1 — Company
- [ ] 3. Layer 2 — Division / department
- [ ] 4. Layer 3 — Team
- [ ] 5. Layer 4 — Project / product
- [ ] 6. Layer 5 — Tech stack
- [ ] 7. Synthesise 3–5 cover-letter / interview angles
- [ ] 8. Write job-ads/<slug>.research.md
- [ ] 9. (optional) Hand off to cover-letter or tailor-cv
```

### 1. Resolve the company

From the job ad, extract:
- Canonical company name (avoid the parent group unless the ad uses it).
- Official domain (do a quick search if unsure — wrong domain = wrong research).
- Slug to match the job-ad spec (`Conserve It` → `conserve-it`).

If the company has multiple legal entities (e.g. "Atlassian" vs. "Atlassian Australia Pty Ltd"), use the brand name; mention legal entity only if relevant for visa or contract questions.

### 2. Layer 1 — Company

Capture:

- **Identity**: what they do in one sentence, in their own words.
- **Mission / positioning**: how they describe their reason to exist.
- **Scale**: rough employee count, age, revenue stage if public, ownership (private / PE / public / subsidiary).
- **Geography**: HQ, AU office presence (relevant for visa/work-rights conversations — see Principle 3).
- **Recent strategic signals**: a release, partnership, funding round, or expansion in the last ~12 months. Pick the most concrete.
- **Mission credibility**: does the website match the ad's tone, or do they diverge? Divergence is a tone signal.

Cite at least 2 sources for this layer (typically homepage + LinkedIn or Crunchbase).

### 3. Layer 2 — Division / department

The role is rarely "at the company" — it's at a *division*. Find:

- The division/department name as the company uses it (e.g. "Niagara Applications", "Platform Engineering", "Growth", "Data Platform").
- What that division ships, and **how it differs from neighbouring divisions**.
- The division's external surface area (does it have its own product page, blog, GitHub org, conference talks?).
- Any leadership signal — division GM, head of engineering, or product lead — if publicly named.

If the division isn't a discrete business unit (e.g. small companies have flat structures), note this and merge with Layer 1.

### 4. Layer 3 — Team

The team named in the ad ("Niagara Applications Development team", "Platform Reliability team", "Search Quality team"). Find:

- Team mission in one sentence.
- Team lead / engineering manager **if named in the ad or on LinkedIn / company site**. Use only public info.
- Team size if stated; otherwise leave blank, do not guess.
- Working model (remote / hybrid / on-site) — usually in the ad, sometimes only on Glassdoor.
- Recent team output: a blog post, conference talk, GitHub repo, or open-source project authored by the team. This is the highest-leverage finding for cover letters.

If team-level info is genuinely unavailable, write: *"team-level info not surfaced; cover letter must work from division + product."*

### 5. Layer 4 — Project / product

The specific product or project the role contributes to. Find:

- Product name, one-line description, current major version if public.
- The technical shape (digital twin, real-time ML, embedded, multi-tenant SaaS, on-prem, mobile, etc.). This is what the cover letter's hook anchors to.
- Customer / user shape (who pays, who uses).
- Distinctive constraints: latency, deployment target, hardware involvement, regulatory environment, data residency, etc.
- Public material: product page, demo video, case studies, white papers, conference decks. Prefer their own materials over third-party summaries.

If the role spans multiple products, capture the one named first or most prominently in the ad and note the others briefly.

### 6. Layer 5 — Tech stack

The actual stack — not what they list as desirable in the ad. Sources, in order:

1. **Job ad essentials** (the hard requirements list).
2. **Engineering blog posts / conference talks** by current employees.
3. **Public GitHub orgs / repos** (the organisation's repos and their dependencies).
4. **StackShare / BuiltWith / Wappalyzer** for the customer-facing surface.
5. **LinkedIn employee skill aggregations** (low-signal, use only for pattern confirmation).
6. **Glassdoor / interview reviews** (lowest signal — opinions, not facts).

Capture per category: languages, frameworks, infra, data layer, observability, build tooling, integration partners, hardware/firmware (if any).

Mark each finding with **(confirmed) / (likely) / (rumoured)** based on source quality. Cover-letter and tailor-cv skills should *only* use *(confirmed)* or *(likely)* facts.

### 7. Synthesise angles

From the five layers, pull **3–5 angles** the cover letter or interview answers can use that no generic application could:

| Angle | Layer source | Why it's distinctive | Where to use |
|---|---|---|---|
| e.g. PlantPRO is a digital twin | Project | Mirrors my Battery Digital Twin capstone | Cover letter P1 hook |
| e.g. Edge ML on Niagara controllers | Project + Stack | Embedded+ML overlap, narrow industry | Cover letter P4 forward |

Rank angles by *uniqueness* (how few other candidates would catch this) × *honesty* (how well it actually matches a real bullet you have).

### 8. Write the research file

Path: `job-ads/<slug>.research.md`. Schema:

```markdown
# <Company> — Research

> Source ad: [link or "n/a"] · Researched: YYYY-MM-DD · Skill version: research-company

## Layer 1 — Company

- **Identity**: …
- **Mission**: …
- **Scale**: …
- **Geography**: …
- **Recent signals**: …

Sources: [link 1](…), [link 2](…)

## Layer 2 — Division

…

## Layer 3 — Team

…

## Layer 4 — Project / Product

- **Name**: …
- **Shape**: …
- **Constraints**: …

Sources: …

## Layer 5 — Tech stack

| Category | Findings | Confidence |
|---|---|---|
| Languages | … | confirmed |
| Frameworks | … | likely |
| Infra | … | rumoured |

Sources: …

## Synthesis — Cover-letter / interview angles

| # | Angle | Layer source | Best use |
|---|---|---|---|
| 1 | … | Project | Cover letter P1 |
| 2 | … | Stack | Interview question |

## Open questions

- Things that couldn't be verified from public sources.
- Things to ask in the interview.

## Reading list (for the user)

Ordered shortest → deepest:

1. [Product page](…)
2. [Partnership page](…)
3. [Conference deck PDF](…)
4. [Founder talk YouTube (5 min)](…)
```

### 9. Hand off

When the user is ready to draft, the next skill should:

- `cover-letter`: read `<slug>.research.md` instead of doing its own search. The "Synthesis" angles directly feed paragraph design.
- `tailor-cv`: use the tech-stack table to refine the `keywords:` list in the spec when the ad's vocabulary is thin.

If the research file is missing when those skills run, they should invoke this skill first (or warn the user explicitly that they're proceeding without research).

## Constraints

- **Never invent**. If a layer has no findings, write the `*not surfaced*` placeholder. Better an honest gap than a fabricated detail.
- **Always cite**. Every non-obvious claim in the research file gets a source link. Unsourced claims get pruned before save.
- **Mark confidence**. *confirmed* (primary source), *likely* (multiple corroborating secondary sources), *rumoured* (single low-quality source like a Glassdoor comment). Downstream skills filter on this.
- **Respect privacy and BOUNDARIES**. Don't surface employees' personal information beyond what they themselves publish in a professional capacity (LinkedIn role, conference talk, blog post). No phone numbers, no home addresses, no scraped emails.
- **Don't recommend applying or not applying**. The skill produces facts and angles; the human decides.

## Example trigger phrases

- "Research Conserve It before I apply"
- "Tell me about [Company] in layers — company, team, product, stack"
- "What does [Company] actually do, and what would I be working on?"
- "Do the research thing first, then we'll do the cover letter"
- "Layer-by-layer research on this ad"
