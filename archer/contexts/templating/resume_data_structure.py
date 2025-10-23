"""
Resume Document Structure

Defines structured data representation of resume content for ARCHER.
This structure serves as the interface between Templating and Targeting contexts.

Templating owns:
- Parsing .tex files into ResumeDocument instances
- Serializing ResumeDocument instances back to .tex format

Targeting operates on ResumeDocument instances for analysis and content selection.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from archer.contexts.templating.resume_components_data_structures import (
    Page,
    DocumentMetadata,
)


@dataclass
class ResumeSection:
    """
    Represents a single section within a resume.

    Attributes:
        name: Cleaned section name (e.g., "Core Skills", "Experience")
        raw_content: LaTeX source code between this section header and the next section

    Future extensions:
        - bullets: List[Bullet] - parsed bullet points and their hierarchy
        - subsections: List[Subsection] - nested structure for complex sections
    """
    name: str
    raw_content: str


@dataclass
class ResumeDocument:
    """
    Structured representation of a complete resume document.

    This is the primary data model shared between Templating and Targeting contexts.
    Templating converts .tex ↔ ResumeDocument. Targeting analyzes ResumeDocument instances.

    Attributes:
        fields: LaTeX \renewcommand field values (e.g., {"brand": "ML Engineer | Physicist"})
        sections: Ordered list of resume sections (order preserved from source document)
        metadata: Optional metadata about the document (source path, dates, etc.)
    """
    fields: Dict[str, str] = field(default_factory=dict)
    sections: List[ResumeSection] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_tex(cls, tex_path: Path) -> "ResumeDocument":
        """
        Parse a .tex file into a structured ResumeDocument.

        Args:
            tex_path: Path to LaTeX resume file

        Returns:
            Parsed ResumeDocument instance

        Raises:
            FileNotFoundError: If tex_path does not exist
            ValueError: If tex file cannot be parsed

        Note:
            Implementation will use templating/parser.py functions
        """
        if not tex_path.exists():
            raise FileNotFoundError(f"Resume file not found: {tex_path}")

        # Import here to avoid circular dependency during development
        from archer.contexts.templating.parser import (
            extract_latex_fields,
            extract_all_sections_with_content,
        )

        content = tex_path.read_text(encoding="utf-8")

        # Extract fields
        fields = extract_latex_fields(content)

        # Extract sections with content
        sections_data = extract_all_sections_with_content(content)
        sections = [
            ResumeSection(name=name, raw_content=content)
            for name, content in sections_data
        ]

        # Store metadata
        metadata = {
            "source_path": str(tex_path),
            "filename": tex_path.name,
        }

        return cls(fields=fields, sections=sections, metadata=metadata)

    def to_tex(self) -> str:
        """
        Serialize ResumeDocument back to LaTeX format.

        Returns:
            LaTeX source code as string

        Note:
            This is a stub for future implementation. Will be needed when
            Templating populates templates with content from Targeting.
        """
        raise NotImplementedError(
            "LaTeX serialization not yet implemented. "
            "This will be added when template population is needed."
        )

    def get_section(self, name: str, case_sensitive: bool = False) -> Optional[ResumeSection]:
        """
        Find a section by name.

        Args:
            name: Section name to find
            case_sensitive: Whether to match case exactly

        Returns:
            ResumeSection if found, None otherwise
        """
        if case_sensitive:
            for section in self.sections:
                if section.name == name:
                    return section
        else:
            name_lower = name.lower()
            for section in self.sections:
                if section.name.lower() == name_lower:
                    return section
        return None

    def get_field(self, field_name: str) -> Optional[str]:
        """
        Get a field value by name.

        Args:
            field_name: Field name (e.g., "brand", "profile")

        Returns:
            Field value if exists, None otherwise
        """
        return self.fields.get(field_name)

    def get_all_text(self) -> str:
        """
        Get all text content from the resume (fields + sections).

        Returns:
            Combined text for full-document search
        """
        parts = []

        # Add all field values
        parts.extend(self.fields.values())

        # Add all section content
        for section in self.sections:
            parts.append(section.raw_content)

        return "\n".join(parts)
