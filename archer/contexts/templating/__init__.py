"""
Templating Context

Responsibilities:
- Manages resume structure representation (structured data model for resume documents)
- Converts between LaTeX (.tex) files and structured data
- Manages LaTeX template system (archer/contexts/rendering/mystyle/)
- Populates templates with targeted content
- Handles branding, spacing, and formatting decisions

Owns: Resume structure representation, tex ↔ structured data conversion, LaTeX template system
Never: Makes content prioritization decisions
"""

from archer.contexts.templating.converter import (
    clean_yaml,
    latex_to_yaml,
    validate_roundtrip_conversion,
    yaml_to_latex,
)
from archer.contexts.templating.resume_data_structure import (
    ResumeDocument,
    ResumeDocumentArchive,
)
from archer.contexts.templating.resume_database import ResumeDatabase

__all__ = [
    "yaml_to_latex",
    "latex_to_yaml",
    "clean_yaml",
    "validate_roundtrip_conversion",
    "ResumeDocument",
    "ResumeDocumentArchive",
    "ResumeDatabase",
]
