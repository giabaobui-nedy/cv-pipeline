#!/usr/bin/env python3
"""Check the bullet bank against bullet-bank/README.md.

Usage:
    python3 tools/lint_bank.py            # errors fail (exit 1), warnings print
    python3 tools/lint_bank.py --words    # also list every bullet's word count

Run it after every bank edit and before every tailor.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML not installed. Run: pip install -r requirements.txt")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_tailored import BANK, NON_ROLE_FILES, plain_text  # noqa: E402

OWNERSHIP = {"led", "owned", "co-built", "contributed"}
ENVS = {"dev", "staging", "prod"}
AI_FRAMING = {"user", "builder"}
STRONG_VERBS = ("led", "architected", "spearheaded", "initiated", "owned")
BANNED = [
    "leverage", "leveraged", "leveraging", "utilise", "utilize", "spearhead", "robust",
    "comprehensive", "seamless", "synergy", "passionate", "cutting-edge", "world-class",
    "transforming", "holistic", "ecosystem", "delve",
]
LONG_WORDS = 45
MAX_TAGS = 8
YM = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", action="store_true")
    args = ap.parse_args()

    errors: list[str] = []
    warns: list[str] = []
    vocab = yaml.safe_load((BANK / "tags.yml").read_text())
    known_tags = set(vocab["tags"])

    bullets: list[tuple[str, dict]] = []
    for path in sorted(BANK.glob("*.yml")):
        if path.name == "tags.yml":
            continue
        data = yaml.safe_load(path.read_text()) or {}
        if path.name not in NON_ROLE_FILES:
            role = data.get("role") or {}
            for k in ("title", "employer", "dates", "location", "start"):
                if not role.get(k):
                    errors.append(f"{path.name}: role block has no '{k}'")
            for k in ("start", "end"):
                if role.get(k) and not YM.match(str(role[k])):
                    errors.append(f"{path.name}: role.{k} must be YYYY-MM or YYYY-MM-DD")
            bullets += [(path.name, b) for b in data.get("bullets") or []]
        else:
            for proj in data.get("projects", []):
                for t in proj.get("tags", []):
                    if t not in known_tags:
                        warns.append(f"{path.name}:{proj['id']}: tag '{t}' is not in tags.yml")
                bullets += [(path.name, b) for b in proj.get("bullets", [])]

    ids = Counter(b.get("id") for _, b in bullets)
    errors += [f"duplicate id {i} ({n} times)" for i, n in ids.items() if n > 1]
    groups: dict[str, list[str]] = defaultdict(list)
    word_rows = []

    for fname, b in bullets:
        bid = b.get("id", "<no id>")
        where = f"{fname}:{bid}"
        for k in ("id", "tags", "text"):
            if not b.get(k):
                errors.append(f"{where}: missing '{k}'")
        text = b.get("text", "")
        plain = plain_text(text)
        words = len(plain.split())
        tags = b.get("tags", [])
        is_stack = "stack" in tags
        word_rows.append((words, where))

        if "---" in text or "—" in text:
            errors.append(f"{where}: em dash in text")
        if b.get("status") not in (None, "outdated"):
            errors.append(f"{where}: unknown status '{b['status']}'")
        if b.get("status") == "outdated" and not b.get("note"):
            errors.append(f"{where}: outdated bullets need a note naming the replacement")

        own = b.get("ownership")
        if own is not None and own not in OWNERSHIP:
            errors.append(f"{where}: ownership must be one of {sorted(OWNERSHIP)}")
        first = plain.split()[0].lower() if plain else ""
        if own in ("co-built", "contributed") and first in STRONG_VERBS:
            errors.append(f"{where}: opens with '{first}' but ownership is {own}")
        bad_env = set(b.get("env", [])) - ENVS
        if bad_env:
            errors.append(f"{where}: unknown env {sorted(bad_env)}")
        if b.get("ai_framing") not in (None, *AI_FRAMING):
            errors.append(f"{where}: ai_framing must be user or builder")

        if "impact-metric" in tags:
            source = (b.get("metric") or {}).get("source")
            if not source:
                errors.append(f"{where}: impact-metric bullet has no metric.source")
            elif str(source).startswith("unverified"):
                warns.append(f"{where}: metric not verified ({source})")

        unknown = [t for t in tags if t not in known_tags]
        if unknown:
            warns.append(f"{where}: tags not in tags.yml: {unknown}")
        if len(tags) > MAX_TAGS and not is_stack:
            warns.append(f"{where}: {len(tags)} tags (max {MAX_TAGS})")
        lowered = plain.lower()
        hits = [w for w in BANNED if re.search(rf"\b{re.escape(w)}\b", lowered)]
        if hits:
            warns.append(f"{where}: banned or AI-sounding words {hits}")
        if b.get("variant_group"):
            groups[b["variant_group"]].append(bid)
        elif words > LONG_WORDS and not is_stack and b.get("status") != "outdated":
            warns.append(f"{where}: {words} words and no compact twin (variant_group)")

    warns += [f"variant_group '{g}' has only {m}" for g, m in groups.items() if len(m) < 2]

    for w in warns:
        print(f"warn: {w}")
    for e in errors:
        print(f"error: {e}")
    if args.words:
        for words, where in sorted(word_rows, reverse=True):
            print(f"{words:4d}  {where}")
    print(f"{len(bullets)} bullets, {len(errors)} errors, {len(warns)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
