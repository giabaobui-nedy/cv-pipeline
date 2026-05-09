"""
filters.py — post-fetch filtering for JobStub lists.

Lets you narrow a raw search results list down to roles that actually match
your profile before spending time fetching full descriptions.

Usage
-----
    from job_fetcher.filters import JobFilter, filter_stubs, classify_level

    f = JobFilter(
        levels={"junior", "graduate", "associate"},
        stack={"typescript", "python", "react"},
        min_salary=70_000,
        arrangements={"hybrid", "remote"},
        visa_friendly=True,
    )
    matched = filter_stubs(stubs, f)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from .models import JobStub

# ---------------------------------------------------------------------------
# Experience-level classification
# ---------------------------------------------------------------------------

# Map of level name → patterns that indicate that level in a job title/preview.
# More specific patterns are listed first; the first match wins.
_LEVEL_PATTERNS: dict[str, list[str]] = {
    "intern": [
        r"\bintern(ship)?\b",
        r"\bwork[- ]integrated[- ]learning\b",
        r"\bwil\b",
        r"\bco[- ]?op\b",
        r"\bplacement\b",
    ],
    "graduate": [
        r"\bgrad(uate)?\b",
        r"\bearly[- ]career\b",
        r"\bentry[- ]level\b",
        r"\bentry[- ]level\b",
        r"\b(new|recent)\s+(grad|graduate)\b",
    ],
    "junior": [
        r"\bjunior\b",
        r"\bjr\.?\b",
        r"\bassociate\b",
        r"\bstarting[- ]your\b",
        r"\bstart[- ]your[- ]career\b",
        r"\bfractional\b",         # fractional roles skew junior/part-time
    ],
    "mid": [
        r"\bmid[- ]?level\b",
        r"\bintermediate\b",
        r"\b[2-4]\+?\s+years?\b",  # "2+ years experience"
    ],
    "senior": [
        r"\bsenior\b",
        r"\bsr\.?\b",
        r"\blead\b",
        r"\bprincipal\b",
        r"\bstaff\b",
        r"\bhead\s+of\b",
        r"\barchitect\b",
        r"\b[5-9]\+?\s+years?\b",  # "5+ years"
        r"\b1[0-9]\+?\s+years?\b",
    ],
}

Level = Literal["intern", "graduate", "junior", "mid", "senior", "unknown"]

_COMPILED: dict[str, list[re.Pattern]] = {
    level: [re.compile(p, re.IGNORECASE) for p in patterns]
    for level, patterns in _LEVEL_PATTERNS.items()
}

# Check seniority signals FIRST so "Senior Associate" → senior, not junior.
# Within the junior cluster, intern/graduate/junior are fine in any order
# since their patterns don't overlap with each other.
_LEVEL_ORDER = ["senior", "mid", "intern", "graduate", "junior"]


def classify_level(stub: JobStub) -> Level:
    """Detect the experience level from a job stub's title and preview text.

    Returns one of: ``"intern"``, ``"graduate"``, ``"junior"``, ``"mid"``,
    ``"senior"``, ``"unknown"``.
    """
    text = " ".join(filter(None, [stub.title, stub.description_preview]))
    for level in _LEVEL_ORDER:
        for pat in _COMPILED[level]:
            if pat.search(text):
                return level  # type: ignore[return-value]
    return "unknown"


# ---------------------------------------------------------------------------
# Tech-stack keyword detection
# ---------------------------------------------------------------------------

def _stack_tokens(text: str) -> set[str]:
    """Lowercase word-tokens from a stub's title + preview."""
    return set(re.findall(r"[a-z][a-z0-9.#+\-]*", text.lower()))


def stub_matches_stack(stub: JobStub, required: set[str]) -> bool:
    """Return True if at least one token in *required* appears in the stub."""
    if not required:
        return True
    text = " ".join(filter(None, [stub.title, stub.description_preview, stub.company]))
    tokens = _stack_tokens(text)
    return bool(required & tokens)


# ---------------------------------------------------------------------------
# Salary parsing
# ---------------------------------------------------------------------------

def _parse_salary_min(salary_str: str | None) -> float | None:
    """Extract the lower-bound salary as a float from a human salary string.

    Handles: "$70,000", "$70K", "$70,000 – $90,000 per year", "AUD 70000"
    """
    if not salary_str:
        return None
    # Grab all numeric chunks (with optional K suffix).
    matches = re.findall(r"\$?([\d,]+)\s*([kK]?)", salary_str)
    values: list[float] = []
    for digits, suffix in matches:
        try:
            val = float(digits.replace(",", ""))
            if suffix.lower() == "k":
                val *= 1000
            values.append(val)
        except ValueError:
            continue
    return min(values) if values else None


# ---------------------------------------------------------------------------
# Work-arrangement detection
# ---------------------------------------------------------------------------

_ARRANGEMENT_PATTERNS: dict[str, list[str]] = {
    "remote":  [r"\bremote\b", r"\bwork[- ]from[- ]home\b", r"\bwfh\b"],
    "hybrid":  [r"\bhybrid\b"],
    "on-site": [r"\bon[- ]site\b", r"\bonsite\b", r"\bin[- ]office\b"],
}
_ARRANGEMENT_RE: dict[str, list[re.Pattern]] = {
    arr: [re.compile(p, re.IGNORECASE) for p in pats]
    for arr, pats in _ARRANGEMENT_PATTERNS.items()
}


