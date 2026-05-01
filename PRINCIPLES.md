# Pipeline Principles

Cross-cutting rules every skill (`tailor-cv`, `cover-letter`, `add-bullet`)
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

1. **State work rights explicitly and early.** Recommended placement:
   contact line of every CV and cover letter. Don't bury it; don't omit it.
   Long form: `Australian work rights — Subclass 485 (valid to <YYYY-MM>)`.
   Short form when tight: `AU work rights (Subclass 485)`.
2. **Frame positively, never apologetically.** "Australian work rights"
   first, "(Subclass 485…)" as supporting detail. Never write "looking for
   sponsorship" (untrue for 485) or "happy to discuss visa" (invites
   uncertainty).
3. **Detect ad gates before drafting.** If the ad says "Australian/NZ
   citizens or PR only" (common in defence, government, banking, some
   financial services), **flag this and ask the user whether to proceed**
   before writing anything. Do not silently submit.
4. **Cover letter body handling.** If the ad does not gate on PR, do *not*
   raise the visa in the body — the contact-line statement is enough. If the
   ad explicitly mentions sponsorship as a benefit or names visa support,
   briefly note in P5: "I have full Australian work rights via the Subclass
   485 visa, so no sponsorship is required." This turns a perceived blocker
   into an asset.
5. **Wire it to the spec.** Set `work_rights:` once at the top of the
   job-ad spec (or default it from the example). The renderer should pick
   it up so it never gets forgotten on any output.

### Canonical phrasing (currently in templates)

The contact block of `cv/main.tex`, `cv/tailored.tex.template`, and
`cv/cover-letter.tex.template` already carries:

```
Australian work rights --- Subclass 485 (valid to January 2028)
```

Update all three together if the visa is renewed or the expiry shifts.
When the date is within ~6 months of expiry, switch to the short form
(`AU work rights (Subclass 485)`) until renewal lands.

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
