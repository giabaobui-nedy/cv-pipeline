#!/usr/bin/env python3
"""Print a Notion-paste-ready row for a tailored application.

Usage:
    python tools/track.py <slug>
    python tools/track.py job-ads/<slug>/spec.yml

Prints a fields view (one label/value pair per line, easy to read and to copy
individual fields), followed by a TSV row that pastes cleanly into a Notion
database when the columns are arranged in the same order.

Designed for Approach A in the Notion integration plan — manual paste, no MCP
required. When you eventually upgrade to Notion MCP write-back, the schema
emitted here is the same one the MCP push will use.

Fields:
    Company             — from spec.company
    Position            — from spec.role
    Status              — defaults to "Applied"
    Application Date    — from spec.date_saved, or today
    Source URL          — from spec.source_url
    Slug                — repo cross-reference (the job-ads/<slug>/ folder)
    CV pages            — page count of outputs/<slug>/cv.pdf (— if missing)
    Cover pages         — page count of outputs/<slug>/cover.pdf (— if missing)
    CV bullets          — comma-separated bullet ids selected for the CV
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML not installed. Run: .venv/bin/pip install -r requirements.txt")

REPO = Path(__file__).resolve().parent.parent


def _page_count(pdf_path: Path) -> str:
    if not pdf_path.exists():
        return "—"
    try:
        from pypdf import PdfReader
        return str(len(PdfReader(str(pdf_path)).pages))
    except Exception:
        return "?"


def _resolve_spec(target: str) -> Path:
    if target.endswith(".yml"):
        return Path(target)
    direct = REPO / "job-ads" / target / "spec.yml"
    if direct.exists():
        return direct
    sys.exit(f"spec not found: tried {direct}")


def _bullets_used(spec: dict) -> str:
    ids: list[str] = []
    for role in spec.get("experience", []) or []:
        ids.extend(role.get("bullets", []) or [])
    for proj in spec.get("projects", []) or []:
        ids.extend(proj.get("bullets", []) or [])
    return ", ".join(ids) if ids else "—"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", help="slug or path to spec.yml")
    args = ap.parse_args()

    spec_path = _resolve_spec(args.target)
    spec = yaml.safe_load(spec_path.read_text()) or {}
    slug = spec_path.parent.name

    fields: list[tuple[str, str]] = [
        ("Company",          str(spec.get("company", "—"))),
        ("Position",         str(spec.get("role", "—"))),
        ("Status",           "Applied"),
        ("Application Date", str(spec.get("date_saved") or dt.date.today().isoformat())),
        ("Source URL",       str(spec.get("source_url", "—"))),
        ("Slug",             slug),
        ("CV pages",         _page_count(REPO / "outputs" / slug / "cv.pdf")),
        ("Cover pages",      _page_count(REPO / "outputs" / slug / "cover.pdf")),
        ("CV bullets",       _bullets_used(spec)),
    ]

    label_width = max(len(label) for label, _ in fields)

    print("=== Notion row — fields view ===")
    for label, value in fields:
        print(f"{label.ljust(label_width)}  {value}")

    print()
    print("=== Notion row — TSV (paste into a database with these columns) ===")
    print("\t".join(label for label, _ in fields))
    print("\t".join(value for _, value in fields))

    print()
    print("Tip: arrange your Notion DB columns in the order above, then paste")
    print("the second line as a new row. Notion matches by column position.")


if __name__ == "__main__":
    main()
