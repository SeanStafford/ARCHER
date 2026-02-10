"""
Reusable patterns and constants for job description parsing.

This module provides geographic constants and regex patterns used across
the intake context for metadata extraction and normalization.

Pattern classes follow the convention from templating/latex_patterns.py:
- Dataclasses with frozen=True for immutability
- Class-level constants for patterns
- Helper functions that use these patterns
"""

import re
from dataclasses import dataclass

# =============================================================================
# FIELD DEFINITIONS
# =============================================================================

REQUIRED_FIELDS = ["Company", "Role", "Location"]

# Optional fields that have validated LLM extraction
OPTIONAL_FIELDS_LLM_VIABLE = ["Salary", "Work Mode"]

# Optional fields for manual entry only (satisfactory LLM performance not confirmed)
OPTIONAL_FIELDS_MANUAL = ["Job ID", "Source", "URL", "Clearance", "Date Posted"]

# All optional fields (for heuristic extraction, which is free to attempt)
OPTIONAL_FIELDS = OPTIONAL_FIELDS_LLM_VIABLE + OPTIONAL_FIELDS_MANUAL

# Fields viable for LLM fallback extraction (validated >80% accuracy)
LLM_VIABLE_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS_LLM_VIABLE

ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

# =============================================================================
# GEOGRAPHIC CONSTANTS
# =============================================================================

US_STATES = (
    "Alabama",
    "Alaska",
    "Arizona",
    "Arkansas",
    "California",
    "Colorado",
    "Connecticut",
    "Delaware",
    "Florida",
    "Georgia",
    "Hawaii",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Kansas",
    "Kentucky",
    "Louisiana",
    "Maine",
    "Maryland",
    "Massachusetts",
    "Michigan",
    "Minnesota",
    "Mississippi",
    "Missouri",
    "Montana",
    "Nebraska",
    "Nevada",
    "New Hampshire",
    "New Jersey",
    "New Mexico",
    "New York",
    "North Carolina",
    "North Dakota",
    "Ohio",
    "Oklahoma",
    "Oregon",
    "Pennsylvania",
    "Rhode Island",
    "South Carolina",
    "South Dakota",
    "Tennessee",
    "Texas",
    "Utah",
    "Vermont",
    "Virginia",
    "Washington",
    "West Virginia",
    "Wisconsin",
    "Wyoming",
)

# Build regex alternation from state names
_US_STATE_PATTERN = "|".join(re.escape(s) for s in US_STATES)


# =============================================================================
# LOCATION PATTERNS
# =============================================================================


@dataclass(frozen=True)
class LocationPatterns:
    """
    Regex patterns for extracting location information from job descriptions.

    Supports various formats:
    - City, ST (two-letter state code)
    - City, State Name (full state name)
    - Work mode indicators (Remote, Hybrid, On-site)
    """

    # City, State (2-letter abbreviation) - e.g., "Baltimore, MD"
    # Uses literal space (not \s) to prevent matching across line breaks
    CITY_STATE_ABBREV: re.Pattern = re.compile(r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)*),\s*([A-Z]{2})\b")

    # City, State (full name) - e.g., "Baltimore, Maryland"
    CITY_STATE_FULL: re.Pattern = re.compile(
        rf"\b([A-Z][a-z]+(?: [A-Z][a-z]+)*),\s*({_US_STATE_PATTERN})\b"
    )

    # Work arrangement indicators
    WORK_MODE: re.Pattern = re.compile(r"\b(Remote|Hybrid|On-?site|In-?office)\b", re.IGNORECASE)


# Convenience list for iteration
LOCATION_PATTERNS = [
    LocationPatterns.CITY_STATE_ABBREV,
    LocationPatterns.CITY_STATE_FULL,
    LocationPatterns.WORK_MODE,
]


# =============================================================================
# SALARY PATTERNS
# =============================================================================


@dataclass(frozen=True)
class SalaryPatterns:
    """
    Regex patterns for extracting salary information from job descriptions.
    """

    SALARY_RANGE: re.Pattern = re.compile(
        r"\$[\d,]+(?:\s*[-–—]\s*\$[\d,]+)?(?:\s*(?:per\s+)?(?:year|yr|annually|/yr))?",
        re.IGNORECASE,
    )


# =============================================================================
# JOB ID PATTERNS
# =============================================================================


@dataclass(frozen=True)
class JobIdPatterns:
    """
    Regex patterns for extracting job/requisition IDs from job descriptions.
    """

    # Job ID/Number/Ref variations — word boundary after keyword prevents matching "Identification"
    JOB_ID: re.Pattern = re.compile(
        r"(?:Job\s*(?:ID|#|Number|Ref|Identification))\b[:\s]*([A-Z0-9_-]+)", re.IGNORECASE
    )

    # Position ID variations
    POSITION_ID: re.Pattern = re.compile(
        r"(?:Position\s*(?:ID|#|Number))[:\s]*([A-Z0-9_-]+)", re.IGNORECASE
    )


# Convenience list for iteration
JOB_ID_PATTERNS = [
    JobIdPatterns.JOB_ID,
    JobIdPatterns.POSITION_ID,
]


# =============================================================================
# METADATA PATTERNS
# =============================================================================


@dataclass(frozen=True)
class MetadataPatterns:
    """
    Regex patterns for extracting inline metadata from markdown.
    """

    # Bold metadata - e.g., **Company:** Acme Corp
    BOLD_FIELD: re.Pattern = re.compile(r"\*\*([^*]+):\*\*\s*(.+?)(?:\n|$)")
