"""
visa_filter.py — work-rights / visa eligibility detection for job listings.

Two public surfaces:

  detect_visa_signals(text) -> tuple[bool | None, bool | None]
      Scans raw description text and returns (visa_eligible, sponsorship_available).
      Called by every fetcher immediately after it extracts the description.

  is_visa_friendly(job) -> bool
      High-level helper used by the CV pipeline to filter listings worth applying
      to.  Returns True for listings that are open or unknown; False only when the
      ad explicitly restricts to citizens / PR.
"""

from __future__ import annotations

import re

from .models import JobListing

# ---------------------------------------------------------------------------
# Signal tables
# ---------------------------------------------------------------------------

# Patterns that signal the role is OPEN to visa holders (visa_eligible = True).
_OPEN_PATTERNS: list[str] = [
    r"open to all work rights",
    r"all visa types welcome",
    r"working rights? not required",
    r"international applicants? welcome",
    # Require "visa" before "sponsorship" so we don't match "No sponsorship available."
    r"visa sponsorship (available|provided|offered|considered)",
    r"sponsorship (available|provided|considered) for (the )?right",
    r"we (offer|provide|consider) sponsorship",
    r"sponsorship is (available|provided|offered)",
    r"temporary residents? welcome",
    r"we will sponsor",
    r"457\s*/?\s*(tss|482)?\s*visa",
    r"tss visa",
    r"482 visa",
    r"skilled (worker|migrant) visa",
]

# Patterns that signal RESTRICTION to citizens / PR (visa_eligible = False).
# We deliberately keep this list conservative — false exclusions cost more than
# false inclusions for the user's workflow.
_RESTRICTED_PATTERNS: list[str] = [
    r"must be an? australian citizen",
    r"australian citizen or permanent resident",
    r"australian\s*/?\s*new zealand citizen",
    r"permanent reside?ncy required",
    r"(nv1|baseline|nv2|ts|tsp) clearance",           # security clearance ⇒ citizenship
    r"must hold (or be eligible for)? (a )?(security|defence) clearance",
    r"eligible for security clearance",
    r"full working rights",                            # ambiguous — treated as None
    # The line above is intentionally classified as None, handled separately below.
]

# Patterns that specifically imply the candidate must be a citizen
# (subset of restricted where we are confident enough to set False).
_CITIZEN_ONLY_PATTERNS: list[str] = [
    # ── Citizenship requirement ───────────────────────────────────────────
    # Singular AND plural ("citizen" / "citizens", "resident" / "residents").
    r"must be an? australian citizens?",
    r"(applicants?|candidates?|you) must be (an? )?australian citizens?",

    # Bare "Australian Citizen" / "Australian Citizens" — appears as a
    # standalone requirement line in government traineeships and similar ads.
    # \b anchors to the complete word so the lookaheads fire on what follows
    # the full word, not on a mid-word backtrack position.
    # Negative lookaheads exclude the rare open phrasings such as
    # "Australian Citizens and international applicants welcome".
    r"australian citizens?\b(?!\s+(?:and|or)\s+(?:international|overseas|temporary|all|other|visa)\b)(?!\s+welcome\b)(?!\s+invited\b)",

    # "Australian citizen or permanent resident" — all plural/singular combos.
    r"australian citizens?\s*(or|and)\s*permanent residents?",
    r"australian citizens?\s*(or|and)\s*nz citizens?",
    r"australian\s*(?:/|\s+or\s+)?\s*new zealand citizens?",

    # "citizenship or permanent residency required/needed"
    r"(australian )?(citizenship|citizen)\s*(or\s*permanent\s*residen\w*)?\s*(required|needed|mandatory|only)",

    # "available/open to Australian citizens [only]"
    r"(available|open)\s+only\s+to\s+(australian\s+)?citizens?",

    # "only open to / open only to Australian citizens and permanent residents"
    r"(only open|open only) to (australian )?(citizens?|permanent residen)",
    r"role is open only to (australian )?(citizens?|permanent residen)",
    r"(only open|open only) to (australian )?(citizens?|permanent residen)",

    # "restricted to Australian citizens/PR"
    r"restricted to (australian )?(citizens?|permanent residen)",

    # ── Permanent residency ───────────────────────────────────────────────
    r"permanent reside?ncy required",
    r"must (hold|have) (australian )?(permanent residen\w*|pr)\b",

    # ── PR ↔ citizenship cross-phrases ───────────────────────────────────
    # "working rights (PR or Citizenship)", "working rights — PR/citizen"
    r"working rights?\s*[\(\-–—]\s*(pr|permanent residen|citizen)",
    # "PR or citizenship required", "citizenship or PR"
    r"\b(pr|permanent residen\w*)\s+(or|and)\s+citizen\w*\b",
    r"\bcitizen\w*\s+(or|and)\s+(pr|permanent residen\w*)\b",

    # ── Security clearance (implies citizenship) ──────────────────────────
    r"(nv1|baseline|nv2|ts|tsp)\s*(level)?\s*clearance",
    r"must hold (or be eligible for)? (a )?(security|defence|national security) clearance",
    r"(hold|obtain|maintain) (a |an )?(security|defence) clearance",
    r"eligible for (a |an )?(security|defence|nv1|baseline) clearance",

    # ── Temporary visa exclusion ──────────────────────────────────────────
    # Direct statement that temp visa holders cannot apply.
    # "Sponsorship is not available" alone is NOT here — a 485 holder has
    # full work rights and doesn't need sponsorship.
    r"temporary (work )?visas? (are )?(not available|not offered|unavailable)",

    # ── Unrestricted working rights ───────────────────────────────────────
    r"unrestricted (australian )?working rights",
]

