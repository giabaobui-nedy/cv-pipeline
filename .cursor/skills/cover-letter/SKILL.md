---
name: cover-letter
description: >-
  Draft and render a one-page cover letter for Gia Bao Bui against a specific
  job ad, using the bullet bank as evidence and tone-matching the company.
  Use when the user pastes a job ad and asks for a cover letter, asks to write
  / draft / generate / customise a cover letter for a specific role or company,
  or extends an existing job-ad spec with cover-letter content.
---

# Cover Letter

Write a tight, one-page cover letter that earns the read in its first 8 words
and uses real evidence from the bullet bank. The cover letter is rendered from
the same `job-ads/<slug>/spec.yml` that drives the CV — one application, one file.

## Cross-cutting principles (read first)

Read `../../../PRINCIPLES.md` (at repo root) before drafting. Three rules that
override anything below if they conflict:

1. **Honesty over keywords.** The bullet bank is the source of truth. The
   cover letter narrates a bullet's underlying story but **cannot exceed
   what the bank claims**. Don't inflate scope, don't fabricate a metric,
   don't claim a keyword the underlying work doesn't support. If the ad
   asks for X and no bullet covers X, flag the gap to the user before
   drafting — never paper over it with vague language.
2. **Optimise for ATS *and* the manual screen.** Recruiters at AU big tech
   skim in ~8 seconds. The cover letter's job is to differentiate in the
   first sentence (already enforced by the first-line hook rule) and to
   deliver one quantified outcome in P2. Avoid process-narrative; use
   outcome-narrative.
3. **Visa 485.** Don't mention the visa in the body unless the ad
   explicitly mentions sponsorship as a benefit (then briefly note in P5).
   The contact-line statement is enough. If the ad gates on PR/citizenship,
   flag and ask the user before drafting. See `PRINCIPLES.md` §3.

### Pivot rule for big-tech targeting (from Principle 2)

The user is pivoting from SONIQ (digital signage CMS) to big tech. Apply by
default:

