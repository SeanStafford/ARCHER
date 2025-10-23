"""
LaTeX Pattern Constants

Centralized LaTeX pattern strings used for parsing and generation.
Organized into frozen dataclasses by category for immutability and clear grouping.
"""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class DocumentPatterns:
    """
    Document-level LaTeX patterns.

    Used for document boundary detection and page splitting.
    """
    BEGIN_DOCUMENT: str = r'\begin{document}'
    END_DOCUMENT: str = r'\end{document}'
    CLEARPAGE: str = r'\clearpage'


@dataclass(frozen=True)
class PagePatterns:
    """
    Page layout patterns for two-column paracol structure.

    Used for page region extraction and generation.
    """
    BEGIN_PARACOL: str = r'\begin{paracol}{2}'
    END_PARACOL: str = r'\end{paracol}'
    SWITCHCOLUMN: str = r'\switchcolumn'


@dataclass(frozen=True)
class SectionPatterns:
    """
    Section heading patterns.

    Used for section boundary detection.
    """
    SECTION_STAR: str = r'\section*'


@dataclass(frozen=True)
class EnvironmentPatterns:
    """
    Custom LaTeX environment patterns for resume content.

    Used for parsing work experience, projects, and skill lists.
    """
    # Work experience
    BEGIN_ITEMIZE_ACADEMIC: str = r'\begin{itemizeAcademic}'
    END_ITEMIZE_ACADEMIC: str = r'\end{itemizeAcademic}'
    ITEMI: str = r'\itemi'

    # Projects
    BEGIN_ITEMIZE_APROJECT: str = r'\begin{itemizeAProject}'
    END_ITEMIZE_APROJECT: str = r'\end{itemizeAProject}'
    ITEMII: str = r'\itemii'

    # Skill lists
    BEGIN_ITEMIZE_LL: str = r'\begin{itemizeLL}'
    END_ITEMIZE_LL: str = r'\end{itemizeLL}'
    ITEM_LL: str = r'\itemLL'

    BEGIN_ITEMIZE_MAIN: str = r'\begin{itemizeMain}'
    END_ITEMIZE_MAIN: str = r'\end{itemizeMain}'


@dataclass(frozen=True)
class MetadataPatterns:
    """
    Preamble metadata field patterns.

    Used for extracting and generating document metadata (name, brand, colors, etc.).
    """
    # Command patterns
    RENEWCOMMAND: str = r'\renewcommand'
    SETUPHYPERANDMETA: str = r'\setuphyperandmeta'
    SETHLCOLOR: str = r'\sethlcolor'
    DEF_NLINESPP: str = r'\def\nlinesPP'

    # Field names (for \renewcommand extraction)
    MYNAME: str = 'myname'
    MYDATE: str = 'mydate'
    BRAND: str = 'brand'
    PROFESSIONAL_PROFILE: str = 'ProfessionalProfile'
    PDFKEYWORDS: str = 'pdfkeywords'


@dataclass(frozen=True)
class ColorFields:
    """
    Known color field names for resume theming.

    These are extracted separately from general metadata fields.
    """
    EMPHCOLOR: str = 'emphcolor'
    TOPBARCOLOR: str = 'topbarcolor'
    LEFTBARCOLOR: str = 'leftbarcolor'
    BRANDCOLOR: str = 'brandcolor'
    NAMECOLOR: str = 'namecolor'

    @classmethod
    def all(cls) -> List[str]:
        """Return list of all color field names."""
        return [
            cls.EMPHCOLOR,
            cls.TOPBARCOLOR,
            cls.LEFTBARCOLOR,
            cls.BRANDCOLOR,
            cls.NAMECOLOR,
        ]


@dataclass(frozen=True)
class FormattingPatterns:
    """
    LaTeX formatting command patterns.

    Used for cleaning metadata values and generating formatted content.
    """
    TEXTBF: str = r'\textbf'
    CENTERING: str = r'\centering'
    PAR: str = r'\par'
    SCSHAPE: str = r'\scshape'
    SETLENGTH: str = r'\setlength'
    BASELINESKIP: str = r'\baselineskip'
    PARSKIP: str = r'\parskip'
    TEXTTT: str = r'\texttt'
    COLOREMPH: str = r'\coloremph'
