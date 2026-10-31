#!/usr/bin/env python3
"""Render a cover letter from a job-ad spec.

Usage:
    python tools/render_cover_letter.py job-ads/<slug>/spec.yml [-o outputs/<slug>/cover.tex]

Reads the `cover_letter` block of the spec and fills `cv/cover-letter.tex.template`.
If the spec has no `cover_letter` block, exits with code 2 (skipped, not an error).
"""
from __future__ import annotations

import argparse
import re
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_tailored import load_banks, prose_escape  # noqa: E402

try:
    import yaml
except ImportError:
    sys.exit("PyYAML not installed. Run: pip install -r requirements.txt")

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = REPO / "cv" / "cover-letter.tex.template"


def _normalise(text: str) -> str:
    return " ".join((text or "").split())


def _body(text: str) -> str:
    """Paragraph text: escape bare %, & and #, and use proper LaTeX quotes."""
    return prose_escape(text)


TONES = {
    "startup_scrappy", "corporate_formal", "research_scientific", "consultancy_clientfacing",
    "mission_driven", "agency_recruiter", "public_sector_pitch", "hybrid_warm_professional",
}


def render_recipient(cl: dict) -> str:
    """Build the LaTeX recipient block. All fields optional; render what we have."""
    lines: list[str] = []
    name = cl.get("recipient_name")
    company = cl.get("company") or cl.get("recipient_company")
    # A generic name only repeats the salutation, so only a real person gets a line.
    if name and name.strip().lower() not in {"hiring manager", "hiring team", "recruitment team"}:
        lines.append(name)
    if company:
        lines.append(f"\\textbf{{{company}}}")
    address = cl.get("recipient_address")
    if address:
        for line in str(address).strip().splitlines():
            line = line.strip()
            if line:
                lines.append(line)
    return " \\\\\n".join(lines)


PLACEHOLDER = re.compile(r"<[^>\n]{1,40}>|\[(?:company|role|name|team|product)[^\]]*\]|\{\{|\bTODO\b|\bTBD\b|lorem ipsum", re.I)
CHATBOT = re.compile(r"\b(here is|here's (?:a|your)|certainly[,!]|as an ai|i hope this (?:helps|letter finds)|feel free to)\b", re.I)
HIDDEN = re.compile(r"\\color\{white\}|\\textcolor\{white\}|\\phantom|\\tiny|\\scriptsize")


def presend_problems(cl: dict, paragraphs: dict, used: list[str], company: str) -> list[str]:
    """Blocking checks before a letter can be compiled."""
    problems = []
    # write-cover-letter rules C1, C2 and C4.
    for field in ("recipient_name", "salutation", "tone"):
        if not cl.get(field):
            problems.append(f"missing cover_letter.{field} (rule C1)")
    if cl.get("tone") and cl["tone"] not in TONES:
        problems.append(f"tone '{cl['tone']}' is not one of {sorted(TONES)} (rule C2)")
    role_banks, _, projects = load_banks()
    known = {bid for bank in role_banks.values() for bid in bank}
    known |= {b["id"] for p in projects.values() for b in p.get("bullets", [])}
    evidence = cl.get("evidence") or {}
    for kind in ("technical", "values"):
        bid = evidence.get(kind)
        if not bid:
            problems.append(f"missing cover_letter.evidence.{kind} (rule C1)")
        elif bid not in known:
            problems.append(f"evidence.{kind} '{bid}' is not a bullet ID in the bank (rule C4)")
    body = " ".join(_normalise(paragraphs[k]) for k in used)
    salutation = str(cl.get("salutation", ""))
    if "whom it may concern" in salutation.lower():
        problems.append("salutation 'To whom it may concern'; use a name or 'Dear Hiring Manager'")
    for k in used:
        text = str(paragraphs[k])
        if PLACEHOLDER.search(text):
            problems.append(f"{k}: unfilled placeholder '{PLACEHOLDER.search(text).group(0)}'")
        if CHATBOT.search(text):
            problems.append(f"{k}: chatbot phrasing '{CHATBOT.search(text).group(0)}'")
        if HIDDEN.search(text):
            problems.append(f"{k}: hidden or tiny text command")
        if "---" in text or "\u2014" in text:
            problems.append(f"{k}: em dash; rewrite with a comma or a full stop")
    if company and company.lower() not in body.lower():
        problems.append(f"the letter body never names '{company}'; check the company name")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=None)
    args = ap.parse_args()

    spec = yaml.safe_load(args.spec.read_text()) or {}
    cl = spec.get("cover_letter")
    if not cl:
        print(f"no cover_letter block in {args.spec}; skipping", file=sys.stderr)
        sys.exit(2)

    template = TEMPLATE.read_text()

    paragraphs = cl.get("paragraphs", {})
    required = ["hook", "technical_match", "values_fit", "close"]
    missing = [k for k in required if not paragraphs.get(k)]
    if missing:
        sys.exit(f"missing paragraphs: {missing}")
    # `forward` is optional: Robert Half AU recommends four paragraphs, Hays AU caps at five.
    used = [k for k in ("hook", "technical_match", "values_fit", "forward", "close") if paragraphs.get(k)]

    company = spec.get("company", "")
    cl_company = cl.get("company") or company
    problems = presend_problems(cl, paragraphs, used, cl_company)
    if problems:
        sys.exit("pre-send check failed:\n  - " + "\n  - ".join(problems))
    cl_for_recipient = {**cl, "company": cl_company}

    today = dt.date.today()
    letter_date = cl.get("date") or f"{today.day} {today:%B %Y}"

    out = (
        template
        .replace("{{COMPANY}}", _normalise(cl_company))
        .replace("{{LETTER_DATE}}", _normalise(letter_date))
        .replace("{{RECIPIENT_BLOCK}}", render_recipient(cl_for_recipient))
        .replace("{{SALUTATION}}", _normalise(cl.get("salutation", "Dear Hiring Manager")))
        .replace("{{PARAGRAPH_FORWARD}}\n\n", "{{PARAGRAPH_FORWARD}}\n\n" if paragraphs.get("forward") else "")
        .replace("{{PARAGRAPH_HOOK}}", _body(paragraphs["hook"]))
        .replace("{{PARAGRAPH_TECHNICAL}}", _body(paragraphs["technical_match"]))
        .replace("{{PARAGRAPH_VALUES}}", _body(paragraphs["values_fit"]))
        .replace("{{PARAGRAPH_FORWARD}}", _body(paragraphs.get("forward", "")))
        .replace("{{PARAGRAPH_CLOSE}}", _body(paragraphs["close"]))
    )

    slug = args.spec.parent.name
    out_path = args.output or (REPO / "outputs" / slug / "cover.tex")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out)
    print(f"wrote {out_path}")

    # Word count guard: ≤ 350 across paragraphs (one-page hard limit).
    total_words = sum(len(_normalise(paragraphs[k]).split()) for k in used)
    budgets = {"hook": (40, 80), "technical_match": (50, 85), "values_fit": (50, 85), "forward": (30, 70), "close": (15, 50)}
    for k in used:
        n = len(_normalise(paragraphs[k]).split())
        lo, hi = budgets[k]
        if not lo <= n <= hi:
            print(f"warn: {k} is {n} words; aim for {lo} to {hi}", file=sys.stderr)
    if total_words > 350:
        print(f"warn: cover letter is {total_words} words; trim to ≤ 350 for one page", file=sys.stderr)


if __name__ == "__main__":
    main()
