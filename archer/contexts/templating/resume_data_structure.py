"""
Resume Document Structure

Defines structured data representation of resume content for ARCHER.
This structure serves as the interface between Templating and Targeting contexts.

Templating owns:
- Parsing .tex files into ResumeDocument instances
- Converting YAML to ResumeDocument instances

Targeting operates on ResumeDocument instances for analysis and content selection.
"""

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from omegaconf import OmegaConf

from archer.contexts.templating import latex_to_yaml
from archer.utils.markdown import format_list_markdown
from archer.contexts.templating.markdown_formatter import (
    format_education_markdown,
    format_skills_markdown,
    format_work_experience_markdown,
)
from archer.utils.latex_parsing_tools import to_plaintext


@dataclass
class ResumeSection:
    """
    Represents a single section within a resume.

    Stores structured content specific to section type (work experience, skills, etc.)
    Provides lazy-evaluated plaintext representation for search and analysis.

    Attributes:
        name: Section name (e.g., "Core Skills", "Experience")
        section_type: Type identifier (e.g., "work_experience", "skill_list_caps")
        data: Structured content (varies by section type)
        page_number: Page number where section appears (1-indexed)
        region: Region where section appears (e.g., "left_column", "right_column")
    """
    name: str
    section_type: str
    data: Dict[str, Any] = field(default_factory=dict)
    page_number: int = 1
    region: str = ""
    _text_cache: Optional[str] = field(default=None, init=False, repr=False)

    @property
    def display_name(self) -> str:
        """
        Get display name with region information if applicable.

        Returns:
            Section name with region appended for left_column sections
        """
        if self.region == "left_column":
            return f"{self.name} (Left Column)"
        return self.name

    @property
    def text(self) -> str:
        """
        Lazy-evaluated markdown representation of section content.

        Returns:
            Markdown-formatted text suitable for LLM consumption and analysis
        """
        if self._text_cache is None:
            self._text_cache = self._format_to_text()
        return self._text_cache

    def _format_to_text(self) -> str:
        """Format structured data into markdown."""
        if self.section_type == "work_history":
            # Format section header, then each work experience
            parts = [f"## {self.name}\n"]
            for work_exp in self.data.get("subsections", []):
                parts.append(format_work_experience_markdown(work_exp))
            return "\n\n".join(parts)
        elif self.section_type == "skill_categories":
            # Format section header, then each category
            parts = [f"## {self.name}\n"]
            for category in self.data.get("subsections", []):
                # Unified structure: categories are subsections with items
                category_name = category.get("name", "")
                if category_name:
                    parts.append(f"\n### {category_name}\n")
                # Use "items" key from unified structure
                for skill in category.get("items", []):
                    parts.append(f"- {skill}")
            return "\n".join(parts)
        elif self.section_type in ("skill_list_caps", "skill_list_pipes"):
            # Adapt formatter to use unified "items" key
            adapted_data = {"skills": self.data.get("items", [])}
            return format_skills_markdown(adapted_data, self.name)
        elif self.section_type == "education":
            return format_education_markdown(self.data, self.name)
        elif self.section_type in ("personality_alias_array", "personality_bottom_bar"):
            return format_list_markdown(self.data.get("items", []), self.name)
        else:
            # Generic fallback
            return str(self.data)



