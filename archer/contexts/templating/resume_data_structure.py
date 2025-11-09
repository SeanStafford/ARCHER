"""
Resume Document Structure

Defines structured data representation of resume content for ARCHER.
This structure serves as the interface between Templating and Targeting contexts.

Templating owns:
- Parsing .tex files into ResumeDocument instances
- Converting YAML to ResumeDocument instances

Targeting operates on ResumeDocument instances for analysis and content selection.
"""

import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from omegaconf import OmegaConf

from archer.contexts.templating import latex_to_yaml
from archer.utils.markdown import format_list_markdown, latex_to_markdown
from archer.contexts.templating.markdown_formatter import (
    format_education_markdown,
    format_skills_markdown,
    format_work_experience_markdown,
)
from archer.utils.latex_parsing_tools import to_plaintext


DEFAULT_BLACKLIST_PATTERNS = ["Truths and a Lie"]

@dataclass
class ResumeSection:
    """
    Represents a single section within a resume.

    Stores structured content specific to section type (work experience, skills, etc.)
    Provides lazy-evaluated plaintext representation for search and analysis.

    Attributes:
        name: Section name in plaintext (e.g., "AI & Machine Learning", "Core Skills")
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
            # Generic fallback for unknown types
            # Try to format as a list if it has items
            items = self.data.get("items", [])
            if items:
                return format_list_markdown(items, self.name)
            else:
                # Empty or unrecognized - just show header
                return f"## {self.name}\n\n(No content)"



class ResumeDocument:
    """
    Structured representation of a complete resume document.

    This is the primary data model shared between Templating and Targeting contexts.
    Simplified from full YAML structure to contain only content relevant for targeting.

    Supports two modes:
    - markdown: Convert LaTeX formatting to markdown (preserves **bold**, *italic*, etc.)
    - plaintext: Strip all formatting (for statistical analysis, search, embeddings)

    Note: Structural markdown (headers, bullets) from formatters is always present.
    """

    def __init__(self, yaml_path: Path, mode: str = "markdown", blacklist_patterns: List[str] = DEFAULT_BLACKLIST_PATTERNS):
        """
        Load resume from YAML file and simplify to Targeting-focused structure.

        Args:
            yaml_path: Path to YAML file (structured resume format)
            mode: Content formatting mode - "markdown" or "plaintext" (default: "markdown")
            blacklist_patterns: Optional list of regex patterns to exclude sections by name (default: None)

        Returns:
            ResumeDocument instance

        Raises:
            FileNotFoundError: If yaml_path does not exist
            ValueError: If YAML structure is invalid or mode is invalid

        Note:
            Structural markdown (##, -, etc.) is always present regardless of mode.
            Mode only controls inline content formatting.
        """
        if mode not in ("markdown", "plaintext"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'markdown' or 'plaintext'")
        
        if type(yaml_path) is str:
            yaml_path = Path(yaml_path)

        if not yaml_path.exists():
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")

        self.mode = mode
        self.blacklist_patterns = blacklist_patterns
        yaml_data = OmegaConf.load(yaml_path)
        yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

        if "document" not in yaml_dict:
            raise ValueError(f"Invalid YAML structure: missing 'document' key in {yaml_path}")

        doc = yaml_dict["document"]
        self.sections = []

        # Extract professional profile from metadata (appears at top of page 1)
        metadata_dict = doc["metadata"]
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
                
                # Skip empty regions or regions without sections
                if not region_data or not isinstance(region_data, dict) or "sections" not in region_data:
                    continue

                for section_data in region_data["sections"]:
                    # Get section name from metadata (plaintext version for analysis)
                    metadata = section_data["metadata"]
                    section_name = metadata["name_plaintext"]

                    # Skip section if name matches any blacklist pattern
                    if any(re.search(pattern, section_name, re.IGNORECASE) for pattern in self.blacklist_patterns):
                        continue

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
    def from_tex(cls, tex_path: Path, mode: str = "markdown", blacklist_patterns: Optional[List[str]] = None) -> "ResumeDocument":
        """
        Parse a .tex file into a structured ResumeDocument.

        Converts LaTeX to YAML using templating converter, then processes with __init__ which constructs it from a yaml file.

        Args:
            tex_path: Path to LaTeX resume file
            mode: Content formatting mode - "markdown" or "plaintext" (default: "markdown")
            blacklist_patterns: Optional list of regex patterns to exclude sections by name (default: DEFAULT_BLACKLIST_PATTERNS)

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

            # Load from YAML with specified mode
            doc = cls(tmp_path, mode=mode, blacklist_patterns=blacklist_patterns)

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
        """Extract items from standardized list, respecting mode.

        After YAML standardization, all items are dicts with 'latex_raw' and 'plaintext' fields.

        Mode determines formatting:
        - markdown: Convert latex_raw → markdown formatting
        - plaintext: Use plaintext field directly

        Note: Some sections use 'items' key, others use 'bullets' key.
        """
        # Try 'items' first (skill lists), then 'bullets' (personality, skill_category)
        items = content.get("items", content.get("bullets", []))
        if self.mode == "markdown":
            return [latex_to_markdown(item["latex_raw"]) for item in items]
        else:  # plaintext
            return [item["plaintext"] for item in items]

    def _get_section_data(self, section_data: Dict[str, Any], section_name: str = "") -> Dict[str, Any]:
        """Parse a section from YAML structure into ResumeSection.

        Args:
            section_data: Section data from YAML
            section_name: Optional parent section name (e.g., "Experience", "Education")
        """
        section_type = section_data["type"]

        # Get name from metadata (standardized structure)
        metadata = section_data["metadata"]
        raw_name = metadata.get("name", section_name)  # Fallback to section_name if name not in metadata

        if section_type == "work_experience":
            return self._parse_work_experience(section_data)
        elif section_type == "education":
            return self._parse_education(section_data)
        else:
            # For all other types (project, skill_category, etc.)
            content = section_data.get("content", {})
            items = self._get_plaintext_items_from_yaml_list(content)

            # Convert name based on mode (may contain LaTeX like \coloremph{})
            # Use name_plaintext if available (added during standardization), otherwise convert
            if self.mode == "markdown":
                name = latex_to_markdown(metadata.get("name_plaintext", raw_name))
            else:  # plaintext
                try:
                    name = metadata["name_plaintext"]
                except KeyError:
                    raise ValueError(f"Missing 'name_plaintext' in metadata for section with data:\n{section_data}")
                # name = metadata.get("name_plaintext", to_plaintext(raw_name))

            data = {"items": items, "name": name}
            return data
        
    def _parse_work_experience(self, section_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract work experience data from YAML, respecting mode.

        Args:
            section_data: Work experience data from YAML

        Returns:
            Structured work experience data dict with formatting based on mode
        """
        metadata = section_data["metadata"]
        content = section_data["content"]

        # Convert metadata fields based on mode (they may contain LaTeX like \&)
        converted_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, str) and value:
                if self.mode == "markdown":
                    converted_metadata[key] = latex_to_markdown(value)
                else:  # plaintext
                    converted_metadata[key] = to_plaintext(value)
            else:
                converted_metadata[key] = value

        # Extract bullets based on mode
        if self.mode == "markdown":
            bullets = [latex_to_markdown(bullet["latex_raw"]) for bullet in content["bullets"]]
        else:  # plaintext
            bullets = [bullet["plaintext"] for bullet in content["bullets"]]

        # Parse projects with their bullets (standardized structure: proj.content.bullets)
        projects = []
        for proj in content.get("projects", []):
            proj_metadata = proj["metadata"]
            proj_content = proj["content"]

            # Project name: use name_plaintext if available, otherwise convert name based on mode
            if self.mode == "markdown":
                project_name = latex_to_markdown(proj_metadata["name"])
                project_bullets = [latex_to_markdown(bullet["latex_raw"]) for bullet in proj_content["bullets"]]
            else:  # plaintext
                project_name = proj_metadata["name_plaintext"]
                project_bullets = [bullet["plaintext"] for bullet in proj_content["bullets"]]

            project_data = {
                "name": project_name,
                "bullets": project_bullets
            }
            projects.append(project_data)

        return {
            **converted_metadata,
            "projects": projects,
            "bullets": bullets
        }

    def _parse_education(self, section_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse education section, respecting mode.

        Args:
            section_data: Education data from YAML
            section_name: Section heading name (e.g., "Education")
        """
        metadata = section_data.get("metadata", {})
        content = section_data.get("content", {})

        # Convert metadata fields based on mode
        if self.mode == "markdown":
            institution = latex_to_markdown(metadata.get("institution", ""))
            degree = latex_to_markdown(metadata.get("degree", ""))
            field = latex_to_markdown(metadata.get("field", ""))
            dates = latex_to_markdown(metadata.get("dates", ""))
        else:  # plaintext
            institution = to_plaintext(metadata.get("institution", ""))
            degree = to_plaintext(metadata.get("degree", ""))
            field = to_plaintext(metadata.get("field", ""))
            dates = to_plaintext(metadata.get("dates", ""))

        # Extract items based on mode
        if self.mode == "markdown":
            items = [latex_to_markdown(b["latex_raw"]) for b in content.get("bullets", [])]
        else:  # plaintext
            items = [b["plaintext"] for b in content.get("bullets", [])]

        data = {
            "institution": institution,
            "degree": degree,
            "field": field,
            "dates": dates,
            "items": items
        }

        return data


    def get_section(self, name: str, case_sensitive: bool = False) -> ResumeSection:
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
                
        raise AttributeError(f"Section not found: {name}")        

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

    def load(self, mode: str = "available", format_mode: str = "markdown", blacklist_patterns: List[str] = DEFAULT_BLACKLIST_PATTERNS) -> List[ResumeDocument]:
        """
        Load resume documents from archive.

        Args:
            mode: Loading mode
                - "available": Load only pre-converted YAMLs from structured/
                - "all": Load all .tex files, converting if needed
            format_mode: Content formatting mode - "markdown" or "plaintext" (default: "markdown")
            blacklist_patterns: Optional list of regex patterns to exclude sections by name (default: DEFAULT_BLACKLIST_PATTERNS)

        Returns:
            List of successfully loaded ResumeDocument instances

        Raises:
            ValueError: If mode or format_mode is invalid
        """
        if mode not in ("available", "all"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'available' or 'all'")

        if mode == "available":
            return self._load_available(format_mode, blacklist_patterns)
        else:
            return self._load_all(format_mode, blacklist_patterns)

    def _load_available(self, format_mode: str = "markdown", blacklist_patterns: List[str] = DEFAULT_BLACKLIST_PATTERNS) -> List[ResumeDocument]:
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
                doc = ResumeDocument(yaml_file, mode=format_mode, blacklist_patterns=blacklist_patterns)
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

    def _load_all(self, format_mode: str = "markdown", blacklist_patterns: List[str] = DEFAULT_BLACKLIST_PATTERNS) -> List[ResumeDocument]:
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
                    doc = ResumeDocument(yaml_file, mode=format_mode, blacklist_patterns=blacklist_patterns)
                else:
                    # Convert from .tex
                    doc = ResumeDocument.from_tex(tex_file, mode=format_mode, blacklist_patterns=blacklist_patterns)
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
