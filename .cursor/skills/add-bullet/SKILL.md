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
to the right bullet-bank file (and optionally mirror it into `cv/main.tex`).

## Repo invariants

- Bullets live in `bullet-bank/{soniq,csiro,projects}.yml`.
- Each bullet has `id` (unique, kebab-case), `tags` (free-form list), and `text` (LaTeX-ready content of `\resumeItem{...}`).
- Master CV at `cv/main.tex` is the canonical narrative — keep it in sync when the user wants the new bullet on the master too.
- Confidentiality rules in `BOUNDARIES.md` apply — generalise before storing.

## Workflow

```
- [ ] 1. Classify the bullet (which bank?)
- [ ] 2. Polish wording (await user approval)
- [ ] 3. Assign id + tags
- [ ] 4. Append to bullet bank
- [ ] 5. Mirror to cv/main.tex (optional)
```

### 1. Classify

Decide which bank the bullet belongs to:

- **`soniq.yml`** — work at SONIQ Digital (Feb 2026 – Present).
- **`csiro.yml`** — work at CSIRO (Mar 2024 – Jun 2025).
- **`projects.yml`** — personal/uni/side projects. If it's for an **existing** project, find the project block and append to its `bullets`. If it's a **new** project, draft a new project entry (id/title/stack/links/tags) and ask the user for the missing metadata (link URL, stack list).

If unclear, ask the user.

### 2. Polish wording

Apply the house style of the existing bank:

- Start with a strong verb in past tense (Designed, Implemented, Led, Engineered, Refactored, Architected, Investigated, …). Use present participle ("Contributing to…") only for the role-overview bullet.
- Lead with **what was built / changed**, follow with the **measurable or qualitative outcome**.
- Quantify when possible (`\textbf{N\%}`, time saved, cost reduction). Wrap percentages and key numbers in `\textbf{…}` to mirror existing impact bullets.
- 1–3 sentences max. Aim for one line in the rendered PDF (~25 words).
- Plain LaTeX inside the `text` value: use `\textbf{...}`, `\emph{...}`, `\href{...}{...}`, `$\rightarrow$` for arrows, `$\times$` for ×, `\&` for &, `\%` for %, `---` for em-dashes, `--` for en-dashes.
- Generalise away confidential details (no client names, no internal tool names, no exact business metrics that aren't already public). If unsure, flag and ask.

Show the polished bullet to the user and **wait for approval** before writing.

### 3. Assign id + tags

- **id**: kebab-case, prefixed with the bank. SONIQ → `soniq-...`, CSIRO → `csiro-...`, project bullets → `<project-id>-...` (e.g. `battery-modular-backend`). Must be unique within the file.
- **tags**: 3–6 lowercase, hyphenated themes. Reuse existing tags from the same bank where possible (read the file and prefer tags that already appear). Add new tags only when no existing one fits. Always include an `impact-metric` tag if the bullet contains a quantified outcome.

### 4. Append

Append the new entry to the relevant `bullet-bank/*.yml` file under the existing `bullets:` (or, for project bullets, the project's `bullets:` list). Preserve indentation. Do not reorder existing entries.

After writing, run a quick parse check:

```bash
.venv/bin/python -c "import yaml; yaml.safe_load(open('bullet-bank/<file>.yml'))"
```

### 5. Mirror to cv/main.tex (optional)

Ask the user: **"Add this to the master CV (`cv/main.tex`) as well?"**

If yes:

- For SONIQ/CSIRO: insert a new `\resumeItem{...}` line in the corresponding role's `\resumeItemListStart` block, immediately before the `\textbf{Stack:}` bullet.
- For project bullets: insert inside the project's `\resumeItemListStart` block.
- The text inside `\resumeItem{...}` must match the bullet bank's `text` exactly — keep them synchronised.

If no, remind the user that tailored CVs can use the new bullet immediately, but `main.tex` will lag until they choose to mirror it.

## Constraints

- Never write fictionalised work or numbers. If the user's wording is vague, ask for the metric rather than inventing one.
- Never bypass `BOUNDARIES.md`.
- Never silently overwrite an existing bullet with the same `id` — append a numeric suffix or ask.

## Example trigger phrases

- "Add this to my SONIQ bullets: I just shipped …"
- "Log a new achievement: …"
- "Update the bullet bank with this project win"
- "I just did X at work, get it into the CV"