class ResumeDocument:
    """
    Structured representation of a complete resume document.

    This is the primary data model shared between Templating and Targeting contexts.
    Simplified from full YAML structure to contain only content relevant for targeting.
    """

    def __init__(self, yaml_path: Path):
        """
        Load resume from YAML file and simplify to Targeting-focused structure.

        Args:
            yaml_path: Path to YAML file (structured resume format)

        Returns:
            ResumeDocument instance

        Raises:
            FileNotFoundError: If yaml_path does not exist
            ValueError: If YAML structure is invalid

        Note:
            Strips formatting/layout metadata, extracts only content.
        """
        if not yaml_path.exists():
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")

        yaml_data = OmegaConf.load(yaml_path)
        yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

        if "document" not in yaml_dict:
            raise ValueError(f"Invalid YAML structure: missing 'document' key in {yaml_path}")

        doc = yaml_dict["document"]
        self.sections = []

        # Extract professional profile from metadata (appears at top of page 1)
        metadata_dict = doc.get("metadata", {})
        self.name = metadata_dict["name_plaintext"]
        self.professional_title = metadata_dict.get("brand_plaintext", "")
        self.professional_profile = metadata_dict.get("professional_profile_plaintext", "")

        # Set document attributes
        self.source_path = str(yaml_path)
        self.filename = yaml_path.stem
        self.date = metadata_dict.get("date", "")

        self._load_sections(doc)

    def _load_sections(self, doc):
        # Extract sections from all pages and regions
        for page_number, page in enumerate(doc["pages"], start=1):
            for region_name, region_data in page["regions"].items():
                if not region_data or not isinstance(region_data, dict) or "sections" not in region_data:
                    # Claude Code, put a descriptive comment here
                    continue

                for section_data in region_data["sections"]:
                    # Get section name from container
                    section_name = section_data["name"]

                    if "subsections" in section_data:
                        # Parse all subsections
                        subsections = [self._get_section_data(subsection) for subsection in section_data["subsections"]]
                        data = {"subsections": subsections}
                        
                    else:
                        # Handle direct sections
                        data = self._get_section_data(section_data)

                    section = ResumeSection(
                        name=section_name,
                        section_type=section_data["type"],
                        data=data,
                        page_number=page_number,
                        region=region_name
                    )
                    self.sections.append(section)

    @classmethod
    def from_tex(cls, tex_path: Path) -> "ResumeDocument":
        """
        Parse a .tex file into a structured ResumeDocument.

        Converts LaTeX to YAML using templating converter, then processes with __init__ which constructs it from a yaml file.

        Args:
            tex_path: Path to LaTeX resume file

        Returns:
            ResumeDocument instance

        Raises:
            FileNotFoundError: If tex_path does not exist
            ValueError: If tex file cannot be parsed

        Note:
            If conversion fails, a warning is raised suggesting use of the
            conversion script which saves intermediate files for debugging.
        """
        if not tex_path.exists():
            raise FileNotFoundError(f"Resume file not found: {tex_path}")

        try:
            # Create temporary YAML in memory
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp:
                tmp_path = Path(tmp.name)

            # Convert LaTeX to YAML
            latex_to_yaml(tex_path, tmp_path)

            # Load from YAML
            doc = cls(tmp_path)

            # Clean up temp file
            tmp_path.unlink()

            # Update with original source
            doc.source_path = str(tex_path)
            doc.filename = tex_path.stem

            return doc

        except Exception as e:
            warnings.warn(
                f"Failed to convert {tex_path.name}: {str(e)}\n"
                f"Consider using scripts/latex_to_yaml.py which saves intermediate files for debugging.",
                UserWarning
            )
            raise ValueError(f"Failed to parse {tex_path}: {str(e)}") from e

    def _get_plaintext_items_from_yaml_list(self, content):
        """Extract latex_raw from standardized list items for markdown conversion.

        After YAML standardization, all items are dicts with 'latex_raw' and 'plaintext' fields.
        We use latex_raw so latex_to_markdown() can convert LaTeX formatting to markdown.
        """
        items = content.get("items", [])
        return [item["latex_raw"] for item in items]

    def _get_section_data(self, section_data: Dict[str, Any], section_name: str = "") -> Dict[str, Any]:
        """Parse a section from YAML structure into ResumeSection.

        Args:
            section_data: Section data from YAML
            section_name: Optional parent section name (e.g., "Experience", "Education")
        """
        section_type = section_data.get("type")
        name = section_data.get("name", "") or section_name

        if section_type == "work_experience":
            return self._parse_work_experience(section_data)
        elif section_type == "education":
            return self._parse_education(section_data)
        else:
            content = section_data.get("content", {})
            items = self._get_plaintext_items_from_yaml_list(content)

            data = {"items": items, "name": name}
            return data
        
    def _parse_work_experience(self, section_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract work experience data from YAML for markdown conversion.

        Args:
            section_data: Work experience data from YAML

        Returns:
            Structured work experience data dict with LaTeX formatting
            (to be converted to markdown by formatters)
        """
        metadata = section_data["metadata"]
        content = section_data["content"]

        # Extract latex_raw for markdown conversion
        bullets = [bullet["latex_raw"] for bullet in content["bullets"]]

        # Parse projects with their bullets
        projects = []
        for proj in content.get("projects", []):
            proj_metadata = proj.get("metadata", {})
            project_data = {
                "name": proj_metadata["name"],  # Already LaTeX from metadata
                "bullets": [bullet["latex_raw"] for bullet in proj["bullets"]]
            }
            projects.append(project_data)

        return {
            **metadata,
            "projects": projects,
            "bullets": bullets
        }

    def _parse_education(self, section_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse education section for markdown conversion.

        Args:
            section_data: Education data from YAML
            section_name: Section heading name (e.g., "Education")
        """
        metadata = section_data.get("metadata", {})
        content = section_data.get("content", {})

        data = {
            "institution": metadata.get("institution", ""),
            "degree": metadata.get("degree", ""),
            "field": metadata.get("field", ""),
            "dates": metadata.get("dates", ""),
            "items": [b["latex_raw"] for b in content.get("bullets", [])]
        }

        return data


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

    def get_all_text(self) -> str:
        """
        Get all text content from the resume.

        Returns:
            Combined markdown text with professional profile at top and page breaks (---) between pages
        """
        parts = []

        # Add professional profile at the top
        if self.name:
            parts.append(f"# {self.name}\n")
        if self.professional_title:
            parts.append(f"{self.professional_title}\n")
        if self.professional_profile:
            parts.append(self.professional_profile)

        if not self.sections:
            return "\n".join(parts) if parts else ""

        # Add sections
        current_page = 1
        for section in self.sections:
            # Insert page break when page number changes
            if section.page_number != current_page:
                parts.append("---")
                current_page = section.page_number

            parts.append(section.text)

        return "\n\n".join(parts)

    @property
    def table_of_contents(self) -> str:
        """
        Get formatted table of contents showing all sections.

        Returns:
            Formatted table with section display names, page numbers, regions, and types
        """
        if not self.sections:
            return "No sections found."

        lines = []
        for i, section in enumerate(self.sections, 1):
            lines.append(
                f"{i:2}. {section.display_name:45} | page {section.page_number} | "
                f"{section.region:15} | {section.section_type}"
            )
        return "\n".join(lines)


class ResumeDocumentArchive:
    """
    Manager for loading and accessing multiple resume documents.

    Provides batch loading with error handling and summary reporting.
    """

    def __init__(self, archive_path: Path):
        """
        Initialize archive manager.

        Args:
            archive_path: Path to resume archive directory (data/resume_archive/)
        """
        self.archive_path = archive_path
        self.structured_path = archive_path / "structured"

    def load(self, mode: str = "available") -> List[ResumeDocument]:
        """
        Load resume documents from archive.

        Args:
            mode: Loading mode
                - "available": Load only pre-converted YAMLs from structured/
                - "all": Load all .tex files, converting if needed

        Returns:
            List of successfully loaded ResumeDocument instances

        Raises:
            ValueError: If mode is invalid
        """
        if mode not in ("available", "all"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'available' or 'all'")

        if mode == "available":
            return self._load_available()
        else:
            return self._load_all()

    def _load_available(self) -> List[ResumeDocument]:
        """Load only pre-converted YAMLs from structured/ directory."""
        if not self.structured_path.exists():
            warnings.warn(
                f"Structured directory not found: {self.structured_path}\n"
                f"Run scripts/latex_to_yaml.py batch to convert resumes.",
                UserWarning
            )
            return []

        yaml_files = sorted(self.structured_path.glob("*.yaml"))
        documents = []
        errors = []

        for yaml_file in yaml_files:
            try:
                doc = ResumeDocument(yaml_file)
                documents.append(doc)
            except Exception as e:
                errors.append((yaml_file.name, str(e)))

        if errors:
            error_summary = "\n".join(f"  - {name}: {error}" for name, error in errors)
            warnings.warn(
                f"Failed to load {len(errors)} YAML file(s):\n{error_summary}",
                UserWarning
            )

        return documents

    def _load_all(self) -> List[ResumeDocument]:
        """Load all resumes, converting .tex files if needed."""
        # Get all .tex files
        tex_files = sorted(self.archive_path.glob("*.tex"))

        # Check which are already converted
        if self.structured_path.exists():
            existing_yamls = {f.stem for f in self.structured_path.glob("*.yaml")}
        else:
            existing_yamls = set()

        documents = []
        errors = []

        for tex_file in tex_files:
            try:
                if tex_file.stem in existing_yamls:
                    # Load from YAML
                    yaml_file = self.structured_path / f"{tex_file.stem}.yaml"
                    doc = ResumeDocument(yaml_file)
                else:
                    # Convert from .tex
                    doc = ResumeDocument.from_tex(tex_file)
                documents.append(doc)
            except Exception as e:
                errors.append((tex_file.name, str(e)))

        if errors:
            error_summary = "\n".join(f"  - {name}: {error}" for name, error in errors[:10])
            if len(errors) > 10:
                error_summary += f"\n  ... and {len(errors) - 10} more"

            warnings.warn(
                f"Failed to load {len(errors)}/{len(tex_files)} resume(s):\n{error_summary}\n\n"
                f"Consider using scripts/latex_to_yaml.py batch to convert all resumes with validation.",
                UserWarning
            )

        return documents
