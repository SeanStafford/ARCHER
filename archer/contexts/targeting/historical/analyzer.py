"""
Resume Archive Pattern Analyzer

Analyzes statistical patterns in historical resume archive using structured data.

Uses ResumeDocument and ResumeDocumentArchive from the Templating context to
operate on structured resume data rather than raw LaTeX. This separation respects
context boundaries and enables powerful text-based analysis capabilities.
"""

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set

from archer.contexts.templating import ResumeDocument, ResumeDocumentArchive
from archer.utils.report_formatter import Column, TableFormatter

# Default exclusion list: personality/fun sections
DEFAULT_EXCLUDED_SECTIONS = [
    "Passions",
    "Alias Array",
    "Alliterative Aliases",
    "Proficiency Pseudonyms",
    "Marketable Monikers",
    "Certifiable Pseudonyms",
    "Alliterative Alias",
    "2 Truths and a Lie",
]


class ResumeArchiveAnalyzer:
    """
    Analyzes patterns in historical resume archive.

    Uses structured ResumeDocument instances (from Templating context) rather than
    parsing raw LaTeX. Supports both markdown and plaintext modes for different
    analysis needs.

    Attributes:
        archive_path: Path to resume archive directory
        mode: Content formatting mode ("markdown" or "plaintext")
        documents: List of loaded ResumeDocument instances
    """

    def __init__(self, archive_path: Path, mode: str = "plaintext"):
        """
        Initialize analyzer with archive directory path.

        Args:
            archive_path: Path to resume archive directory
            mode: Content formatting mode - "markdown" or "plaintext" (default: plaintext)
                  "plaintext" recommended for statistical analysis and search
                  "markdown" preserves inline formatting for LLM consumption
        """
        self.archive_path = archive_path
        self.mode = mode
        self._archive = ResumeDocumentArchive(archive_path)
        self.documents: List[ResumeDocument] = []

    def load_archive(self, load_mode: str = "available") -> int:
        """
        Load resume documents using ResumeDocumentArchive.

        Args:
            load_mode: Loading strategy
                - "available": Load only pre-converted YAMLs from structured/ (fast, recommended)
                - "all": Load all .tex files, converting if needed (slow, fallback)

        Returns:
            Number of resumes successfully loaded

        Note:
            Uses ResumeDocumentArchive.load() which handles errors gracefully
            and emits warnings for failed files.
        """
        self.documents = self._archive.load(mode=load_mode, format_mode=self.mode)
        return len(self.documents)

    def get_resume_count(self) -> int:
        """
        Get number of resumes currently loaded.

        Returns:
            Count of loaded resumes
        """
        return len(self.documents)

    # ========================================================================
    # Section Analysis Methods
    # ========================================================================

    def section_prevalence(self) -> Dict[str, int]:
        """
        Count how often each section name appears across all resumes.

        Returns:
            Dict mapping section name → count of resumes containing it
            Sorted by prevalence (most common first)
        """
        if not self.documents:
            raise ValueError("No resumes loaded. Call load_archive() first.")

        counts = defaultdict(int)

        for doc in self.documents:
            # Track unique section names per resume (don't double-count)
            unique_sections = {section.name for section in doc.sections}

            for section_name in unique_sections:
                counts[section_name] += 1

        # Sort by prevalence (descending)
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def section_type_distribution(self) -> Dict[str, int]:
        """
        Count how often each section type appears across all resumes.

        Unlike section_prevalence (which counts by name like "Core Skills"),
        this counts by type (like "skill_list_caps", "work_history").

        Returns:
            Dict mapping section type → total count across all resumes
            Sorted by frequency (most common first)
        """
        if not self.documents:
            raise ValueError("No resumes loaded. Call load_archive() first.")

        counts = defaultdict(int)

        for doc in self.documents:
            for section in doc.sections:
                counts[section.section_type] += 1

        # Sort by frequency (descending)
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def section_co_occurrence(self) -> Dict[str, Dict[str, int]]:
        """
        Analyze which sections appear together in resumes.

        Returns:
            Nested dict: section → {co-occurring section → count}
        """
        if not self.documents:
            raise ValueError("No resumes loaded. Call load_archive() first.")

        co_occurrence = defaultdict(lambda: defaultdict(int))

        for doc in self.documents:
            section_names = [s.name for s in doc.sections]

            # For each section, count all other sections in same resume
            for i, section_a in enumerate(section_names):
                for j, section_b in enumerate(section_names):
                    if i != j:  # Don't count self
                        co_occurrence[section_a][section_b] += 1

        # Convert defaultdict to regular dict and sort inner dicts
        return {
            section: dict(sorted(co_occur.items(), key=lambda x: x[1], reverse=True))
            for section, co_occur in co_occurrence.items()
        }

    # ========================================================================
    # Property-Based Analysis Methods
    # ========================================================================

    def professional_title_distribution(self) -> Dict[str, int]:
        """
        Show distribution of professional titles across resumes.

        Returns:
            Dict mapping title → count of resumes with that title
            Sorted by frequency (most common first)
        """
        if not self.documents:
            raise ValueError("No resumes loaded. Call load_archive() first.")

        counts = defaultdict(int)

        for doc in self.documents:
            if doc.professional_title:
                # Normalize whitespace for consistent counting
                normalized = " ".join(doc.professional_title.split())
                counts[normalized] += 1

        # Sort by frequency (descending)
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def date_distribution(self) -> Dict[str, int]:
        """
        Show distribution of resume dates.

        Returns:
            Dict mapping date → count of resumes with that date
            Sorted by frequency (most common first)
        """
        if not self.documents:
            raise ValueError("No resumes loaded. Call load_archive() first.")

        counts = defaultdict(int)

        for doc in self.documents:
            if doc.date:
                counts[doc.date] += 1

        # Sort by frequency (descending)
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def title_component_frequency(self) -> Dict[str, int]:
        """
        Count frequency of individual title components.

        Splits compound titles on " | " separator and counts each component separately.

        Returns:
            Dict mapping title component → count of resumes containing it
            Sorted by frequency (most common first)
        """
        if not self.documents:
            raise ValueError("No resumes loaded. Call load_archive() first.")

        counts = defaultdict(int)

        for doc in self.documents:
            if doc.professional_title:
                # Split on " | " and normalize whitespace
                components = [c.strip() for c in doc.professional_title.split("|")]

                # Count each unique component once per resume
                for component in set(components):
                    if component:
                        counts[component] += 1

        # Sort by frequency (descending)
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def title_component_co_occurrence(self) -> Dict[str, Dict[str, int]]:
        """
        Analyze which title components appear together.

        For compound titles like "Machine Learning Engineer | Physicist",
        tracks how often each component appears with other components.

        Returns:
            Nested dict: title component → {co-occurring component → count}
        """
        if not self.documents:
            raise ValueError("No resumes loaded. Call load_archive() first.")

        co_occurrence = defaultdict(lambda: defaultdict(int))

        for doc in self.documents:
            if doc.professional_title:
                # Split on " | " and normalize whitespace
                components = [c.strip() for c in doc.professional_title.split("|")]
                components = [c for c in components if c]

                # For each component, count all other components
                for i, comp_a in enumerate(components):
                    for j, comp_b in enumerate(components):
                        if i != j:  # Don't count self
                            co_occurrence[comp_a][comp_b] += 1

        # Convert defaultdict to regular dict and sort inner dicts
        return {
            component: dict(sorted(co_occur.items(), key=lambda x: x[1], reverse=True))
            for component, co_occur in co_occurrence.items()
        }

    # ========================================================================
    # Hierarchical Content Analysis
    # ========================================================================

    def count_work_experiences(self) -> Dict[str, int]:
        """
        Count total work experiences per resume.

        Work experiences are nested inside work_history sections.

        Returns:
            Dict mapping filename → count of work experiences
        """
        if not self.documents:
            raise ValueError("No resumes loaded. Call load_archive() first.")

        counts = {}

        for doc in self.documents:
            count = sum(
                len(section.data.get("subsections", []))
                for section in doc.sections
                if section.section_type == "work_history"
            )
            counts[doc.filename] = count

        return counts

    def extract_all_skills(
        self, exclude_sections: List[str] = DEFAULT_EXCLUDED_SECTIONS
    ) -> Set[str]:
        """
        Extract all unique skills across all resumes.

        Handles both flat skill lists and categorized skills.

        Args:
            exclude_sections: Section names to exclude from skill extraction.
                If None, defaults to personality/fun sections.
                Pass empty list [] to disable exclusions.

        Returns:
            Set of unique skill strings (plaintext format)
        """
        if not self.documents:
            raise ValueError("No resumes loaded. Call load_archive() first.")

        exclude_set = set(exclude_sections)
        skills = set()

        for doc in self.documents:
            for section in doc.sections:
                # Skip excluded sections
                if section.name in exclude_set:
                    continue

                # Flat skill lists
                if section.section_type in ("skill_list_caps", "skill_list_pipes"):
                    skills.update(section.data.get("items", []))

                # Categorized skills
                elif section.section_type == "skill_categories":
                    for category in section.data.get("subsections", []):
                        skills.update(category.get("items", []))

        return skills

    def skill_frequency(
        self, exclude_sections: List[str] = DEFAULT_EXCLUDED_SECTIONS
    ) -> Dict[str, int]:
        """
        Count how often each skill appears across all resumes.

        Args:
            exclude_sections: Section names to exclude from skill extraction.
                If None, defaults to personality/fun sections.
                Pass empty list [] to disable exclusions.

        Returns:
            Dict mapping skill → count of resumes containing it
            Sorted by frequency (most common first)
        """
        if not self.documents:
            raise ValueError("No resumes loaded. Call load_archive() first.")

        exclude_set = set(exclude_sections)
        counts = defaultdict(int)

        for doc in self.documents:
            # Get unique skills per resume (don't double-count)
            skills_in_doc = set()

            for section in doc.sections:
                # Skip excluded sections
                if section.name in exclude_set:
                    continue

                if section.section_type in ("skill_list_caps", "skill_list_pipes"):
                    skills_in_doc.update(section.data.get("items", []))
                elif section.section_type == "skill_categories":
                    for category in section.data.get("subsections", []):
                        skills_in_doc.update(category.get("items", []))

            # Count each unique skill once per resume
            for skill in skills_in_doc:
                counts[skill] += 1

        # Sort by frequency (descending)
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    # ========================================================================
    # Text Search Methods
    # ========================================================================

    def search_field(
        self,
        field_name: str,
        patterns: List[str],
        return_matches: bool = False,
        case_sensitive: bool = False,
    ) -> Dict[str, any]:
        """
        Search for patterns in a specific document field.

        Args:
            field_name: Field to search - one of:
                - "professional_title"
                - "name"
                - "date"
                - "filename"
            patterns: List of patterns to search for
            return_matches: If True, return matching filenames; if False, return counts
            case_sensitive: Whether to match case exactly (default: False)

        Returns:
            If return_matches=False: Dict mapping pattern → count of matching resumes
            If return_matches=True: Dict mapping pattern → list of matching filenames

        Raises:
            ValueError: If field_name is not a valid field
        """
        if not self.documents:
            raise ValueError("No resumes loaded. Call load_archive() first.")

        # Validate field name
        valid_fields = ["professional_title", "name", "date", "filename"]
        if field_name not in valid_fields:
            raise ValueError(
                f"Invalid field_name '{field_name}'. Must be one of: {', '.join(valid_fields)}"
            )

        results = {}

        for pattern in patterns:
            matching_filenames = []

            for doc in self.documents:
                # Get field value
                field_value = getattr(doc, field_name, None)

                if field_value is None:
                    continue

                # Search for pattern
                if case_sensitive:
                    if pattern in field_value:
                        matching_filenames.append(doc.filename)
                else:
                    if pattern.lower() in field_value.lower():
                        matching_filenames.append(doc.filename)

            # Store results based on return_matches
            if return_matches:
                results[pattern] = matching_filenames
            else:
                results[pattern] = len(matching_filenames)

        return results

    def search_resumes(self, keyword: str, case_sensitive: bool = False) -> List[str]:
        """
        Find resumes containing a keyword.

        Uses plaintext/markdown content from ResumeDocument.get_all_text().

        Args:
            keyword: Keyword to search for
            case_sensitive: Whether to match case exactly (default: False)

        Returns:
            List of filenames containing the keyword
        """
        if not self.documents:
            raise ValueError("No resumes loaded. Call load_archive() first.")

        matches = []

        for doc in self.documents:
            text = doc.get_all_text()

            if case_sensitive:
                if keyword in text:
                    matches.append(doc.filename)
            else:
                if keyword.lower() in text.lower():
                    matches.append(doc.filename)

        return matches

    def keyword_frequency(self, keywords: List[str]) -> Dict[str, int]:
        """
        Count how many resumes contain each keyword.

        Args:
            keywords: List of keywords to search for

        Returns:
            Dict mapping keyword → count of resumes containing it
            Sorted by frequency (most common first)
        """
        if not self.documents:
            raise ValueError("No resumes loaded. Call load_archive() first.")

        counts = {}

        for keyword in keywords:
            count = sum(
                1 for doc in self.documents if keyword.lower() in doc.get_all_text().lower()
            )
            counts[keyword] = count

        # Sort by frequency (descending)
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    # ========================================================================
    # Grouping Methods
    # ========================================================================

    def extract_job_type_from_filename(self, doc: ResumeDocument) -> str:
        """
        Extract job type from resume filename.

        Assumes naming convention: ResYYYYMM_JobTitle_Company

        Args:
            doc: ResumeDocument instance

        Returns:
            Job type extracted from filename
            Returns "Unknown" if pattern doesn't match
        """
        filename = doc.filename

        # Pattern: ResYYYYMM_<job_type>_<company>
        # Split on underscore, skip first part (ResYYYYMM)
        parts = filename.split("_")

        if len(parts) < 3 or not parts[0].startswith("Res"):
            return "Unknown"

        # Everything between date and last part (company) is job type
        job_type_parts = parts[1:-1]
        return "_".join(job_type_parts)

    def group_resumes_by_pattern(self, extract_key: callable) -> Dict[str, List[ResumeDocument]]:
        """
        Group resumes by a custom extraction pattern.

        Generic grouping function for flexible analysis.

        Args:
            extract_key: Function that takes ResumeDocument and returns grouping key

        Returns:
            Dict mapping keys → lists of resumes with that key
        """
        if not self.documents:
            raise ValueError("No resumes loaded. Call load_archive() first.")

        groups = defaultdict(list)

        for doc in self.documents:
            key = extract_key(doc)
            if key:  # Skip if key is None or empty
                groups[key].append(doc)

        return dict(groups)

    # ========================================================================
    # Report Formatting Methods
    # ========================================================================

    def format_section_prevalence_report(self) -> str:
        """
        Generate formatted report for section prevalence analysis.

        Returns:
            Formatted string report
        """
        prevalence = self.section_prevalence()
        total = self.get_resume_count()

        formatter = TableFormatter(
            columns=[
                Column("Section Name", 50, "<"),
                Column("Count", 10, "<"),
                Column("% Resumes", 15, "<"),
            ],
            total_width=100,
        )

        formatter.add_section_header("SECTION PREVALENCE ACROSS RESUME ARCHIVE")
        formatter.add_text(f"Analyzed {total} resumes from {self.archive_path}")
        formatter.add_blank_line()
        formatter.add_table_header()
        formatter.add_separator("-")

        for section_name, count in prevalence.items():
            percent = (count / total) * 100
            formatter.add_row([section_name, count, f"{percent:>13.1f}%"])

        formatter.add_blank_line()
        formatter.add_text(f"Total unique sections: {len(prevalence)}")
        formatter.add_blank_line()

        return formatter.render()

    def format_section_type_report(self) -> str:
        """
        Generate formatted report for section type distribution.

        Returns:
            Formatted string report
        """
        distribution = self.section_type_distribution()
        total = self.get_resume_count()

        formatter = TableFormatter(
            columns=[Column("Section Type", 50, "<"), Column("Count", 10, "<")],
            total_width=100,
        )

        formatter.add_section_header("SECTION TYPE DISTRIBUTION")
        formatter.add_text(f"Analyzed {total} resumes from {self.archive_path}")
        formatter.add_blank_line()
        formatter.add_table_header()
        formatter.add_separator("-")

        for section_type, count in distribution.items():
            formatter.add_row([section_type, count])

        formatter.add_blank_line()
        formatter.add_text(f"Total unique types: {len(distribution)}")
        formatter.add_blank_line()

        return formatter.render()

    def format_professional_title_report(self) -> str:
        """
        Generate formatted report for professional title distribution.

        Returns:
            Formatted string report
        """
        distribution = self.professional_title_distribution()
        total = self.get_resume_count()

        formatter = TableFormatter(
            columns=[
                Column("Title", 60, "<"),
                Column("Count", 10, "<"),
                Column("% Resumes", 15, "<"),
            ],
            total_width=100,
        )

        formatter.add_section_header("PROFESSIONAL TITLE DISTRIBUTION")
        formatter.add_text(f"Analyzed {total} resumes from {self.archive_path}")
        formatter.add_blank_line()
        formatter.add_table_header()
        formatter.add_separator("-")

        for title, count in distribution.items():
            percent = (count / total) * 100
            # Truncate long titles
            display_title = title if len(title) <= 58 else title[:55] + "..."
            formatter.add_row([display_title, count, f"{percent:>13.1f}%"])

        formatter.add_blank_line()
        formatter.add_text(f"Total unique titles: {len(distribution)}")
        formatter.add_blank_line()

        return formatter.render()

    def format_title_component_report(self) -> str:
        """
        Generate formatted report for title component frequency.

        Returns:
            Formatted string report
        """
        frequency = self.title_component_frequency()
        total = self.get_resume_count()

        formatter = TableFormatter(
            columns=[
                Column("Component", 60, "<"),
                Column("Count", 10, "<"),
                Column("% Resumes", 15, "<"),
            ],
            total_width=100,
        )

        formatter.add_section_header("TITLE COMPONENT FREQUENCY")
        formatter.add_text(f"Analyzed {total} resumes from {self.archive_path}")
        formatter.add_blank_line()
        formatter.add_table_header()
        formatter.add_separator("-")

        for component, count in frequency.items():
            percent = (count / total) * 100
            # Truncate long components
            display_component = component if len(component) <= 58 else component[:55] + "..."
            formatter.add_row([display_component, count, f"{percent:>13.1f}%"])

        formatter.add_blank_line()
        formatter.add_text(f"Total unique components: {len(frequency)}")
        formatter.add_blank_line()

        return formatter.render()

    def format_title_component_co_occurrence_report(self, component: Optional[str] = None) -> str:
        """
        Generate formatted report for title component co-occurrence.

        Args:
            component: Specific component to analyze (if None, shows top 5 components)

        Returns:
            Formatted string report
        """
        co_occur = self.title_component_co_occurrence()

        if component:
            # Single component report
            formatter = TableFormatter(
                columns=[Column("Co-occurring Component", 60, "<"), Column("Count", 10, "<")],
                total_width=100,
            )

            formatter.add_section_header(f"TITLE COMPONENT CO-OCCURRENCE: {component}")
            formatter.add_text(
                f"Analyzed {self.get_resume_count()} resumes from {self.archive_path}"
            )
            formatter.add_blank_line()

            if component not in co_occur:
                formatter.add_text(f"Component '{component}' not found in any titles.")
                formatter.add_blank_line()
                return formatter.render()

            formatter.add_table_header()
            formatter.add_separator("-")

            for other_component, count in co_occur[component].items():
                display_comp = (
                    other_component if len(other_component) <= 58 else other_component[:55] + "..."
                )
                formatter.add_row([display_comp, count])

            formatter.add_blank_line()
            return formatter.render()

        else:
            # Top 5 components report
            formatter = TableFormatter(columns=[], total_width=100)

            formatter.add_section_header("TITLE COMPONENT CO-OCCURRENCE (Top 5 Components)")
            formatter.add_text(
                f"Analyzed {self.get_resume_count()} resumes from {self.archive_path}"
            )
            formatter.add_blank_line()

            # Get top 5 components by frequency
            freq = self.title_component_frequency()
            top_components = list(freq.keys())[:5]

            for comp in top_components:
                formatter.add_blank_line()
                formatter.add_text(f"{comp}:")
                formatter.add_separator("-")
                if comp in co_occur:
                    for other_comp, count in list(co_occur[comp].items())[:10]:
                        display_comp = (
                            other_comp if len(other_comp) <= 56 else other_comp[:53] + "..."
                        )
                        formatter.add_text(f"  {display_comp:<58} {count:<10}")

            formatter.add_blank_line()
            return formatter.render()

    def format_skill_frequency_report(
        self, top_n: int = 20, exclude_sections: List[str] = DEFAULT_EXCLUDED_SECTIONS
    ) -> str:
        """
        Generate formatted report for skill frequency analysis.

        Args:
            top_n: Number of top skills to include (default: 20)
            exclude_sections: Section names to exclude from skill extraction.
                If None, defaults to personality/fun sections.
                Pass empty list [] to disable exclusions.

        Returns:
            Formatted string report
        """
        frequency = self.skill_frequency(exclude_sections=exclude_sections)
        total = self.get_resume_count()

        # Get top N skills
        top_skills = dict(list(frequency.items())[:top_n])

        formatter = TableFormatter(
            columns=[
                Column("Skill", 50, "<"),
                Column("Count", 10, "<"),
                Column("% Resumes", 15, "<"),
            ],
            total_width=100,
        )

        formatter.add_section_header(f"SKILL FREQUENCY (Top {top_n})")
        formatter.add_text(f"Analyzed {total} resumes from {self.archive_path}")
        formatter.add_blank_line()
        formatter.add_table_header()
        formatter.add_separator("-")

        for skill, count in top_skills.items():
            percent = (count / total) * 100
            # Truncate long skills
            display_skill = skill if len(skill) <= 48 else skill[:45] + "..."
            formatter.add_row([display_skill, count, f"{percent:>13.1f}%"])

        formatter.add_blank_line()
        formatter.add_text(f"Total unique skills: {len(frequency)}")
        formatter.add_blank_line()

        return formatter.render()
