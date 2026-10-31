#!/usr/bin/env python3
"""Render a tailored CV from a job-ad spec + the bullet bank.

Usage:
    python tools/render_tailored.py job-ads/<slug>/spec.yml [-o outputs/<slug>/cv.tex]

The spec is a small YAML file (see job-ads/_example/spec.yml) that lists which
bullet IDs to include per role and which projects to include. The renderer
fills `cv/tailored.tex.template` and writes a ready-to-compile .tex file.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from collections import Counter
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML not installed. Run: pip install -r requirements.txt")

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = REPO / "cv" / "tailored.tex.template"
BANK = REPO / "bullet-bank"


NON_ROLE_FILES = {"projects.yml", "tags.yml"}


def load_banks() -> tuple[dict[str, dict], dict[str, dict], dict[str, dict]]:
    """Return (role bullets by bank, role meta by bank, projects by id).

    Every bullet-bank/*.yml except projects.yml and tags.yml is a role bank,
    keyed by file stem, so a new employer only needs a new file.
    """
    role_banks: dict[str, dict] = {}
    role_meta: dict[str, dict] = {}
    for path in sorted(BANK.glob("*.yml")):
        if path.name in NON_ROLE_FILES:
            continue
        data = yaml.safe_load(path.read_text()) or {}
        role_banks[path.stem] = {b["id"]: b for b in data.get("bullets") or []}
        role_meta[path.stem] = data.get("role") or {}
    data = yaml.safe_load((BANK / "projects.yml").read_text()) or {}
    projects = {p["id"]: p for p in data.get("projects", [])}
    return role_banks, role_meta, projects


def plain_text(latex: str) -> str:
    """Rough LaTeX-to-text for word counts and keyword checks."""
    s = re.sub(r"\\(textbf|emph|texttt|textit)\{([^}]*)\}", r"\2", latex)
    s = s.replace("$\\rightarrow$", "->").replace("$\\sim$", "~").replace("$\\times$", "x")
    s = re.sub(r"\\[,;]", " ", s)
    s = re.sub(r"\\([%&$#_])", r"\1", s)
    return " ".join(s.split())


def _normalise(text: str) -> str:
    return " ".join(text.split())


def _latex_escape(text: object) -> str:
    """Escape plain-text spec values for LaTeX.

    Bullet-bank entries are already LaTeX-ready and should not pass through this
    helper. It is for structured spec fields such as skills categories/items.

    Accepts both plain text ("Cloud & DevOps") and pre-escaped LaTeX
    ("Cloud \\& DevOps") — pre-escaped sequences are normalised to plain text
    first so either form produces identical output.
    """
    s = str(text)
    # Normalise pre-escaped sequences so authors can write `&` or `\&` and get
    # the same result. Must run before the char-by-char escape pass below.
    for seq, plain in (
        (r"\&", "&"), (r"\%", "%"), (r"\$", "$"),
        (r"\#", "#"), (r"\_", "_"), (r"\{", "{"), (r"\}", "}"),
    ):
        s = s.replace(seq, plain)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in s)


def render_skills(skills: object) -> str:
    if isinstance(skills, str):
        return skills.strip()

    if not skills:
        return ""

    if not isinstance(skills, list):
        sys.exit("skills must be either a LaTeX string or a list of category/items mappings")

    lines = []
    for entry in skills:
        if not isinstance(entry, dict):
            sys.exit("each structured skills entry must be a mapping")

        category = entry.get("category")
        items = entry.get("items")
        if not category or not isinstance(items, list):
            sys.exit("each structured skills entry needs 'category' and list-valued 'items'")

        rendered_items = ", ".join(_latex_escape(item) for item in items)
        lines.append(f"\\textbf{{{_latex_escape(category)}}}{{: {rendered_items}}}")

    return " \\\\\n".join(lines)


def render_referees(referees: object) -> str:
    """Render the referee block.

    Monash and most AU public-sector portals require named referees on the CV
    itself, so this is a first-class section rather than a spec afterthought.
    """
    if not referees:
        return ""

    if not isinstance(referees, list):
        sys.exit("referees must be a list of name/title/organisation/email mappings")

    lines = []
    for entry in referees:
        if not isinstance(entry, dict):
            sys.exit("each referee entry must be a mapping")

        name = entry.get("name")
        if not name:
            sys.exit("each referee entry needs a 'name'")

        role_line = ", ".join(
            _latex_escape(entry[k])
            for k in ("title", "organisation")
            if entry.get(k)
        )

        contacts = []
        if entry.get("email"):
            email = _latex_escape(entry["email"])
            contacts.append(f"\\href{{mailto:{entry['email']}}}{{{email}}}")
        if entry.get("phone"):
            contacts.append(_latex_escape(entry["phone"]))
        if entry.get("relationship"):
            contacts.append(_latex_escape(entry["relationship"]))

        head = f"\\textbf{{{_latex_escape(name)}}}"
        if role_line:
            head += f" --- {role_line}"
        if contacts:
            head += " \\newline " + " $|$ ".join(contacts)
        lines.append(head)

    return " \\\\[2pt]\n".join(lines)


def render_role(role_meta: dict, bullets: list[dict]) -> str:
    """`role_meta` is the bank's role block overlaid with the spec's fields."""
    items = [f"            \\resumeItem{{{_normalise(b['text'])}}}" for b in bullets]
    stack = role_meta.get("stack")
    if stack:
        items.append(
            f"            \\resumeItem{{\\textbf{{Stack:}} \\emph{{{_latex_escape(stack.strip())}}}}}"
        )
    head = (
        f"      \\resumeSubheading\n"
        f"          {{{role_meta['title']}}}{{{role_meta['dates']}}}\n"
        f"          {{{role_meta['employer']}}}{{{role_meta['location']}}}"
    )
    if not items:
        # A new role can be listed before it has achievements; an empty itemize breaks LaTeX.
        return head
    items_block = "\n".join(items)
    return (
        f"{head}\n"
        f"            \\resumeItemListStart\n"
        f"{items_block}\n"
        f"            \\resumeItemListEnd"
    )


def render_project(proj: dict, bullets: list[dict]) -> str:
    links = " $|$ ".join(
        f"\\href{{{l['url']}}}{{{l['label']}}}" for l in proj.get("links", [])
    )
    items = [f"                \\resumeItem{{{_normalise(b['text'])}}}" for b in bullets]
    return (
        f"        \\resumeProjectHeading\n"
        f"            {{{proj['title']} $|$ \\emph{{{proj['stack']}}}}}{{{links}}}\n"
        f"            \\resumeItemListStart\n"
        f"{chr(10).join(items)}\n"
        f"            \\resumeItemListEnd"
    )


def expand_all(pool: dict[str, dict]) -> list[str]:
    """`bullets: all` (used by cv/master.yml): every current bullet, one per
    variant_group (the first listed, which is the long version), stack line last."""
    seen: set[str] = set()
    body, stack = [], []
    for bid, b in pool.items():
        group = b.get("variant_group")
        if b.get("status") == "outdated" or (group and group in seen):
            continue
        if group:
            seen.add(group)
        (stack if "stack" in b.get("tags", []) else body).append(bid)
    return body + stack


def parse_start(value: object) -> dt.date | None:
    """role.start is YYYY-MM or YYYY-MM-DD; a bare month means its first day."""
    parts = str(value or "").split("-")
    if len(parts) < 2:
        return None
    day = int(parts[2]) if len(parts) > 2 else 1
    return dt.date(int(parts[0]), int(parts[1]), day)


def _has_token(token: str, text: str) -> bool:
    # Whole-token match, so "java" does not match inside "javascript".
    return re.search(rf"(?<![a-z0-9+#]){re.escape(token)}(?![a-z0-9+#])", text) is not None


def selection_warnings(spec: dict, selected: list[dict], extra_evidence: list[str]) -> list[str]:
    """Non-blocking checks on the chosen bullets. See tailor-cv for the rules."""
    warns = []
    stories = Counter(b["story"] for b in selected if b.get("story"))
    warns += [f"{n} bullets from story '{s}'; more than 2 reads as padding" for s, n in stories.items() if n > 2]

    body = [b for b in selected if "stack" not in b.get("tags", [])]
    verbs = Counter(plain_text(b["text"]).split()[0].lower() for b in body if b["text"].strip())
    warns += [f"{n} bullets open with '{v}'; vary the opening verbs" for v, n in verbs.items() if n > 2]

    for b in selected:
        if "---" in b["text"] or "\u2014" in b["text"]:
            warns.append(f"{b['id']} contains an em dash")
        if b.get("note"):
            warns.append(f"{b['id']} has a note; confirm the CV respects it: {' '.join(b['note'].split())}")

    evidence = " ".join([plain_text(b["text"]) for b in selected] + extra_evidence).lower().replace(".js", "")
    skills = spec.get("skills") if isinstance(spec.get("skills"), list) else []
    for entry in skills:
        for item in entry.get("items", []):
            item_text = str(item).lower().replace(".js", "")
            tokens = [t for t in re.split(r"[\s(),/&]+", item_text) if t]
            if len(tokens) > 1:
                tokens = [t for t in tokens if len(t) > 1]
            if tokens and not any(_has_token(t, evidence) for t in tokens):
                warns.append(f"skills item '{item}' is not backed by any selected bullet, stack line or project stack")

    # Stack lines list tools by design, so only prose counts toward keyword stuffing.
    text = " ".join([plain_text(spec.get("profile", ""))] + [plain_text(b["text"]) for b in body]).lower()
    for kw in spec.get("keywords", []):
        n = len(re.findall(rf"(?<![a-z]){re.escape(str(kw).lower())}(?![a-z])", text))
        if n > 4:
            warns.append(f"keyword '{kw}' appears {n} times; more than 3 or 4 reads as stuffing")
    return warns


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=None)
    args = ap.parse_args()

    spec = yaml.safe_load(args.spec.read_text()) or {}
    role_banks, role_metas, projects = load_banks()
    template = TEMPLATE.read_text()
    errors: list[str] = []
    selected: list[dict] = []

    def pick(bid: str, pool: dict[str, dict], where: str) -> dict | None:
        b = pool.get(bid)
        if b is None:
            errors.append(f"unknown bullet id {bid} ({where})")
        elif b.get("status") == "outdated":
            errors.append(f"{bid} is marked status: outdated ({where}); pick its replacement")
        else:
            selected.append(b)
        return b

    # Matches tailor-cv H1: Highest Achieving Graduate only, unless the spec says otherwise.
    default_education_bullets = [
        r"Recognised as \textbf{Highest Achieving Graduate} in the Bachelor of Computer Science (Professional) cohort.",
    ]
    education_bullets = spec.get("education_bullets", default_education_bullets)
    if education_bullets:
        education_items = "\n".join(
            f"            \\resumeItem{{{_normalise(b)}}}" for b in education_bullets
        )
        education_list_block = (
            "        \\resumeItemListStart\n"
            f"{education_items}\n"
            "        \\resumeItemListEnd\n"
        )
    else:
        education_list_block = ""

    experience_blocks = []
    extra_evidence: list[str] = []
    today = dt.date.today()
    for role in spec.get("experience", []):
        bank = role_banks.get(role["bank"])
        if bank is None:
            sys.exit(f"unknown bank '{role['bank']}' (known: {list(role_banks)})")
        meta = {**role_metas[role["bank"]], **{k: v for k, v in role.items() if k != "bullets"}}
        start = parse_start(meta.get("start"))
        if start and start > today and not spec.get("allow_future_roles"):
            errors.append(
                f"role {role['bank']} starts on {start:%d %b %Y}, after today; drop it from the spec "
                "until then (or set allow_future_roles: true for a draft you won't send yet)"
            )
            continue
        extra_evidence.append(str(meta.get("stack", "")))
        missing = [k for k in ("title", "dates", "employer", "location") if not meta.get(k)]
        if missing:
            errors.append(f"role {role['bank']} has no {missing} in the spec or the bank's role block")
            continue
        ids = expand_all(bank) if role.get("bullets") == "all" else role.get("bullets", [])
        bullets = [b for bid in ids if (b := pick(bid, bank, role["bank"]))]
        bullets = [b for b in bullets if b.get("status") != "outdated"]
        experience_blocks.append(render_role(meta, bullets))

    project_blocks = []
    proj_specs = spec.get("projects", [])
    if proj_specs == "all":
        proj_specs = [{"id": pid, "bullets": "all"} for pid in projects]
    for proj_spec in proj_specs:
        proj = projects.get(proj_spec["id"])
        if proj is None:
            errors.append(f"unknown project {proj_spec['id']}")
            continue
        pool = {b["id"]: b for b in proj.get("bullets", [])}
        extra_evidence.append(str(proj.get("stack", "")))
        ids = expand_all(pool) if proj_spec.get("bullets") == "all" else proj_spec.get("bullets", [])
        bullets = [b for bid in ids if (b := pick(bid, pool, proj["id"]))]
        bullets = [b for b in bullets if b.get("status") != "outdated"]
        project_blocks.append(render_project(proj, bullets))

    groups = Counter(b["variant_group"] for b in selected if b.get("variant_group"))
    for group, n in groups.items():
        if n > 1:
            errors.append(f"{n} bullets from variant_group '{group}'; keep one version of a story")

    if errors:
        sys.exit("error: " + "\nerror: ".join(errors))

    # The master lists everything on purpose, so selection warnings are noise there.
    for w in ([] if spec.get("page_mode") == "master" else selection_warnings(spec, selected, extra_evidence)):
        print(f"warn: {w}", file=sys.stderr)

    sections = {
        "profile": (
            "\\section{Profile}\n"
            f"\\small{{ {spec.get('profile', '').strip()} }}\\justifying"
        ),
        "experience": (
            "\\section{Experience}\n"
            "  \\resumeSubHeadingListStart\n"
            f"{chr(10).join(experience_blocks)}\n"
            "  \\resumeSubHeadingListEnd"
        ),
        "projects": (
            "\\section{Projects}\n"
            "    \\resumeSubHeadingListStart\n"
            f"{chr(10).join(project_blocks)}\n"
            "    \\resumeSubHeadingListEnd"
        ),
        "skills": (
            "\\section{Technical Skills}\n"
            "\\begin{itemize}[leftmargin=0.15in, label={}]\n"
            "\\small{\\item{\n"
            f"{render_skills(spec.get('skills', ''))}\n"
            "}}\n"
            "\\end{itemize}"
        ),
        "referees": (
            "\\section{Referees}\n"
            "\\begin{itemize}[leftmargin=0.15in, label={}]\n"
            "\\small{\\item{\n"
            f"{render_referees(spec.get('referees'))}\n"
            "}}\n"
            "\\end{itemize}"
        ),
        "education": (
            "\\section{Education}\n"
            "  \\resumeSubHeadingListStart\n"
            "    \\resumeSubheading\n"
            "      {Swinburne University of Technology}{Hawthorn, VIC}\n"
            "      {Bachelor of Computer Science (Professional), Major in Software Development}{GPA: 3.88/4 | Feb 2022 -- Dec 2025}\n"
            f"{education_list_block}"
            "  \\resumeSubHeadingListEnd"
        ),
    }

    default_order = ["profile", "experience", "projects", "skills", "education"]
    # `referees` is opt-in: only AU public-sector / university portals require it.
    order = spec.get("section_order", default_order)
    unknown = [s for s in order if s not in sections]
    if unknown:
        sys.exit(f"unknown section(s) in section_order: {unknown} (known: {list(sections)})")

    out = template.replace(
        "{{SECTIONS}}", "\n\n".join(sections[s] for s in order)
    )

    slug = args.spec.parent.name
    out_path = args.output or (REPO / "outputs" / slug / "cv.tex")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out)
    body = [b for b in selected if "stack" not in b.get("tags", [])]
    words = sum(len(plain_text(b["text"]).split()) for b in body)
    print(f"wrote {out_path} ({len(body)} bullets, {words} bullet words, "
          f"{len(spec.get('profile', '').split())} profile words)")


if __name__ == "__main__":
    main()