def detect_arrangement(stub: JobStub) -> set[str]:
    """Return a set of detected work arrangements for a stub."""
    text = " ".join(filter(None, [stub.title, stub.description_preview, stub.location]))
    found: set[str] = set()
    for arr, pats in _ARRANGEMENT_RE.items():
        if any(p.search(text) for p in pats):
            found.add(arr)
    return found


# ---------------------------------------------------------------------------
# JobFilter dataclass
# ---------------------------------------------------------------------------

@dataclass
class JobFilter:
    """Criteria for narrowing a list of JobStubs.

    All criteria are AND-ed together.  An empty/None criterion is ignored
    (i.e. it matches everything).

    Parameters
    ----------
    levels
        Keep only stubs whose detected level is in this set.
        Valid values: ``"intern"``, ``"graduate"``, ``"junior"``, ``"mid"``,
        ``"senior"``, ``"unknown"``.
        Example: ``{"junior", "graduate", "associate"}``

    stack
        Keep only stubs that mention at least one of these keywords in their
        title or description preview.
        Example: ``{"typescript", "python", "react", "aws"}``

    min_salary
        Exclude stubs whose *advertised minimum* salary is below this value.
        Stubs with no salary listed are kept (benefit of the doubt).

    arrangements
        Keep only stubs that match at least one of these work arrangements.
        Valid values: ``"remote"``, ``"hybrid"``, ``"on-site"``.
        Stubs with no detected arrangement are kept.

    visa_friendly
        If True, exclude stubs with ``visa_eligible = False`` (citizen/PR only).

    exclude_keywords
        Drop stubs whose title or preview contains any of these phrases
        (case-insensitive).  Useful for blocking roles you don't want, e.g.
        ``{"security clearance", "nv1", "defence"}``.
    """

    levels: set[str] = field(default_factory=set)
    stack: set[str] = field(default_factory=set)
    min_salary: float | None = None
    arrangements: set[str] = field(default_factory=set)
    visa_friendly: bool = False
    exclude_keywords: set[str] = field(default_factory=set)

    # Compiled exclude patterns — built lazily on first use.
    _exclude_re: list[re.Pattern] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        # Normalise sets to lowercase.
        self.levels = {s.lower() for s in self.levels}
        self.stack = {s.lower() for s in self.stack}
        self.arrangements = {s.lower() for s in self.arrangements}
        self.exclude_keywords = {s.lower() for s in self.exclude_keywords}
        self._exclude_re = [
            re.compile(re.escape(kw), re.IGNORECASE)
            for kw in self.exclude_keywords
        ]


# ---------------------------------------------------------------------------
# Main filter function
# ---------------------------------------------------------------------------

@dataclass
class FilterResult:
    """Outcome of running filter_stubs()."""
    matched: list[JobStub]
    excluded: list[tuple[JobStub, str]]  # (stub, reason)

    @property
    def total(self) -> int:
        return len(self.matched) + len(self.excluded)

    def summary(self) -> str:
        return (
            f"{len(self.matched)} matched / "
            f"{len(self.excluded)} excluded / "
            f"{self.total} total"
        )


def filter_stubs(stubs: list[JobStub], f: JobFilter) -> FilterResult:
    """Apply *f* to *stubs* and return a FilterResult.

    Each excluded stub is tagged with a short human-readable reason so the
    CLI can display why it was dropped.
    """
    matched: list[JobStub] = []
    excluded: list[tuple[JobStub, str]] = []

    for stub in stubs:
        reason = _why_excluded(stub, f)
        if reason:
            excluded.append((stub, reason))
        else:
            matched.append(stub)

    return FilterResult(matched=matched, excluded=excluded)


def _why_excluded(stub: JobStub, f: JobFilter) -> str | None:
    """Return a short exclusion reason, or None if the stub passes all criteria."""

    # 1. Visa filter.
    if f.visa_friendly and stub.visa_eligible is False:
        return "citizens/PR only"

    # 2. Exclude keywords.
    if f._exclude_re:
        text = " ".join(filter(None, [stub.title, stub.description_preview]))
        for pat in f._exclude_re:
            if pat.search(text):
                return f"contains '{pat.pattern}'"

    # 3. Experience level.
    if f.levels:
        level = classify_level(stub)
        if level not in f.levels:
            return f"level={level!r} (want {sorted(f.levels)})"

    # 4. Tech stack.
    if f.stack and not stub_matches_stack(stub, f.stack):
        return f"no stack match (want any of {sorted(f.stack)})"

    # 5. Minimum salary.
    if f.min_salary is not None:
        sal_min = _parse_salary_min(stub.salary)
        if sal_min is not None and sal_min < f.min_salary:
            return f"salary {stub.salary!r} < ${f.min_salary:,.0f}"

    # 6. Work arrangement.
    if f.arrangements:
        detected = detect_arrangement(stub)
        if detected and not (detected & f.arrangements):
            return f"arrangement={detected} (want {f.arrangements})"

    return None
