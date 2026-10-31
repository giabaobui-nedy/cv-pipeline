# Bullet bank fields

Each role file (`soniq.yml`, `csiro.yml`, `canonical.yml`) has a `role:` block and a `bullets:` list.
`projects.yml` has a `projects:` list, and each project has its own `bullets:`.
Run `python3 tools/lint_bank.py` after every edit.

## role (role files only)

| Field | Meaning |
|---|---|
| `title`, `employer`, `dates`, `location` | Rendered in the CV heading. A spec can override any of them. |
| `start`, `end` | `YYYY-MM`. Omit `end` for the current role. tailor-cv sums these to compute YoE. |

## Bullet fields

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Unique across all files. Prefix with the bank (`soniq-`, `csiro-`, `canonical-`, `<project-id>-`). |
| `tags` | yes | 3 to 6 tags from `tags.yml`, plus `impact-metric` if the text has a number. |
| `text` | yes | LaTeX for `\resumeItem{...}`. No em dashes (`---` or the Unicode dash). |
| `note` | no | Honesty limits. Every skill must read it before using the bullet. |
| `status` | no | `outdated` means never select. The renderer refuses it. |
| `explanation` | no | Background for interviews. Never rendered. |
| `variant_group` | no | Versions of one story (long, compact, angle). The renderer refuses two from one group. |
| `story` | no | Separate bullets about one piece of work. The renderer warns when a CV uses more than 2. |
| `metric` | with `impact-metric` | `source` (Cost Explorer, Jira key, test run), `baseline`, `window`, `note`. `source: unverified ...` makes lint warn. |
| `ownership` | no | `led`, `owned`, `co-built` or `contributed`. Lint blocks "Led", "Architected" or "Spearheaded" on `co-built` or `contributed`. |
| `env` | no | List of `dev`, `staging`, `prod`. Never imply production when `prod` is absent. |
| `ai_framing` | no | `user` (used AI tools to ship work) or `builder` (built AI features or agents). |

## Length

Lint reports each bullet's word count. Bullets over 45 words need a compact twin in the same
`variant_group` (about 25 to 30 words). tailor-cv budgets the page by word count.
