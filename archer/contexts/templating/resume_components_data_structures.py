from dataclasses import dataclass, field

@dataclass
class DocumentMetadata:
    name: str
    date: str
    brand: str
    professional_profile: str = None
    fields = field(default_factory=dict)


@dataclass
class TopBar:
    show_professional_profile: bool = True


@dataclass
class Subsection:
    type: str
    content = field(default_factory=dict)


@dataclass
class Section:
    name: str
    type: str
    content = None
    subsections = None


@dataclass
class PageRegions:
    top: TopBar
    left_column = None
    main_column = None


@dataclass
class Page:
    page_number: int
    regions: PageRegions
