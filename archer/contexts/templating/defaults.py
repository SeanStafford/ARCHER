"""
Default values for ARCHER resume structure.

Provides shared defaults used by:
- yaml_normalizer.py (Step 2: add missing fields)
- minimal/builder.py (Step 1: can use for reference, but shouldn't add defaults)

These defaults ensure all resumes have complete metadata for LaTeX compilation.
"""

from typing import Any, Dict

# Default color scheme (neutral professional gray)
DEFAULT_COLORS = {
    "emphcolor": "red",
    "topbarcolor": "black",
    "leftbarcolor": "gray9",
    "brandcolor": "gray9",
    "namecolor": "white",
}

# Default spacing and layout values (from historical resume patterns)
DEFAULT_SETLENGTHS = {
    "leftmargin": "0.4in",
    "rightmargin": "0.5in",
    "aboveheader": "10pt",
    "bottommargin": "0.2in",
    "headheight": "60pt",
    "headervskip": "20pt",
    "leftbarwidth": r"0.275\paperwidth",
    "sidecolwidth": r"\leftbarwidth-1.5\leftmargin",
    "doublecolsep": r"1\leftmargin",
    "projlistvsep": "7pt",
    "firstlistvsep": "10pt",
    "highlightindent": "48pt",
    "seclisttopsepcontent": "-2pt",
    "keyprojvsep": "8pt",
    "seclistlabelsep": "11pt",
    "sectionsep": "15pt",
}

# Default defined lengths
DEFAULT_DEFLENS = {
    "bottombarheight": "50pt",
    "bottombarsolidheight": "60pt",
}

# Section spacing defaults by type
SECTION_SPACING = {
    "skill_list_caps": r"\vspace{2\sectionsep}",
    "skill_list_pipes": r"\vspace{2\sectionsep}",
    "skill_categories": "",
    "work_history": r"\vspace{\sectionsep}",
    "projects": r"\vspace{\sectionsep}",
}


def get_default_metadata() -> Dict[str, Any]:
    """
    Get complete default metadata structure with all expected fields.

    Returns a metadata dict with:
    - Actual defaults for colors, setlengths, deflens, hlcolor
    - null values for fields expected to be filled by user or remain empty

    Used by yaml_normalizer to ensure metadata is complete before LaTeX generation.

    Returns:
        Dict with all metadata fields needed for LaTeX compilation
    """
    return {
        "colors": DEFAULT_COLORS.copy(),
        "setlengths": DEFAULT_SETLENGTHS.copy(),
        "deflens": DEFAULT_DEFLENS.copy(),
        "hlcolor": DEFAULT_COLORS["emphcolor"],  # Default hlcolor to emphcolor
        "custom_packages": None,
        "custom_contact_info": None,
        "fields": {
            "pdfkeywords": None,
        },
    }
