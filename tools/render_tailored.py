#!/usr/bin/env python3
"""Render a tailored CV from a job-ad spec + the bullet bank.

Usage:
    python tools/render_tailored.py job-ads/<company>.yml [-o outputs/<company>.tex]

The spec is a small YAML file (see job-ads/_example.yml) that lists which
bullet IDs to include per role and which projects to include. The renderer
fills `cv/tailored.tex.template` and writes a ready-to-compile .tex file.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML not installed. Run: pip install -r requirements.txt")

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = REPO / "cv" / "tailored.tex.template"
BANK = REPO / "bullet-bank"


def load_role_bank(path: Path) -> dict[str, dict]:
    data = yaml.safe_load(path.read_text()) or {}
    return {b["id"]: b for b in data.get("bullets", [])}


def load_projects_bank(path: Path) -> dict[str, dict]:
    data = yaml.safe_load(path.read_text()) or {}
    return {p["id"]: p for p in data.get("projects", [])}


def load_banks() -> tuple[dict[str, dict[str, dict]], dict[str, dict]]:
    role_banks = {
        "soniq": load_role_bank(BANK / "soniq.yml"),
        "csiro": load_role_bank(BANK / "csiro.yml"),
    }
    projects = load_projects_bank(BANK / "projects.yml")
    return role_banks, projects


def _normalise(text: str) -> str:
    return " ".join(text.split())


def render_role(role_meta: dict, bullet_ids: list[str], bank: dict[str, dict]) -> str:
    items = []
    for bid in bullet_ids:
        if bid not in bank:
            print(f"warn: missing bullet id {bid}", file=sys.stderr)
            continue
        items.append(f"            \\resumeItem{{{_normalise(bank[bid]['text'])}}}")
    items_block = "\n".join(items)
    return (
        f"      \\resumeSubheading\n"
        f"          {{{role_meta['title']}}}{{{role_meta['dates']}}}\n"
        f"          {{{role_meta['employer']}}}{{{role_meta['location']}}}\n"
        f"            \\resumeItemListStart\n"
        f"{items_block}\n"
        f"            \\resumeItemListEnd"
    )


def render_project(project_id: str, bullet_ids: list[str], projects: dict[str, dict]) -> str:
    proj = projects.get(project_id)
    if not proj:
        print(f"warn: missing project {project_id}", file=sys.stderr)
        return ""
    links = " $|$ ".join(
        f"\\href{{{l['url']}}}{{{l['label']}}}" for l in proj.get("links", [])
    )
    bullet_map = {b["id"]: b for b in proj.get("bullets", [])}
    items = []
    for bid in bullet_ids:
        if bid not in bullet_map:
            print(f"warn: missing project bullet {bid} (in {project_id})", file=sys.stderr)
            continue
        items.append(f"                \\resumeItem{{{_normalise(bullet_map[bid]['text'])}}}")
    return (
        f"        \\resumeProjectHeading\n"
        f"            {{{proj['title']} $|$ \\emph{{{proj['stack']}}}}}{{{links}}}\n"
        f"            \\resumeItemListStart\n"
        f"{chr(10).join(items)}\n"
        f"            \\resumeItemListEnd"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=None)
    args = ap.parse_args()

    spec = yaml.safe_load(args.spec.read_text()) or {}
    role_banks, projects = load_banks()
    template = TEMPLATE.read_text()

    experience_blocks = []
    for role in spec.get("experience", []):
        bank = role_banks.get(role["bank"])
        if bank is None:
            sys.exit(f"unknown bank '{role['bank']}' (known: {list(role_banks)})")
        experience_blocks.append(render_role(role, role.get("bullets", []), bank))

    project_blocks = []
    for proj in spec.get("projects", []):
        block = render_project(proj["id"], proj.get("bullets", []), projects)
        if block:
            project_blocks.append(block)

    out = (
        template
        .replace("{{PROFILE}}", spec.get("profile", "").strip())
        .replace("{{EXPERIENCE_BLOCKS}}", "\n".join(experience_blocks))
        .replace("{{PROJECT_BLOCKS}}", "\n".join(project_blocks))
        .replace("{{SKILLS}}", spec.get("skills", "").strip())
    )

    out_path = args.output or (REPO / "outputs" / f"{args.spec.stem}.tex")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