# Patterns indicating sponsorship is explicitly available.
_SPONSORSHIP_PATTERNS: list[str] = [
    r"visa sponsorship (provided|available|offered)",
    r"sponsorship (available|provided) for (the )?right candidate",
    r"we will sponsor",
    r"457\s*/?\s*(tss|482)?\s*visa (considered|available|provided)",
    r"tss\s*/?\s*482 visa",
    r"sponsorship considered",
]

# Compile all patterns once.
def _compile(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


_OPEN_RE = _compile(_OPEN_PATTERNS)
_CITIZEN_ONLY_RE = _compile(_CITIZEN_ONLY_PATTERNS)
_SPONSORSHIP_RE = _compile(_SPONSORSHIP_PATTERNS)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_visa_signals(text: str) -> tuple[bool | None, bool | None]:
    """Scan *text* (a raw job description) for work-rights signals.

    Evaluation order (restrictions win over open signals):
      1. Citizen/PR-only restriction  → (False, None)
      2. Explicit sponsorship offer   → (True,  True)
      3. Other open signal            → (True,  None)
      4. No signal                    → (None,  None)

    Returns
    -------
    visa_eligible : bool | None
        True  — ad explicitly welcomes visa holders or mentions sponsorship.
        False — ad explicitly restricts to citizens / PR.
        None  — no clear signal (user should check manually).

    sponsorship_available : bool | None
        True  — ad explicitly offers visa sponsorship.
        None  — no sponsorship signal detected.
    """
    # Restrictions are checked first so a phrase like "no sponsorship available"
    # cannot accidentally trigger the open-signal path.
    if _any_match(_CITIZEN_ONLY_RE, text):
        return False, None

    sponsorship = _any_match(_SPONSORSHIP_RE, text) or None
    if sponsorship:
        return True, True

    if _any_match(_OPEN_RE, text):
        return True, None

    return None, None


def is_visa_friendly(job: JobListing) -> bool:
    """Return True if the listing is worth applying to on a temporary visa.

    Logic
    -----
    - Explicitly restricted (visa_eligible = False) → exclude.
    - Open or unknown (True / None) → include; the user decides.

    This is intentionally permissive: we would rather surface an ambiguous
    listing and let the applicant judge than silently drop an opportunity.
    """
    return job.visa_eligible is not False


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _any_match(patterns: list[re.Pattern], text: str) -> bool:
    return any(p.search(text) for p in patterns)
