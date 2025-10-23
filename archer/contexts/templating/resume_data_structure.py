"""
Defines structured data representation of resume content for ARCHER.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ResumeSection:
    """
    Represents a single section within a resume.
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

        Returns:
            Parsed ResumeDocument instance
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

    def get_section(self, name: str, case_sensitive: bool = False) -> Optional[ResumeSection]:
        """
        Find a section by name.
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
        """
        return self.fields.get(field_name)

    def get_all_text(self) -> str:
        """
        Get all text content from the resume (fields + sections).
        """
        parts = []

        # Add all field values
        parts.extend(self.fields.values())

        # Add all section content
        for section in self.sections:
            parts.append(section.raw_content)

        return "\n".join(parts)
