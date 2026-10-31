---
name: add-bullet
description: >-
  Add a new bullet (achievement, project bullet, or skills line) to Gia Bao
  Bui's CV bullet bank, polishing the wording and assigning theme tags. Use
  when the user describes a new accomplishment, says "add this to my CV / bullet
  bank", wants to log a recent win, or asks to extend the master CV with a new
  achievement.
---

# Add Bullet

Polish a free-form achievement into a tagged, LaTeX-ready bullet and append it
to the right bullet-bank file. The master CV (`cv/master.yml`) picks it up automatically.

## Cross-cutting principles (read first)

Read `../../../PRINCIPLES.md` (at repo root) before drafting. The honesty
principle is the load-bearing one for this skill — every bullet added here
becomes a fact downstream skills will rely on:

1. **Honesty over keywords.** Never write a verb stronger than the user's
   actual scope ("led" vs "contributed to" vs "supported"). Never invent
   metrics — if the user's description is vague on numbers, ask, don't
   guess. Never embed keywords that don't reflect the underlying work just
   because they'd help a future ad search. The bank is the contract; this
   skill is what writes the contract.
2. **Optimise for the manual screen.** Big-tech recruiters favour outcome-
   first bullets with a quantified result. Frame as
   *"Verb + system/scope + outcome (with metric where honest)"*. Generic
   responsibility statements ("worked on X") are downgraded.
3. **Big-tech vocabulary preferred when honestly applicable.** Use
   *distributed systems, cloud-native, event-driven, infrastructure-as-code,
   observability, scalability* over signage-specific nouns. But never
   substitute a big-tech term for a literal description of what was done.

## Repo invariants

- Bullets live in `bullet-bank/*.yml`: one file per employer (`canonical.yml`, `soniq.yml`, `csiro.yml`) plus `projects.yml`.
- Every field is defined in `bullet-bank/README.md`. Required: `id`, `tags`, `text`. Optional: `note`, `status`, `explanation`, `variant_group`, `story`, `metric`, `ownership`, `env`, `ai_framing`.
- Tags come from `bullet-bank/tags.yml`. Add a new tag there first.
- The master CV is generated from the bank (`cv/master.yml` with `bullets: all`), so there is nothing to mirror by hand.
- Confidentiality rules in `BOUNDARIES.md` apply — generalise before storing.

## Workflow

```
- [ ] 1. Classify the bullet (which bank?)
- [ ] 2. Polish wording (await user approval)
- [ ] 3. Assign id + tags
- [ ] 4. Append to bullet bank
- [ ] 5. Run lint; refresh the master CV
```

### 1. Classify

Decide which bank the bullet belongs to:

- **`canonical.yml`** — work at Canonical (Nov 2026 – Present). Replace `canonical-overview` as the role's lead once real achievements exist.
- **`soniq.yml`** — work at SONIQ Digital (Feb 2026 – Oct 2026).
- **`csiro.yml`** — work at CSIRO (Mar 2024 – Jun 2025).
- **`projects.yml`** — personal/uni/side projects. If it's for an **existing** project, find the project block and append to its `bullets`. If it's a **new** project, draft a new project entry (id/title/stack/links/tags) and ask the user for the missing metadata (link URL, stack list).

If unclear, ask the user.

### 2. Polish wording

Apply the house style of the existing bank:

- Start with a strong verb in past tense (Designed, Implemented, Led, Engineered, Refactored, Architected, Investigated, …). Use present participle ("Contributing to…") only for the role-overview bullet.
- Lead with **what was built / changed**, follow with the **measurable or qualitative outcome**.
- Quantify when possible (`\textbf{N\%}`, time saved, cost reduction). Wrap percentages and key numbers in `\textbf{…}` to mirror existing impact bullets.
- 1–3 sentences max. Aim for ~25 words. If the honest version needs more than 45, write a 25–30 word compact twin too and give both the same `variant_group`.
- Plain LaTeX inside the `text` value: use `\textbf{...}`, `\emph{...}`, `\href{...}{...}`, `$\rightarrow$` for arrows, `$\times$` for ×, `\&` for &, `\%` for %, `--` for en-dashes in ranges. **No em dashes** (`---` or the Unicode dash); use a comma, colon or new sentence. Lint fails on them.
- Avoid AI-sounding words (leveraged, spearheaded, robust, comprehensive, seamless, transforming). Lint warns on them.
- Vary the opening verb from the bullets already in the same role.
- Generalise away confidential details (no client names, no internal tool names, no exact business metrics that aren't already public). If unsure, flag and ask.

Show the polished bullet to the user and **wait for approval** before writing.

### 3. Assign id + tags

- **id**: kebab-case, prefixed with the bank. SONIQ → `soniq-...`, CSIRO → `csiro-...`, project bullets → `<project-id>-...` (e.g. `battery-modular-backend`). Must be unique within the file.
- **tags**: 3–6 tags from `bullet-bank/tags.yml` (8 at most). Add a new tag to `tags.yml` only when no existing one fits. Always include `impact-metric` if the bullet contains a quantified outcome.
- **metric** (required with `impact-metric`): ask the user where the number comes from. Record `source` (Cost Explorer, a Jira key, a test run), and `baseline` and `window` when the number is a change. If the user can't name a source, write `source: unverified (...)`; lint will keep warning until it is confirmed.
- **note**: record any honesty limit the user states ("dev only", "another engineer led it", "never claim production").
- **ownership** / **env** / **ai_framing**: set them when the user's description makes them clear. Lint blocks "Led" or "Architected" on a `co-built` or `contributed` bullet.
- **story**: reuse an existing `story` value when the bullet describes another part of the same piece of work.

### 4. Append

Append the new entry to the relevant `bullet-bank/*.yml` file under the existing `bullets:` (or, for project bullets, the project's `bullets:` list). Preserve indentation. Do not reorder existing entries.

After writing, run the lint and fix every `error:` line:

```bash
python3 tools/lint_bank.py
```

### 5. Refresh the master CV

Run `tools/compile.sh master`. It renders `cv/master.yml`, which includes every current bullet (one per `variant_group`), so the new bullet appears without hand edits. If the new work changes a stack (a new language or service), update that role's `*-stack` bullet too.

## Constraints

- Never write fictionalised work or numbers. If the user's wording is vague, ask for the metric rather than inventing one.
- Never bypass `BOUNDARIES.md`.
- Never silently overwrite an existing bullet with the same `id` — append a numeric suffix or ask.

## Example trigger phrases

- "Add this to my SONIQ bullets: I just shipped …"
- "Log a new achievement: …"
- "Update the bullet bank with this project win"
- "I just did X at work, get it into the CV"
