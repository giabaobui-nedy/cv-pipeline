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

try:
    import yaml
except ImportError:
    sys.exit("PyYAML not installed. Run: pip install -r requirements.txt")

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = REPO / "cv" / "cover-letter.tex.template"


def _normalise(text: str) -> str:
    return " ".join((text or "").split())


def _body(text: str) -> str:
    """Paragraph text: escape bare %, & and # so "40%" can't comment out the rest of a line."""
    return re.sub(r"(?<!\\)([%&#])", r"\\\1", _normalise(text))


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
        .replace("{{SALUTATION}}", _normalise(cl.get("salutation", "Dear Hiring Team")))
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
    if total_words > 350:
        print(f"warn: cover letter is {total_words} words; trim to ≤ 350 for one page", file=sys.stderr)


if __name__ == "__main__":
    main()
