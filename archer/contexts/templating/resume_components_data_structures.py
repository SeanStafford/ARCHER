"""
Resume Component Data Structures

Defines data classes for resume components: pages, columns, sections, and metadata.
These structures are used by the Templating context for LaTeX ↔ YAML conversion.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DocumentMetadata:
    """
    Document-level metadata from resume preamble.

    Attributes:
        name: Full name (\renewcommand{\myname})
        date: Date (\renewcommand{\mydate})
        brand: Professional brand/title (\renewcommand{\brand})
        professional_profile: Optional profile text (\renewcommand{\ProfessionalProfile})
        colors: Color scheme definitions (emphcolor, topbarcolor, etc.)
        fields: All other \renewcommand field values
    """

    name: str
    date: str
    brand: str
    professional_profile: Optional[str] = None
    colors: Dict[str, str] = field(default_factory=dict)
    fields: Dict[str, str] = field(default_factory=dict)


@dataclass
class TopBar:
    """
    Top bar region of a resume page.

    Contains header with name, contact info, and optional professional profile.

    Attributes:
        show_professional_profile: Whether to show profile (True for page 1, False for page 2+)
    """

    show_professional_profile: bool = True


@dataclass
class BottomBar:
    """
    Bottom bar region (typically on page 2).

    Used for personality sections like "Two Truths and a Lie", "Alias Array", etc.

    Attributes:
        name: Section name/title
        text: Content text
    """

    name: str
    text: str


@dataclass
class Subsection:
    """
    Subsection within a section (e.g., work experience entry, skill category).

    Attributes:
        type: Type identifier (references type definition YAML)
        metadata: Type-specific metadata (company, title, icon, etc.)
        content: Type-specific content (bullets, list, projects, etc.)
    """

    type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    content: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Section:
    """
    Section within a column (e.g., "Core Skills", "Experience", "Software Tools").

    Attributes:
        name: Section name (e.g., "Core Skills")
        type: Type identifier (references type definition YAML)
        content: Direct content for simple sections (skill lists)
        subsections: Nested subsections for complex sections (work experience, skill categories)
    """

    name: str
    type: str
    content: Optional[Dict[str, Any]] = None
    subsections: Optional[List[Subsection]] = None


@dataclass
class Column:
    """
    Column within a page (left or main).

    Attributes:
        sections: Ordered list of sections in this column
    """

    sections: List[Section] = field(default_factory=list)


@dataclass
class PageRegions:
    """
    Regions within a single page.

    Represents the paracol two-column structure used in resumes.

    Attributes:
        top: Top bar with header/profile
        left_column: Left column (skills, tools, languages)
        main_column: Main/right column (experience, projects)
        bottom: Optional bottom bar (page 2 personality sections)
    """

    top: TopBar
    left_column: Optional[Column] = None
    main_column: Optional[Column] = None
    bottom: Optional[BottomBar] = None


@dataclass
class Page:
    """
    Single page of a resume.

    Attributes:
        page_number: Page number (1-indexed)
        regions: Page regions (top, columns, bottom)
    """

    page_number: int
    regions: PageRegions
