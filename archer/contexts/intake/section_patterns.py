"""
Pattern matching for job description section identification.

This module provides regex patterns and helper functions to categorize
job description sections into archetypes and identify boilerplate content.

Pattern classes follow the convention from templating/latex_patterns.py:
- Dataclasses with frozen=True for immutability
- Class-level constants for patterns
- Helper functions that use these patterns
"""

import re
from dataclasses import dataclass
from typing import Optional

# =============================================================================
# MARKDOWN HEADER PATTERNS (for section extraction)
# =============================================================================


@dataclass(frozen=True)
class MarkdownHeaderPatterns:
    """
    Regex patterns for detecting markdown section headers.

    These patterns identify section boundaries in job descriptions.
    Supports both bold markdown (**Header**) and ATX headers (# Header).
    """

    # Main section header: **Section Name** or **Section Name:**
    # Must be at start of line (after stripping)
    BOLD_HEADER: str = r"\*\*([^*]+?):?\*\*"

    # Hash headers: # Header, ## Header, ### Header, #### Header
    # Captures 1-4 hash marks followed by content
    HASH_HEADER: str = r"^#{1,4}\s+(.+?):?\s*$"

    # Combined pattern: matches either bold or hash headers
    SECTION_HEADER: str = r"(?:\*\*([^*]+?):?\*\*|^#{1,4}\s+(.+?):?\s*$)"

    # Subsection header: **- SubSection:** or **• SubSection:** or **— SubSection:**
    # The dash/bullet indicates hierarchy under a parent section
    SUBSECTION_MARKER: str = r"\*\*\s*[-•—]\s*([^*:]+):\s*\*\*"

    # Parent section: bold header that does NOT start with dash/bullet
    # Used to identify which section subsections belong to
    PARENT_SECTION: str = r"\*\*(?!\s*[-•—])([^*:]+):?\s*\*\*"


# =============================================================================
# SECTION ARCHETYPE PATTERNS
# =============================================================================


@dataclass(frozen=True)
class SectionArchetypePatterns:
    """
    Regex patterns for categorizing sections into archetypes.

    Each archetype has a list of patterns that match section names.
    Used by match_section_archetype() to categorize sections.

    These aren't meant to be exhaustive. I've just been adding
    from real job listings encountered during development.
    """

    REQUIRED_QUALIFICATION: tuple = (
        r"you have",
        r"basic qualifications?",
        r"required qualifications?",
        r"minimum qualifications?",
        r"requirements?",
        r"must\-? ?have",  # "must have" / "must-have"
        r"required skills?",
        r"what you'?ll need",
        r"qualified candidates? will have",
        r"required:?",
        r"we're looking for",
        r"what we.* like you to have",
        r"ideally you.*have",
        r"what you('ll)? bring",  # "what you bring" / "what you'll bring"
        r"what we need to see",
    )

    PREFERRED_QUALIFICATION: tuple = (
        r"nice (?:if you )?have",  # "nice have" / "nice if you have"
        r"additional qualifications?",
        r"preferred qualifications?",
        r"^preferred$",  # Bare "Preferred" as standalone subsection
        r"bonus experience",
        r"nice to have",
        r"preferred skills?",
        r"preferred certifications?",
        r"go above and beyond",
        r"desired:?",
        r"strong candidates may also",
        r"what would blow us away",
        r"ways to stand out.*",
        r"what we would like to see",
    )

    AMBIGUOUS_QUALIFICATION: tuple = (r"ideal qualifications?",)

    FALLBACK_QUALIFICATION: tuple = (
        r"^qualifications?$",  # Bare "qualifications" with no modifier
    )

    ABOUT_ROLE: tuple = (
        r"(?:about )?(?:the )?(?:role|position|opportunity)",
        r"job (?:summary|description)",
        r"meaningful work",
    )

    RESPONSIBILITIES: tuple = (
        r"what you'?ll (?:be )?do(?:ing)?",  # "what you'll do" / "what you'll be doing"
        r"responsibilities",
        r"basic responsibilities",
        r"your (?:role|responsibilities)",
    )

    ABOUT_COMPANY: tuple = (
        r"about (?:the )?(?:company|us)",
        r"who we are",
        r"our (?:company|mission|culture)",
    )

    BENEFITS: tuple = (
        r"benefits",
        r"compensation",
        r"what we offer",
        r"perks",
    )

    APPLICATION: tuple = (
        r"how to apply",
        r"application (?:process|instructions)",
        r"equal (?:opportunity|employment)",
        r"eeo statement",
        r"reasonable accommodation",
    )


