"""
Resume Component Data Structures
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DocumentMetadata:
    """
    Document-level metadata from resume preamble.
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
    """
    show_professional_profile: bool = True


@dataclass
class BottomBar:
    """
    Bottom bar region (typically on page 2).
    """
    name: str
    text: str


@dataclass
class Subsection:
    """
    Subsection within a section (e.g., work experience entry, skill category).
    """
    type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    content: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Section:
    """
    Section within a column (e.g., "Core Skills", "Experience", "Software Tools").
    """
    name: str
    type: str
    content: Optional[Dict[str, Any]] = None
    subsections: Optional[List[Subsection]] = None


@dataclass
class Column:
    """
    Column within a page (left or main).
    """
    sections: List[Section] = field(default_factory=list)


@dataclass
class PageRegions:
    """
    Regions within a single page.
    """
    top: TopBar
    left_column: Optional[Column] = None
    main_column: Optional[Column] = None
    bottom: Optional[BottomBar] = None


@dataclass
class Page:
    """
    Single page of a resume.
    """
    page_number: int
    regions: PageRegions
