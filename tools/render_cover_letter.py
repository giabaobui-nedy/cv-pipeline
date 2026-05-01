#!/usr/bin/env python3
"""Render a cover letter from a job-ad spec.

Usage:
    python tools/render_cover_letter.py job-ads/<company>.yml [-o outputs/<company>.cover.tex]

Reads the `cover_letter` block of the spec and fills `cv/cover-letter.tex.template`.
If the spec has no `cover_letter` block, exits with code 2 (skipped, not an error).
"""
from __future__ import annotations

import argparse
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


def render_recipient(cl: dict) -> str:
    """Build the LaTeX recipient block. All fields optional; render what we have."""
    lines: list[str] = []
    name = cl.get("recipient_name")
    company = cl.get("company") or cl.get("recipient_company")
    if name and company:
        lines.append(f"\\textbf{{{name} --- {company}}}")
    elif name:
        lines.append(f"\\textbf{{{name}}}")
    elif company:
        lines.append(f"\\textbf{{{company}}}")
    address = cl.get("recipient_address")
    if address:
        for line in str(address).strip().splitlines():
            line = line.strip()
            if line:
                lines.append(line)
    return " \\\\\n".join(lines)


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
    required = ["hook", "technical_match", "values_fit", "forward", "close"]
    missing = [k for k in required if not paragraphs.get(k)]
    if missing:
        sys.exit(f"missing paragraphs: {missing}")

    company = spec.get("company", "")
    cl_company = cl.get("company") or company
    cl_for_recipient = {**cl, "company": cl_company}

    letter_date = cl.get("date") or dt.date.today().strftime("%d %B %Y")

    out = (
        template
        .replace("{{COMPANY}}", _normalise(cl_company))
        .replace("{{LETTER_DATE}}", _normalise(letter_date))
        .replace("{{RECIPIENT_BLOCK}}", render_recipient(cl_for_recipient))
        .replace("{{SALUTATION}}", _normalise(cl.get("salutation", "Dear Hiring Team")))
        .replace("{{PARAGRAPH_HOOK}}", _normalise(paragraphs["hook"]))
        .replace("{{PARAGRAPH_TECHNICAL}}", _normalise(paragraphs["technical_match"]))
        .replace("{{PARAGRAPH_VALUES}}", _normalise(paragraphs["values_fit"]))
        .replace("{{PARAGRAPH_FORWARD}}", _normalise(paragraphs["forward"]))
        .replace("{{PARAGRAPH_CLOSE}}", _normalise(paragraphs["close"]))
    )

    out_path = args.output or (REPO / "outputs" / f"{args.spec.stem}.cover.tex")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out)
    print(f"wrote {out_path}")

    # Word count guard: ≤ 350 across paragraphs (one-page hard limit).
    total_words = sum(len(_normalise(paragraphs[k]).split()) for k in required)
    if total_words > 350:
        print(f"warn: cover letter is {total_words} words; trim to ≤ 350 for one page", file=sys.stderr)


if __name__ == "__main__":
    main()