- **Never lead the technical paragraph (P2) with signage-specific nouns**
  ("displays", "playback", "client deployments", "CMS"). Lead with the
  architecture or infra noun ("event-driven cost optimisation on AWS Lambda
  + EventBridge", "TypeScript migration across distributed microservices").
- Background the product domain. The recruiter doesn't need to know SONIQ
  sells digital signage to evaluate the engineering work.
- Prefer transferable big-tech vocabulary when narrating, where honestly
  applicable: *distributed systems, cloud-native, event-driven,
  infrastructure-as-code, production, scalability, reliability,
  observability, blast radius*.

## Hard rules — verify before writing the cover_letter block

| # | Rule | Common failure mode |
|---|---|---|
| C1 | **All six structural fields are required:** `recipient_name`, `salutation`, `tone`, `evidence.technical`, `evidence.values`, and all five `paragraphs` keys. | Models omit `tone` and `evidence`, making the output untraceable and the evidence anchor missing. |
| C2 | **`tone` must be one of the five named modes** (or `hybrid_warm_professional`). Never leave it blank — it is the traceability marker for future edits. | Left unset when models skip the tone-detection step. |
| C3 | **Hook must not open with any banned phrase.** Run the hook self-check (see §5 P1) before writing. | "I'm excited by…", "I am writing to…", "I would like to apply…" still appear despite the ban list. |
| C4 | **`evidence.technical` and `evidence.values` must be real bullet IDs from the bank.** The cover letter narrates these bullets — if the IDs are wrong the paragraphs will be incoherent. | Models use plausible-sounding but non-existent IDs. |
| C5 | **Never copy a CV bullet verbatim into a paragraph.** The cover letter zooms into the story behind the bullet; it does not restate the bullet text. | P2 often just paraphrases the bullet text, adding no new depth. |

## Why this skill matters

Most cover letters are skipped because they open with "I am writing to express
my interest in…" Recruiters scan the first sentence and bounce. Our job is to
make the first sentence so specifically about *this* company that no other
candidate could have written it.

## Pipeline integration

- The cover letter lives under `cover_letter:` inside the job-ad spec — same
  file as the tailored CV (`job-ads/<slug>/spec.yml`).
- Evidence references the same bullet bank (`bullet-bank/*.yml`) by `id`.
- Render + compile via `tools/compile.sh job-ads/<slug>/spec.yml --cover`.
- Output: `outputs/<slug>/cover.pdf`.

## Workflow

```
- [ ] 1. Load repo context (bank, BOUNDARIES, existing spec)
- [ ] 2. Research the company online and surface a reading list
- [ ] 3. Detect tone from company size + ad voice
- [ ] 4. Propose evidence bullet IDs for paragraphs 2 and 3
- [ ] 5. Draft all 5 paragraphs (await user approval)
- [ ] 6. Write the cover_letter block into job-ads/<slug>/spec.yml
- [ ] 7. Render + compile via tools/compile.sh
- [ ] 8. Enforce one page; iterate
```

### 1. Load repo context

- `BOUNDARIES.md`
- `bullet-bank/{soniq,csiro,projects}.yml`
- `cv/main.tex` (for the master profile paragraph as voice reference)
- Existing `job-ads/<slug>/spec.yml` if present (so the cover letter mirrors any
  emphasis already chosen for the CV).

### 2. Research the company (REQUIRED — do this *before* drafting)

Cover letters live or die on specificity. The ad alone is rarely enough.

**Preferred path: defer to the `research-company` skill.** If `job-ads/<slug>.research.md` already exists, read it and skip to step 3 — its "Synthesis — angles" table directly feeds paragraph design, and the "Tech stack" + "Project" layers anchor P1/P2/P4. Trust only findings marked *(confirmed)* or *(likely)*.

If the file is missing, **invoke `research-company` first** rather than doing ad-hoc research inside this skill. The layered output is reusable across CV, cover letter, and interview prep — duplicating it inside cover-letter alone wastes context.

If the user explicitly says "skip the research, draft now" (e.g. tight deadline, well-known company), do a minimum-viable scan: official site one-liner + flagship product page + one recent news item. Surface a 3-link reading list, then proceed. Flag the resulting cover letter as `ad-only-light-research` so the user knows it's working from less context than usual.

**In all cases**: surface a reading list to the user (ordered shortest → deepest, with cited markdown links) before drafting, so they can verify and learn the domain in parallel.

### 3. Detect tone

Read the ad and company name. Classify into **one** mode and report which
signals drove the choice:

| Mode | Trigger signals | Tone rules |
|---|---|---|
| `startup_scrappy` | "Series A/B/C", "early-stage", "we move fast", "founding engineer", small team size, casual ad voice, first-person plural ("we're building") | Contractions OK ("I'd"), 1 sentence of personality allowed, lighter sentence structure |
| `corporate_formal` | ASX-listed, multinational, large enterprise, formal HR-speak, "stakeholders", "synergies", strict requirements list | No contractions, traditional opening/closing, full role title, third-person about company |
| `research_scientific` | `.gov.au`, `.edu.au`, university, CSIRO/Defence Science/CRC, words like "research", "rigour", "publication", "evidence" | Hedged claims, precise verbs, no hype language, evidence chain matters |
| `consultancy_clientfacing` | "client", "engagement", "delivery", "stakeholders", "consulting", "advisory", "professional services" | Confident, outcome-language ("delivered", "shaped"), business-impact framing |
| `mission_driven` | "mission", "impact", "for-purpose", climate/health/education/social, B-Corp, NFP | Connect personal motivation to mission, but always back with action not feeling |

If signals are mixed or the ad is too short to classify, default to **`hybrid_warm_professional`** — a polite-but-not-stiff register, no contractions, light sentence variation. Always state the chosen mode to the user before drafting so they can override.

### 4. Pick evidence bullets

For paragraphs 2 (technical) and 3 (values), pick **one bullet ID each** from `bullet-bank/`:

- **P2 — technical_match**: Must match the ad's #1 must-have. Prefer bullets with `impact-metric` tags. Try to differ from the bullet IDs already chosen for the CV's most prominent role (otherwise the cover letter just restates the CV).
- **P3 — values_fit**: Must reflect the ad's culture/values signal (ownership, collaboration, scientific rigour, customer focus, etc.). Different *theme* from P2. Prefer `meta`-tagged bullets (cross-cutting) or bullets with collaboration / leadership / debugging / ownership tags.

Show the user a small table:

| Paragraph | Bullet ID | Why this bullet | Story angle |
|---|---|---|---|
| P2 (technical) | `<id>` | hits keywords X, Y | Narrate the *outcome*, not the task |
| P3 (values)    | `<id>` | shows ownership / collab | Different theme from P2 |

Wait for approval before drafting.

### 5. Draft all 5 paragraphs

**Word budget**: ≤ 350 words total. Per paragraph: 50–80 (P5: 30–50).

#### P1 — Hook

**First-line hook rule**: the first 8 words must be unique to this company/role. If they could appear in 100 other cover letters, rewrite. **Banned openers**: "I am writing to…", "Please accept this letter as…", "I would like to apply for…", "My name is…", "As a [role] with X years of experience…"

Strong opener templates (adapt, don't copy):

- "Reading [Company]'s ad, [specific phrase or detail] reminded me of [specific work I did] — and that's why this role caught me."
- "Your platform sits exactly at the boundary I find most interesting: [X meeting Y], which is where I spent [time period] at [employer]."
- "[Specific product/blog post/initiative of theirs] is the kind of problem I've been deliberately steering toward."

The paragraph should: name the role + company, prove you read the ad with one specific reference, signal the angle of fit. ~50–60 words.

**Hook self-check — run before finalising P1:**

Ask: *could this exact opening sentence appear in a cover letter for a different company's similar role?* If yes — rewrite. P1 passes only if it contains at least one of:
- A specific product name, platform name, or feature from **this company** (not just the job title)
- A specific phrase or framing lifted verbatim from **this ad** (quoted or closely mirrored)
- A specific reason grounded in **your own work** that links to their exact context

If none of these are present, the hook is generic and will not differentiate.

#### P2 — Technical match

Open with a thesis sentence about what the role's most important technical aspect is (your read of the ad). Then narrate the evidence bullet's *story* — not the bullet text itself. Explain the **why** and the **outcome** in your own words; mention the metric if there is one. Land on a sentence that connects the lesson back to what they need.

~70–80 words. Never copy the CV bullet verbatim — the CV already says it.

#### P3 — Values fit

Open with an observation about the company/team's values (drawn from the ad — "you mention ownership / a small team / scientific rigour / customer obsession"). Then a behavioural example using the chosen bullet, narrated as a short story. End with what that pattern means for how you'd show up day-to-day.

Avoid generic culture phrases. Concrete behaviour beats vibes.

~70–80 words.

#### P4 — Forward-looking

This is the paragraph most candidates waste. Use it for **one** of:

- A specific thing you'd want to work on / learn / contribute in the first 90 days, anchored to something concrete in the ad.
- A specific opinion or idea you have about their domain (a polite, well-formed take that shows you've thought about their problem space).
- A specific reason you're choosing them over alternatives you're seeing (be honest, not flattering).

Avoid: "I'm passionate about", "I would love to grow", "I see myself contributing to". Be specific or skip the paragraph entirely.

~50–70 words.

#### P5 — Close

Thanks for considering, signal availability for a conversation, sign off. ≤ 50 words. No new content. No "looking forward to hearing from you" filler if you can avoid it.

### 6. Write the spec

Append (or replace) the `cover_letter:` block in `job-ads/<slug>/spec.yml`:

```yaml
cover_letter:
  company: <Company>                 # defaults to top-level `company` if omitted
  recipient_name: Hiring Team        # or specific person if known
  salutation: "Dear Hiring Team"
  date: 2 May 2026                   # optional; defaults to today on render
  recipient_address: |               # optional; omit unless you have a real address
    Street line 1
    City, State Postcode
  tone: startup_scrappy              # the detected mode (for traceability)
  evidence:
    technical: soniq-cost-optimisation
    values: csiro-collaboration
  paragraphs:
    hook: >-
      <P1 text>
    technical_match: >-
      <P2 text>
    values_fit: >-
      <P3 text>
    forward: >-
      <P4 text>
    close: >-
      <P5 text>
```

If the file already has a `cover_letter:` block, **show a diff** before overwriting and ask for confirmation.

### 7. Render + compile

```bash
tools/compile.sh job-ads/<slug>/spec.yml --cover
```

Output: `outputs/<slug>/cover.pdf`. The renderer warns if word count > 350. The compile script warns if pages > 1.

### 8. Enforce one page; iterate

If > 1 page or > 350 words: **trim**, prioritising in this order:

1. P4 first (most cuttable; can drop to ~40 words or merge into P1).
2. P3 second (tighten the narrative around the bullet).
3. P2 last (it's the load-bearing paragraph).
4. Never trim P1 below 50 words — the hook needs room.

If < 250 words and < 1 page: probably under-developed; suggest expanding P4 or sharpening P2's outcome detail.

Then offer the user concrete iteration moves: "swap the technical evidence bullet to X", "shift tone toward more formal", "rewrite P4 around [topic]", "tighten P3".

## Banned phrases (all tones)

These mark the letter as generic and get it skipped:

```
passionate about, deeply passionate, team player, synergy, synergize,
leverage (as verb), value-add, hit the ground running, dynamic environment,
fast-paced environment, wear many hats, results-driven, go-getter, guru,
ninja, rockstar, world-class, best of breed, thought leader, paradigm shift,
"I would love to", "I am writing to", "I would like to apply"
```

Also avoid: starting consecutive paragraphs with "I". Start at most 2 paragraphs with "I"; vary openers ("Your platform…", "What drew me…", "Reading the ad…").

## Constraints

- Never invent achievements not backed by a bullet in the bank.
- Never copy a bullet verbatim — narrate it.
- Never include confidential content (`BOUNDARIES.md`).
- Never claim numbers that aren't already in the bank.
- One page. ≤ 350 words. Always.

## Example trigger phrases

- "Write a cover letter for this Conserve It role: «ad»"
- "Draft a cover letter against the conserve-it spec"
- "Add a cover letter to the existing job-ad spec for «Company»"
- "Cover letter for this job"
