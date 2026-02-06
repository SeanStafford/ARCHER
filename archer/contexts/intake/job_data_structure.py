"""
Job description data structure for the Intake context.

Provides JobListing class that represents a parsed job description
with structured access methods for the Targeting context.
"""

import re
import warnings as warnings_module
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from archer.contexts.intake.job_parser import parse_job_structured_markdown, parse_job_text
from archer.contexts.intake.nomenclature import (
    identifier_from_filename,
    resolve_job_source,
)


@dataclass
class JobListing:
    """
    Parsed job description with structured access methods.

    This class provides the minimal API needed by the Targeting context
    to analyze job requirements and match against resume content.

    Factory methods:
        from_text(text) - Parse raw markdown text
        from_file(path) - Load from markdown file (derives identifier from filename)
        from_database(company, req_id) - Load from job listings database (not yet implemented)
        from_identifier(id) - Auto-resolve from markdown file
    """

    # Raw content
    raw_text: str

    # Parsed sections (key = section name, value = text content)
    sections: dict[str, str]

    # Standard qualification sections (section names, not content)
    required_qualifications_sections: list[str] = field(default_factory=list)
    preferred_qualifications_sections: list[str] = field(default_factory=list)

    # Internal metadata (used for filtering, not exposed in public API)
    _boilerplate_sections: set[str] = field(default_factory=set)
    _section_archetypes: dict[str, str] = field(default_factory=dict)

    # Job metadata
    metadata: dict[str, str] = field(default_factory=dict)
    job_identifier: Optional[str] = None
    title: Optional[str] = None
    source_url: Optional[str] = None

    def _derive_title(self) -> str:
        """
        Derive title from metadata Role field, falling back to first line of raw text.

        Priority:
        1. metadata["Role"] (canonical format)
        2. First line of raw text (last resort)
        """
        if self.metadata.get("Role"):
            return self.metadata["Role"]

        # Last resort: first line of raw text
        first_line = self.raw_text.split("\n")[0].strip()
        # Strip markdown header markers (# and **)
        title = first_line.lstrip("#").strip()
        if title.startswith("**") and title.endswith("**"):
            title = title[2:-2]
        return title

    # =========================================================================
    # FACTORY METHODS
    # =========================================================================

    @classmethod
    def from_text(
        cls,
        text: str,
        source_url: Optional[str] = None,
        job_identifier: Optional[str] = None,
        title: Optional[str] = None,
        use_markdown_tree: bool = False,
    ) -> "JobListing":
        """
        Parse job description text and create a JobListing.

        This is the primary way to create a JobListing from raw markdown.

        Args:
            text: Raw job description markdown
            source_url: Optional URL where job was fetched
            job_identifier: Optional job identifier (if not provided, will be None)
            title: Optional job title (if not provided, derived from first line)

        Returns:
            JobListing instance with parsed sections and extracted features
        """

        if use_markdown_tree:
            parsed = parse_job_structured_markdown(text, source_url=source_url)
        else:
            parsed = parse_job_text(text, source_url=source_url)

        # Surface parser warnings
        for warning in parsed.warnings:
            warnings_module.warn(warning, stacklevel=2)

        return cls(
            raw_text=parsed.raw_text,
            sections=parsed.sections,
            required_qualifications_sections=parsed.required_qualifications_sections,
            preferred_qualifications_sections=parsed.preferred_qualifications_sections,
            _boilerplate_sections=parsed.boilerplate_sections,
            _section_archetypes=parsed.section_archetypes,
            metadata=parsed.metadata,
            job_identifier=job_identifier,
            title=title,
            source_url=parsed.source_url,
        )

    @classmethod
    def from_file(
        cls, file_path: Path, source_url: Optional[str] = None, use_markdown_tree: bool = False
    ) -> "JobListing":
        """
        Parse job description file and create a JobListing.

        The job identifier is derived from the filename stem.
        The title is derived from the first line of the file.

        Args:
            file_path: Path to markdown file
            source_url: Optional URL (defaults to None)

        Returns:
            JobListing instance with parsed sections and extracted features
        """
        file_path = Path(file_path)  # Ensure Path object
        text = file_path.read_text()
        job_id = identifier_from_filename(file_path.name)
        job = cls.from_text(
            text, source_url=source_url, job_identifier=job_id, use_markdown_tree=use_markdown_tree
        )
        # Derive title from metadata or file content
        if not job.title:
            job.title = job._derive_title()
        return job

    @classmethod
    def from_database(cls, company: str, requisition_id: str, **kwargs) -> "JobListing":
        """Load job from a company database. Not yet implemented."""
        raise NotImplementedError("Database source resolution is not yet implemented")

    @classmethod
    def from_identifier(cls, identifier: str, use_markdown_tree: bool = False) -> "JobListing":
        """
        Load job by identifier, auto-resolving the source.

        Args:
            identifier: Job identifier (e.g., "MLEng_AcmeCorp_10130042")

        Returns:
            JobListing instance

        Raises:
            ValueError: If job not found in any source
        """
        source_info = resolve_job_source(identifier)
        if source_info is None:
            raise ValueError(f"Job not found: {identifier}")

        job = cls.from_text(
            source_info.description,
            source_url=source_info.url,
            job_identifier=identifier,
            use_markdown_tree=use_markdown_tree,
        )
        if not job.title:
            job.title = job._derive_title()
        return job

    # =========================================================================
    # PUBLIC API METHODS
    # =========================================================================

    def get_text(self, exclude_boilerplate: bool = True) -> str:
        """
        Get full job description text.

        Args:
            exclude_boilerplate: If True, remove boilerplate sections

        Returns:
            Concatenated text from all (non-boilerplate) sections
        """
        if exclude_boilerplate:
            # Filter out boilerplate sections
            sections_to_include = [
                content
                for section_name, content in self.sections.items()
                if section_name not in self._boilerplate_sections
            ]
        else:
            sections_to_include = list(self.sections.values())

        return "\n\n".join(sections_to_include)

    def get_sections(self) -> dict[str, str]:
        """
        Get all parsed sections.

        Returns:
            Dict mapping section names to content text
        """
        return self.sections.copy()

    def get_required_qualifications(self) -> list[str]:
        """
        Get required qualification items.

        Parses bullets from all required qualifications sections.

        Returns:
            List of requirement strings (parsed from bullets)
        """
        if not self.required_qualifications_sections:
            return []

        all_bullets = []
        for section_name in self.required_qualifications_sections:
            section_content = self.sections.get(section_name, "")
            all_bullets.extend(self._parse_bullets(section_content))
        return all_bullets

    def get_preferred_qualifications(self) -> list[str]:
        """
        Get preferred qualification items.

        Parses bullets from all preferred qualifications sections.

        Returns:
            List of preference strings (parsed from bullets)
        """
        if not self.preferred_qualifications_sections:
            return []

        all_bullets = []
        for section_name in self.preferred_qualifications_sections:
            section_content = self.sections.get(section_name, "")
            all_bullets.extend(self._parse_bullets(section_content))
        return all_bullets

    # =========================================================================
    # INTERNAL HELPER METHODS
    # =========================================================================

    def _parse_bullets(self, text: str) -> list[str]:
        """
        Parse markdown bullets (* or -) from text into list of strings.

        Args:
            text: Section content with markdown bullets

        Returns:
            List of bullet text (without bullet markers)
        """
        if not text:
            return []

        bullets = []
        lines = text.split("\n")

        for line in lines:
            line = line.strip()

            # Match bullet patterns: "* text" or "- text"
            match = re.match(r"^[\*\-]\s+(.+)$", line)
            if match:
                bullet_text = match.group(1).strip()
                if bullet_text:
                    bullets.append(bullet_text)

        return bullets
