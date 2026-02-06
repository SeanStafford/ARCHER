"""
Job description markdown normalizer for the Intake context.

Preprocesses markdown job descriptions to flatten hierarchical structures
before section extraction. Some job listings use nested sub-headers
(e.g., **- Required Skills:** under **WHAT YOU'LL NEED**) that need flattening.

Design principle: Normalize BEFORE parsing, following the pattern from
templating/normalizer.py which preprocesses LaTeX before structured parsing.
"""

import re
import unicodedata

from archer.contexts.intake.section_patterns import MarkdownHeaderPatterns

# Unicode replacements: problematic char → ASCII equivalent
UNICODE_REPLACEMENTS = {
    # Spaces
    "\u00a0": " ",  # non-breaking space → space
    "\u202f": " ",  # narrow no-break space
    # Zero-width characters → remove
    "\u200b": "",  # zero-width space
    "\u200c": "",  # zero-width non-joiner
    "\u200d": "",  # zero-width joiner
    "\u2060": "",  # word joiner
    "\ufeff": "",  # BOM / zero-width no-break space
    # Quotes
    "\u2018": "'",  # left single quote
    "\u2019": "'",  # right single quote
    "\u201c": '"',  # left double quote
    "\u201d": '"',  # right double quote
    # Dashes
    "\u2013": "-",  # en dash
    "\u2014": "--",  # em dash
    # Bullets and misc
    "\u2022": "*",  # bullet
    "\u2026": "...",  # ellipsis
    "\u00b7": "*",  # middle dot (used as bullet)
}


def normalize_unicode(text: str) -> str:
    """
    Normalize unicode characters that cause parsing issues.

    Applies NFKC normalization and replaces common problematic characters
    with ASCII equivalents.

    Args:
        text: Raw text possibly containing problematic unicode

    Returns:
        Text with normalized unicode
    """
    # NFKC normalization handles many compatibility characters
    text = unicodedata.normalize("NFKC", text)

    # Explicit replacements for common issues
    for char, replacement in UNICODE_REPLACEMENTS.items():
        text = text.replace(char, replacement)

    return text


def flatten_subsection_headers(text: str) -> str:
    """
    Convert nested subsection headers to flat section headers.

    Transforms **- Child:** or **• Child:** to **Child:**
    This allows the section extractor to treat them as siblings.

    Args:
        text: Raw markdown text with potentially nested headers

    Returns:
        Text with subsection markers converted to flat headers
    """
    patterns = MarkdownHeaderPatterns()

    # Find all subsection markers and strip the dash/bullet prefix
    # Pattern captures the section name (group 1)
    def replace_subsection(match: re.Match) -> str:
        section_name = match.group(1).strip()
        return f"**{section_name}:**"

    return re.sub(patterns.SUBSECTION_MARKER, replace_subsection, text)


def preprocess_job_markdown(text: str) -> str:
    """
    Preprocess job description markdown before section extraction.

    This is the main entry point for markdown normalization.
    Handles:
    - Unicode normalization (non-breaking spaces, smart quotes, etc.)
    - Flattening nested subsection headers (e.g., **- Required Skills:** → **Required Skills:**)

    Args:
        text: Raw job description markdown

    Returns:
        Normalized markdown ready for section extraction
    """
    # Normalize problematic unicode first
    text = normalize_unicode(text)

    # Flatten any nested subsection headers
    text = flatten_subsection_headers(text)

    return text
