"""
seek_variants.py — SEEK URL builder and keyword expansion for multi-search.

SEEK search URLs follow a strict pattern:
    https://au.seek.com/{Keyword-Slug}-jobs/in-{Location-Slug}

This module provides:
    build_seek_url(keyword, location)  → URL string
    expand_keywords(base_keyword)      → list of related keyword slugs
    LOCATIONS                          → common Australian location slugs
    KEYWORD_GROUPS                     → predefined expansion groups by role theme

Usage
-----
    from job_fetcher.seek_variants import build_seek_url, expand_keywords, LOCATIONS

    urls = [
        build_seek_url(kw, "All-Melbourne-VIC")
        for kw in expand_keywords("junior software engineer")
    ]
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# URL construction
# ---------------------------------------------------------------------------

_SEEK_BASE = "https://au.seek.com"


def slugify(text: str) -> str:
    """Convert a keyword phrase to a SEEK-style Title-Case-Hyphenated slug.

    All-uppercase words (abbreviations like VIC, NSW, ACT, AWS) are preserved
    as-is; all other words are title-cased.

    Examples
    --------
    "junior software engineer"  → "Junior-Software-Engineer"
    "AWS DevOps"                → "AWS-DevOps"
    "full-stack developer"      → "Full-Stack-Developer"
    "All Melbourne VIC"         → "All-Melbourne-VIC"
    """
    words = re.split(r"[\s\-]+", text.strip())
    result = []
    for w in words:
        if not w:
            continue
        # Preserve all-caps abbreviations (e.g. VIC, NSW, ACT, AWS, CBD).
        result.append(w if w.isupper() and len(w) >= 2 else w.capitalize())
    return "-".join(result)


def build_seek_url(keyword: str, location: str) -> str:
    """Build a SEEK search URL from a keyword phrase and a location phrase.

    Parameters
    ----------
    keyword  : e.g. "junior software engineer"  or  "Junior-Software-Engineer"
    location : e.g. "All Melbourne VIC"         or  "All-Melbourne-VIC"

    Returns
    -------
    "https://au.seek.com/Junior-Software-Engineer-jobs/in-All-Melbourne-VIC"
    """
    kw_slug  = slugify(keyword)
    loc_slug = slugify(location)
    return f"{_SEEK_BASE}/{kw_slug}-jobs/in-{loc_slug}"


# ---------------------------------------------------------------------------
# Common locations
# ---------------------------------------------------------------------------

LOCATIONS: dict[str, str] = {
    # key          → SEEK location slug
    "melbourne":          "All-Melbourne-VIC",
    "melbourne-cbd":      "Melbourne-CBD-Melbourne-VIC-3000",
    "sydney":             "All-Sydney-NSW",
    "brisbane":           "All-Brisbane-QLD",
    "perth":              "All-Perth-WA",
    "adelaide":           "All-Adelaide-SA",
    "canberra":           "All-Canberra-ACT",
    "remote":             "Australia",
    "australia":          "Australia",
}

DEFAULT_LOCATION = LOCATIONS["melbourne"]


# ---------------------------------------------------------------------------
# Keyword expansion groups
# ---------------------------------------------------------------------------
# Each group is a list of keyword phrases that SEEK understands as distinct
# search slugs.  Variants are designed to cover synonyms SEEK treats
# differently — fetching them all and deduplicating gives broader coverage
# than a single search.

KEYWORD_GROUPS: dict[str, list[str]] = {

    "junior-swe": [
        "Junior Software Engineer",
        "Junior Software Developer",
        "Junior Developer",
        "Junior Programmer",
    ],

    "graduate-swe": [
        "Graduate Software Engineer",
        "Graduate Software Developer",
        "Graduate Developer",
        "Graduate Full Stack Developer",
    ],

    "associate-swe": [
        "Associate Software Engineer",
        "Associate Developer",
    ],

    "junior-fullstack": [
        "Junior Full Stack Developer",
        "Junior Full Stack Engineer",
        "Junior Fullstack Developer",
    ],

    "junior-frontend": [
        "Junior Frontend Developer",
        "Junior Front End Developer",
        "Junior React Developer",
        "Junior TypeScript Developer",
        "Junior JavaScript Developer",
    ],

    "junior-backend": [
        "Junior Backend Developer",
        "Junior Back End Developer",
        "Junior Python Developer",
        "Junior Node Developer",
    ],

    "junior-cloud": [
        "Junior Cloud Engineer",
        "Junior DevOps Engineer",
        "Junior Platform Engineer",
    ],
}

# Convenience: all keywords flattened, no duplicates, ordered.
ALL_KEYWORDS: list[str] = list(
    dict.fromkeys(kw for group in KEYWORD_GROUPS.values() for kw in group)
)


# ---------------------------------------------------------------------------
# Keyword expansion
# ---------------------------------------------------------------------------

# Map from a normalised input phrase to the group(s) it expands to.
_EXPANSION_MAP: dict[str, list[str]] = {
    # junior-level generics
    "junior software engineer":   ["junior-swe", "graduate-swe", "associate-swe"],
    "junior software developer":  ["junior-swe", "graduate-swe"],
    "junior developer":           ["junior-swe", "graduate-swe", "associate-swe"],
    "junior swe":                 ["junior-swe", "graduate-swe", "associate-swe"],

    # graduate
    "graduate software engineer": ["graduate-swe", "junior-swe"],
    "graduate developer":         ["graduate-swe", "junior-swe"],
    "grad":                       ["graduate-swe", "junior-swe"],
    "graduate":                   ["graduate-swe", "junior-swe"],

    # full-stack
    "full stack":                 ["junior-fullstack", "junior-swe", "graduate-swe"],
    "fullstack":                  ["junior-fullstack", "junior-swe", "graduate-swe"],
    "full-stack":                 ["junior-fullstack", "junior-swe", "graduate-swe"],

    # frontend
    "frontend":                   ["junior-frontend", "junior-fullstack"],
    "front end":                  ["junior-frontend", "junior-fullstack"],
    "react":                      ["junior-frontend"],
    "typescript":                 ["junior-frontend", "junior-fullstack"],

    # backend
    "backend":                    ["junior-backend", "junior-swe"],
    "python":                     ["junior-backend", "junior-swe"],

    # cloud / devops
    "cloud":                      ["junior-cloud"],
    "devops":                     ["junior-cloud"],

    # catch-all
    "all":                        list(KEYWORD_GROUPS.keys()),
}


def expand_keywords(base: str) -> list[str]:
    """Return a deduplicated list of keyword phrases to search for.

    Parameters
    ----------
    base : A free-text hint like "junior software engineer", "fullstack",
           "python", or "all".

    Returns
    -------
    List of keyword strings (e.g. "Junior Software Engineer") ready to pass
    to ``build_seek_url``.
    """
    key = base.strip().lower()
    group_names = _EXPANSION_MAP.get(key)

    if group_names is None:
        # No expansion found — treat the input itself as a single keyword.
        return [base.strip()]

    # Collect keywords from all matching groups, preserving order, no dupes.
    seen: set[str] = set()
    result: list[str] = []
    for group_name in group_names:
        for kw in KEYWORD_GROUPS.get(group_name, []):
            if kw not in seen:
                seen.add(kw)
                result.append(kw)
    return result


def build_variant_urls(base_keyword: str, location: str = DEFAULT_LOCATION) -> list[str]:
    """Expand *base_keyword* and build one SEEK URL per variant.

    Parameters
    ----------
    base_keyword : Free-text hint (see ``expand_keywords``).
    location     : Location slug or plain name (looked up in ``LOCATIONS``).

    Returns
    -------
    List of SEEK search URLs, one per keyword variant.
    """
    # Resolve location alias.
    loc_slug = LOCATIONS.get(location.lower().replace(" ", "-"), location)
    keywords = expand_keywords(base_keyword)
    return [build_seek_url(kw, loc_slug) for kw in keywords]


def list_groups() -> str:
    """Return a human-readable summary of all keyword groups."""
    lines = []
    for name, keywords in KEYWORD_GROUPS.items():
        lines.append(f"  {name}:")
        for kw in keywords:
            lines.append(f"    • {kw}")
    return "\n".join(lines)
