# Pipeline Principles

Cross-cutting rules every skill (`tailor-cv`, `write-cover-letter`, `add-bullet`)
must respect. Updates here propagate to every application — change once,
everything inherits.

## 1. Honesty over keywords

The bullet bank is the **single source of truth**. Never:

- Invent achievements not in the bank.
- Inflate scope ("led" when you contributed; "designed" when you implemented;
  "architected" when you assisted). The bank's verbs are the ceiling, not a
  starting point.
- Add a keyword to a bullet's narration that the underlying achievement
  doesn't actually support.
- Claim metrics you don't have.
- Generalise an experience into a stronger one ("microservices experience"
  when one bullet touched microservices and the rest was monolith work).

When an ad asks for something the bank can't honestly cover, **tell the user
explicitly**: "no bullet supports requirement X — consider adding one via
`add-bullet`, or accept the gap and move on." Never paper over it.

The CV is a contract. Every line must survive a 30-minute interview
cross-examination. The cover letter narrates the same contract; it can
shape emphasis but cannot exceed the bank.

## 2. Optimise for both ATS and the recruiter's manual screen

Target: AU big-tech hiring (Atlassian, Canva, Macquarie, AWS AU, Google AU,
Stripe AU, Datadog AU, etc.) with tight ATS and harder manual screens.
Observed bottleneck: applications get past ATS but stall at the manual
screen — held in queue, then ghosted. The fix is **differentiation density
in the first 8-second skim**, not more keywords.

### ATS layer (already handled)

Engine-agnostic LaTeX, plain-text PDF, `\pdfgentounicode` when available,
`*-stack` bullets per role to anchor keywords, `keywords:` field in spec
mirrors the ad's vocabulary. Don't break these.

### Manual screen layer (where we lose)

The recruiter's 8-second skim path:

1. Name + location + **work rights** (see Principle 3).
2. Most recent employer + role title.
3. First 1–2 bullets of that role.
4. Profile paragraph (read only if the rest looks interesting).
5. Education credential ("Highest Achieving Graduate" + GPA).

Implications:

- The first non-overview bullet of each role **must be the strongest
  `impact-metric` bullet that matches the ad**. Never lead a role with a
  generic responsibility bullet.
- The Profile paragraph must mirror the ad's *primary* technical signal in
  its first sentence — recruiters read sentence one and bounce.
- Drop weak bullets aggressively. Recruiters read fewer lines than candidates
  think.
- Cover letter: first 8 words must be unique to *this* company; the
  technical-evidence paragraph must use a quantified outcome, not a process
  narrative.

### Projects are gap-fillers, not a fixture (experience-first policy, Aug 2026)

With nearly 2 years of paid production work on the CV, Experience carries the
application; Projects exist only to cover ad requirements Experience can't.

- **Default budget: 0–1 project, 1–2 bullets.** A CV with no Projects section
  is fine at this stage — spend the reclaimed space on more experience bullets.
- **Inclusion test**: a project earns its place only if it hits an ad keyword
  that zero experience bullets cover. If every project bullet is redundant
  with experience, drop the section.
- **Uni-era projects age out first** (Weekly Planner, TBRGS, Planner & Diary,
  Decentralised Trading, Battery Digital Twin) — they read increasingly junior
  next to production work. The **cv-pipeline** project is the exception:
  current, self-owned, real engineering, and uniquely strong evidence for
  AI-forward roles (it is a demonstrable agentic workflow).
- A second project is justified only when it covers a *second* uncovered
  requirement — and apply the test strictly. Worked example, Unity Care
  (Aug 2026): `cv-pipeline` stayed (nothing in experience answers
  "screen-share your agentic workflow"), but `weekly-planner-orm-tests`
  ("validate AI-generated code") was cut on review because
  `soniq-architectural-validation` already carried the AI-output-quality
  signal; the freed space went to `soniq-fallback-content`, a scheduling
  bullet matching the ad's domain.

### Pivoting from SONIQ → big tech

SONIQ is real production AWS / microservices / TypeScript work, but the
*product domain* (digital signage CMS) reads as small-company to a big-tech
recruiter. Mitigations the skills should apply by default:

- **Lead with engineering substance, not product domain.** Cost optimisation,
  TypeScript migration, event-driven Shopify integration, infrastructure
  scheduling — these read as big-tech work. "Digital signage" framing is
  background, not foreground.
- **Omit `soniq-overview` by default for big-tech tailoring.** It names
  "digital signage CMS" prominently. The `*-stack` line + impact bullets
  carry the signal without the product-domain anchor. Re-include only if the
  target company actually does media/CMS/AdTech work.
- **Cover letter technical paragraph: never lead with signage-specific nouns**
  ("displays", "playback", "client deployments"). Lead with the architecture
  or infra noun ("event-driven cost optimisation on AWS Lambda + EventBridge").
