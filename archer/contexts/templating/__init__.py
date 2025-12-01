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
    ConversionResult,
    clean_yaml,
    generate_resume,
    parse_resume,
    validate_roundtrip_conversion,
)
from archer.contexts.templating.normalizer import (
    NormalizationResult,
    normalize_resume,
)
from archer.contexts.templating.resume_data_structure import (
    ResumeDocument,
    ResumeDocumentArchive,
)
from archer.contexts.templating.resume_database import ResumeDatabase

__all__ = [
    # Helpers and orchestrators for bidirectional conversion
    "clean_yaml",
    "validate_roundtrip_conversion",
    "parse_resume",
    "generate_resume",
    "ConversionResult",
    # Normalization orchestration
    "normalize_resume",
    "NormalizationResult",
    # Data structure classes
    "ResumeDocument",
    "ResumeDocumentArchive",
    "ResumeDatabase",
]