# Legacy pattern lists for backward compatibility
REQUIRED_QUALIFICATION_PATTERNS = list(SectionArchetypePatterns.REQUIRED_QUALIFICATION)
PREFERRED_QUALIFICATION_PATTERNS = list(SectionArchetypePatterns.PREFERRED_QUALIFICATION)
AMBIGUOUS_QUALIFICATION_PATTERNS = list(SectionArchetypePatterns.AMBIGUOUS_QUALIFICATION)
FALLBACK_QUALIFICATION_PATTERNS = list(SectionArchetypePatterns.FALLBACK_QUALIFICATION)
ABOUT_ROLE_PATTERNS = list(SectionArchetypePatterns.ABOUT_ROLE)
RESPONSIBILITIES_PATTERNS = list(SectionArchetypePatterns.RESPONSIBILITIES)
ABOUT_COMPANY_PATTERNS = list(SectionArchetypePatterns.ABOUT_COMPANY)
BENEFITS_PATTERNS = list(SectionArchetypePatterns.BENEFITS)
APPLICATION_PATTERNS = list(SectionArchetypePatterns.APPLICATION)

# =============================================================================
# BOILERPLATE DETECTION
# =============================================================================

# Known boilerplate sections (aggressive list)
KNOWN_BOILERPLATE_SECTIONS = {
    "eeo statement",
    "equal opportunity employer",
    "equal employment opportunity",
    "diversity and inclusion",
    "reasonable accommodation",
    "disability accommodation",
    "application process",
    "how to apply",
    "privacy policy",
    "disclaimer",
    "pay range",
    "salary",
    "compensation",
    "benefits",
    "perks and benefits",
    "why work at",  # Generic company promotion
    # Metadata sections
    "url",
    "date_posted",
    "location",
    "job_id",
    "time type",
}

# =============================================================================
# ARCHETYPE PRIORITY
# =============================================================================

# Archetype priorities (higher = more specific)
# Used when a section matches multiple archetypes
ARCHETYPE_PRIORITY = {
    "application_process": 1,
    "benefits": 2,
    "about_company": 2,
    "about_role": 3,
    "responsibilities": 4,
    "preferred_qualifications": 5,
    "required_qualifications": 5,
}

# Mapping of archetype names to their patterns
ARCHETYPE_PATTERNS = {
    "required_qualifications": REQUIRED_QUALIFICATION_PATTERNS,
    "preferred_qualifications": PREFERRED_QUALIFICATION_PATTERNS,
    "about_role": ABOUT_ROLE_PATTERNS,
    "responsibilities": RESPONSIBILITIES_PATTERNS,
    "about_company": ABOUT_COMPANY_PATTERNS,
    "benefits": BENEFITS_PATTERNS,
    "application_process": APPLICATION_PATTERNS,
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def normalize_section_name(name: str) -> str:
    """
    Normalize section name for matching.

    Args:
        name: Raw section name from markdown

    Returns:
        Normalized section name (lowercase, stripped, whitespace normalized)
    """
    # Convert to lowercase
    normalized = name.lower()

    # Strip leading/trailing whitespace
    normalized = normalized.strip()

    # Normalize internal whitespace
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized


def match_section_archetype(section_name: str) -> Optional[str]:
    """
    Match section name to archetype using pattern matching.

    If multiple archetypes match, returns the most specific one
    (highest priority).

    Args:
        section_name: Section name to categorize

    Returns:
        Archetype name, or None if no match
    """
    normalized = normalize_section_name(section_name)

    # Find all matching archetypes
    matches = []

    for archetype, patterns in ARCHETYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized):
                matches.append(archetype)
                break  # Don't check other patterns for this archetype

    if not matches:
        return None

    # If single match, return it
    if len(matches) == 1:
        return matches[0]

    # If multiple matches, return highest priority
    return max(matches, key=lambda a: ARCHETYPE_PRIORITY.get(a, 0))


def is_boilerplate_section(section_name: str) -> bool:
    """
    Check if section is known boilerplate.

    Uses substring matching to handle variations like "Our Team's Favorite Perks and Benefits".

    Args:
        section_name: Section name to check

    Returns:
        True if section is boilerplate
    """
    normalized = normalize_section_name(section_name)
    return any(pattern in normalized for pattern in KNOWN_BOILERPLATE_SECTIONS)