- **Big-tech vocabulary preferred when narrating** (where honestly applicable):
  *distributed systems, cloud-native, event-driven, infrastructure-as-code,
  production, scalability, reliability, observability, blast radius*. Most
  of these already appear as bank tags — use them deliberately.

## 3. International / Subclass 485 visa optimisation

The user holds an Australian Subclass 485 (Temporary Graduate) visa with
**full work rights** and **no sponsorship required** for the duration of the
visa. Most AU big-tech employers can hire 485 holders as standard hires —
but recruiters reject conservatively when work-rights status is unclear or
hidden.

### Rules

1. **CV does not carry the work-rights line.** Earlier policy was to put it on the contact line of the CV, but in practice it cost a wrap-line that pushed tailored CVs to two pages without buying meaningful signal — most AU recruiters assume work rights and ask in the application form anyway. Keep the CV's contact block tight: phone, email, LinkedIn, GitHub, Portfolio. Nothing else.
2. **Cover letter contact block carries the canonical line.** That's where the visa statement lives by default:
   ```
   Australian work rights --- Subclass 485 (valid to January 2028)
   ```
   Long form preferred. Short form (`AU work rights (Subclass 485)`) only inside ~6 months of expiry until renewal lands.
3. **Frame positively, never apologetically.** "Australian work rights" first, "(Subclass 485…)" as supporting detail. Never write "looking for sponsorship" (untrue for 485) or "happy to discuss visa" (invites uncertainty).
4. **Detect ad gates before drafting.** If the ad says "Australian/NZ citizens or PR only" (common in defence, government, banking, some financial services), **flag this and ask the user whether to proceed** before writing anything. Do not silently submit.
5. **Cover letter body handling.** If the ad does not gate on PR, do *not* raise the visa in the body — the contact-line statement is enough. If the ad explicitly mentions sponsorship as a benefit or names visa support, briefly note in P5: "I have full Australian work rights via the Subclass 485 visa, so no sponsorship is required." This turns a perceived blocker into an asset.
6. **Application-form fields trump the CV.** Most AU job portals have a dedicated "do you have full work rights?" question. Answer it there. The cover letter's contact line is the backup signal for the manual screen.

### Form fields with a "now or in the future" clause

Some AU portals go past the simple work-rights tickbox and force a choice between:

- *"I currently hold a valid visa (and can freely commence work, with no support required)"*
- *"I currently hold a valid visa on a temporary basis (and would require visa assistance in the future)"*

then add a free-text prompt: *"If you require any visa assistance (either now or in the
future), please let us know details below."* (Observed: Xero, August 2026.)

The 485 makes the **first** option true today and the **second** option true from expiry
(January 2028) onward. The choice therefore turns on a future fact the radio buttons
cannot capture, and the two options are not actually mutually exclusive for a 485 holder.

**Default: pick the "no support required" option, and disclose the expiry in the box.**

- The parenthetical in that option is a claim about *commencing work*, which is
  unambiguously true — you can start tomorrow and the employer does nothing.
- The box then carries the temporary status, so nothing is concealed.
- Picking the "requires assistance" option self-selects into the sponsorship bucket over
  a question about 2028. That is a disproportionate cost at the screening stage, where
  the reviewer is deciding whether hiring you is complicated *now*.

Canonical box text:

```
I hold a Subclass 485 (Temporary Graduate) visa with full Australian working rights,
valid to January 2028. No visa support is required to commence or for the foreseeable
term of the visa. As the 485 is temporary, I would be seeking permanent residency ahead
of its expiry, and I am happy to discuss options closer to the time.
```

**Never leave the box empty when the question says "now or in the future."** Silence
there is the version that reads as concealment if it surfaces later — which is a far
worse outcome than an early conversation about PR timing.

**Exception.** If PR is genuinely *not* being pursued independently and employer
sponsorship would be needed at expiry, pick the "assistance in the future" option.
Honest disclosure beats a rescinded offer. This is a decision for the user, not the
agent — surface the trade-off and let them choose.

**Do not answer this from the agent's memory of the expiry date.** Prompt the user to
confirm the current 485 stream and expiry on VEVO before submitting, and note that PR
strategy is a question for a registered migration agent, not this pipeline.

### When to renew the canonical phrasing

