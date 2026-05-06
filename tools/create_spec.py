#!/usr/bin/env python3
"""Create a draft job-ad spec without an AI agent.

This is intentionally heuristic: it matches the saved job ad against bullet-bank
tags, prefers quantified/stack bullets, and writes a compile-ready spec that a
human can edit. It does not invent new achievements or rewrite bank bullets.

Usage:
    .venv/bin/python tools/create_spec.py --company "Example Co" --role "Software Engineer" --ad job-ads/example/ad.txt
    .venv/bin/python tools/create_spec.py --slug example --company "Example Co" --role "Software Engineer" --write
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.exit("PyYAML not installed. Run: .venv/bin/pip install -r requirements.txt")

REPO = Path(__file__).resolve().parent.parent
BANK = REPO / "bullet-bank"

ROLE_META = {
    "soniq": {
        "title": "Junior Software Engineer",
        "dates": "Feb 2026 -- Present",
        "employer": "SONIQ Digital",
        "location": "Richmond, VIC",
        "mandatory": "soniq-stack",
        "limit": 4,
        "avoid_by_default": {"soniq-overview"},
    },
    "csiro": {
        "title": "Software Engineering Intern / Casual Software Engineer",
        "dates": "Mar 2024 -- Jun 2025",
        "employer": "CSIRO",
        "location": "Clayton, VIC",
        "mandatory": "csiro-stack",
        "limit": 3,
        "avoid_by_default": {"csiro-overview"},
    },
}

DEFAULT_SKILLS = r"""\textbf{Languages:} TypeScript, JavaScript, Python, Java \\
\textbf{Backend}{: Python (Flask/FastAPI), Node.js, system integration, threading and concurrency, AWS} \\
\textbf{Frontend}{: React, Vue.js/Nuxt, component-based UI development} \\
\textbf{Databases}{: PostgreSQL, MySQL, InfluxDB, relational schema design} \\
\textbf{DevOps \& Tools}{: AWS CDK, Terraform, Docker, Linux, Git/GitHub, CI/CD, GitHub Actions} \\
\textbf{AI-Assisted Development:} Experience using LLM-based coding assistants for debugging, code exploration, and documentation."""

EDUCATION_HIGHEST_ACHIEVING = (
    r"Recognised as \textbf{Highest Achieving Graduate} in the Bachelor of "
    r"Computer Science (Professional) cohort."
)


class LiteralDumper(yaml.SafeDumper):
    pass


def _represent_str(dumper: yaml.Dumper, value: str) -> yaml.nodes.ScalarNode:
    if "\n" in value:
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", value)


LiteralDumper.add_representer(str, _represent_str)


@dataclass(frozen=True)
class ScoredBullet:
    bullet_id: str
    score: int
    tags: list[str]


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "application"


def tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9][a-z0-9.+#-]*", text.lower()) if len(t) > 1}


def load_role_bank(name: str) -> list[dict[str, Any]]:
    data = yaml.safe_load((BANK / f"{name}.yml").read_text()) or {}
    return data.get("bullets", []) or []


def load_projects() -> list[dict[str, Any]]:
    data = yaml.safe_load((BANK / "projects.yml").read_text()) or {}
    return data.get("projects", []) or []


def all_bank_tags() -> set[str]:
    found: set[str] = set()
    for bank_name in ROLE_META:
        for bullet in load_role_bank(bank_name):
            found.update(str(t).lower() for t in bullet.get("tags", []) or [])
    for project in load_projects():
        found.update(str(t).lower() for t in project.get("tags", []) or [])
        for bullet in project.get("bullets", []) or []:
            found.update(str(t).lower() for t in bullet.get("tags", []) or [])
    return found


def extract_keywords(ad_text: str, limit: int = 15) -> list[str]:
    ad_tokens = tokens(ad_text)
    matched = sorted(tag for tag in all_bank_tags() if tag in ad_tokens)
    preferred = [
        "aws", "typescript", "react", "python", "fastapi", "vue", "node",
        "microservices", "event-driven", "serverless", "docker", "ci-cd",
        "terraform", "sql", "postgresql", "security", "reliability",
        "frontend", "backend", "fullstack", "testing", "api",
    ]
    ordered = [k for k in preferred if k in matched]
    ordered.extend(k for k in matched if k not in ordered)
    return ordered[:limit]


def score_bullet(bullet: dict[str, Any], keywords: set[str], ad_tokens: set[str]) -> ScoredBullet:
    tags = [str(t).lower() for t in bullet.get("tags", []) or []]
    tag_hits = sum(1 for tag in tags if tag in keywords or tag in ad_tokens)
    text_hits = sum(1 for token in tokens(str(bullet.get("text", ""))) if token in ad_tokens)
    score = tag_hits * 10 + min(text_hits, 8)
    if "impact-metric" in tags:
        score += 8
    if "stack" in tags:
        score += 4
    if "overview" in tags:
        score -= 6
    return ScoredBullet(str(bullet["id"]), score, tags)


def choose_role_bullets(bank_name: str, keywords: set[str], ad_tokens: set[str]) -> list[str]:
    meta = ROLE_META[bank_name]
    mandatory = meta["mandatory"]
    scored = [
        score_bullet(b, keywords, ad_tokens)
        for b in load_role_bank(bank_name)
        if b.get("id") != mandatory and b.get("id") not in meta["avoid_by_default"]
    ]
    picked = [
        b.bullet_id
        for b in sorted(scored, key=lambda b: (-b.score, b.bullet_id))
        if b.score > 0
    ][: meta["limit"]]
    if mandatory not in picked:
        picked.append(mandatory)
    return picked


def choose_projects(keywords: set[str], ad_tokens: set[str], limit: int = 2) -> list[dict[str, Any]]:
    candidates: list[tuple[int, str, list[str]]] = []
    for project in load_projects():
        project_tags = {str(t).lower() for t in project.get("tags", []) or []}
        project_score = 8 * len(project_tags & (keywords | ad_tokens))
        bullet_scores = [
            score_bullet(b, keywords, ad_tokens)
            for b in project.get("bullets", []) or []
        ]
        picked_bullets = [
            b.bullet_id
            for b in sorted(bullet_scores, key=lambda b: (-b.score, b.bullet_id))
            if b.score > 0
        ][:2]
        if picked_bullets:
            candidates.append((project_score + max(b.score for b in bullet_scores), str(project["id"]), picked_bullets))
    return [
        {"id": project_id, "bullets": bullet_ids}
        for _, project_id, bullet_ids in sorted(candidates, key=lambda p: (-p[0], p[1]))[:limit]
    ]


def build_profile(role: str, keywords: list[str]) -> str:
    tech = ", ".join(keywords[:4]) if keywords else "production software engineering"
    return (
        "Software Engineer and Highest Achieving Graduate in Computer Science with "
        "professional experience building production-grade systems. Brings hands-on "
        f"experience across {tech}, with a focus on maintainable, user-facing engineering."
    )


def build_spec(args: argparse.Namespace) -> dict[str, Any]:
    ad_text = args.ad.read_text() if args.ad else ""
    keywords = extract_keywords(ad_text)
    keyword_set = set(keywords)
    ad_token_set = tokens(ad_text)

    return {
        "schema_version": 1,
        "pipeline_version": "0.1.0",
        "evidence_snapshot": args.date,
        "created_by_model": "create_spec.py",
        "reviewed_by": "",
        "review_status": "draft",
        "company": args.company,
        "role": args.role,
        "source_url": args.source_url or "n/a",
        "date_saved": args.date,
        "ad_raw": ad_text or "Paste the original ad here.",
        "keywords": keywords,
        "section_order": ["profile", "experience", "projects", "skills", "education"],
        "education_bullets": [EDUCATION_HIGHEST_ACHIEVING],
        "profile": build_profile(args.role, keywords),
        "experience": [
            {**{k: v for k, v in ROLE_META[bank].items() if k in {"title", "dates", "employer", "location"}}, "bank": bank, "bullets": choose_role_bullets(bank, keyword_set, ad_token_set)}
            for bank in ("soniq", "csiro")
        ],
        "projects": choose_projects(keyword_set, ad_token_set),
        "skills": DEFAULT_SKILLS,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slug", help="job-ads/<slug>; defaults to slugified company")
    ap.add_argument("--company", required=True)
    ap.add_argument("--role", required=True)
    ap.add_argument("--source-url", default="")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--ad", type=Path, help="path to a saved job ad text file")
    ap.add_argument("--write", action="store_true", help="write job-ads/<slug>/spec.yml; default prints YAML")
    ap.add_argument("--force", action="store_true", help="overwrite an existing spec.yml")
    args = ap.parse_args()

    if args.ad and not args.ad.exists():
        sys.exit(f"ad file not found: {args.ad}")

    slug = args.slug or slugify(args.company)
    spec = build_spec(args)
    rendered = yaml.dump(
        spec,
        Dumper=LiteralDumper,
        sort_keys=False,
        allow_unicode=True,
        width=88,
    )

    if not args.write:
        print(rendered)
        return

    out = REPO / "job-ads" / slug / "spec.yml"
    if out.exists() and not args.force:
        sys.exit(f"refusing to overwrite existing spec: {out} (pass --force to replace)")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered)
    print(f"wrote {out}")
    print(f"next: tools/compile.sh {slug}")


if __name__ == "__main__":
    main()