Update `cv/cover-letter.tex.template` (and check `cv/main.tex` / `cv/tailored.tex.template` haven't drifted back to including it) if the visa is renewed or the expiry shifts. The CV templates should remain free of the work-rights line.

## 4. CV is the contract; cover letter is the narrative

Industry assumption: **most companies skip the cover letter**. Estimates vary, but a useful working number is *~70% never read it*. The CV must therefore be **self-sufficient** — every essential signal (work rights, top impact bullets, stack anchors, education credential, contact details) lives in the CV regardless of whether the cover letter is opened.

This creates an apparent tension with the standard "don't repeat yourself between CV and cover letter" advice. Resolve it like this:

### The rule, restated

- **Don't repeat language.** Never copy a CV bullet sentence verbatim into the cover letter.
- **Do reuse facts.** It is correct — and often necessary — for the cover letter's load-bearing paragraph (P2 technical) to draw on the same achievement that the CV's load-bearing bullet describes.
- **Different layer of zoom.** The CV bullet states *what was built and the outcome*. The cover letter narrates *the why, the mechanism, and the lesson learned* — the depth the bullet's word budget cannot afford.

### Practical implications

| Question | Answer |
|---|---|
| Where do new facts go? | Bullet bank (then optionally CV). Never cover-letter-only. If the cover letter would need to introduce a new claim to be effective, force-promote it into a bullet via `add-bullet`, then narrate it in the cover letter. |
| Can two paragraphs (P2 technical, P3 values) reference bullets that are already on the CV? | Yes — preferred, in fact. The cover letter's job is to *deepen* the most relevant achievements, not to find different ones. |
| What belongs ONLY in the cover letter? | Specificity (P1 hook tied to *this* company), the *story / lesson* layer of an achievement (P2), values fit narration (P3 — often net-new tone, but the underlying behaviour must be backed by a bullet), forward-looking intent (P4 — net-new). |
| What belongs ONLY in the CV? | Hard credentials (work rights, GPA, degree, dates), the comprehensive list of impact bullets, the keyword-dense skills block, project links/demos. |
| What goes in both? | The 1–2 load-bearing achievements that anchor the application — at different zoom levels. |

### Failure modes to avoid

- **Cover letter restates the CV bullet text.** Solution: narrate the *story* (mechanism, why, lesson), don't paraphrase the outcome.
- **Cover letter introduces a fact the CV doesn't support.** Solution: stop, run `add-bullet`, then continue.
- **CV depends on the cover letter to land a critical signal** (e.g. work rights only mentioned in the cover letter). Solution: every must-land signal goes in the CV.

## 5. Workflow when a job ad arrives

A consistent pipeline so context compounds across artefacts:

```
job ad lands
  ↓
1. research-company   →  job-ads/<slug>/research.md
  ↓
2. tailor-cv          →  job-ads/<slug>/spec.yml  +  outputs/<slug>/cv.pdf
  ↓
3. write-cover-letter →  cover_letter: block in spec.yml  +  outputs/<slug>/cover.pdf
  ↓
4. tools/export.sh    →  ~/Desktop/(YYYY.MM.DD) Gia Bao Bui - <role> - <company>.pdf
                          ~/Desktop/(YYYY.MM.DD) Gia Bao Bui - Cover letter - <company>.pdf
```

### Why this order

1. **Research first** so bullet selection (step 2) and paragraph anchors (step 3) draw from the same factual ground rather than diverging. Research surfaces the *project shape* (digital twin? embedded? real-time ML?), which is the largest single influence on which bullets win.
2. **CV next** because bullet selection forces explicit decisions about which 12–15 lines best match the role. Those decisions become the cover letter's evidence pool — Principle 4 says the CL narrates the same achievements at deeper zoom, so the CL can't be drafted well until the CV's selections are locked.
3. **Cover letter last** because it's the most editable and least load-bearing artefact (Principle 4 again — many recruiters skip it). It can also be skipped entirely if the application form doesn't accept one.

### When to deviate

- **Tight deadline (< 2 hours)**: do a *light* research pass (product page + one news item), draft CV, optionally skip the cover letter. Mark the cover letter as `ad-only-light-research` if produced.
- **Senior referral / warm intro**: the referrer's context partially substitutes for company research. Still write a brief `research.md` capturing what the referrer told you — future-you will want it.
- **Application without ad text** (e.g. through a recruiter): research-company shifts to "research the team and the most likely product" and produces an `open-questions` section to ask the recruiter before final submission.

### Per-application file layout

```
job-ads/<slug>/
  spec.yml        # CV + cover letter spec (single source per application)
  research.md     # output of research-company (Layers 1–5 + Synthesis)
  ad.txt          # optional — original ad text saved verbatim, for grep

outputs/<slug>/
  cv.tex / cv.pdf
  cover.tex / cover.pdf
```

`<slug>` is kebab-case ASCII (e.g. `Conserve It` → `conserve-it`). One folder per application; the folder name *is* the slug.

---

## How skills inherit these principles

Each skill's `SKILL.md` contains a section titled **"Cross-cutting
principles"** that links here. Skills must:

- Apply Principle 1 to every artefact they generate (no fabrication).
- Apply Principle 2's ordering and pivoting rules to bullet selection,
  paragraph drafting, and shortlist proposals.
- Apply Principle 3 to all CV and cover-letter outputs targeting AU
  employers.

If a principle conflicts with a skill-specific rule, the principle wins
and the skill should be edited to align.
