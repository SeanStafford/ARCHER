"""
Job description parsing utilities for the Intake context.

Provides functions to parse markdown job descriptions into structured data.
This module has no knowledge of JobListing - it returns raw parsed data
that JobListing.from_text() uses to construct instances.

Pattern follows templating context: parser produces data, data structure consumes it.

Note: This module is actively under development and will evolve as more
job listing formats are encountered.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from archer.contexts.intake.normalizer import preprocess_job_markdown
from archer.contexts.intake.section_patterns import (
    AMBIGUOUS_QUALIFICATION_PATTERNS,
    FALLBACK_QUALIFICATION_PATTERNS,
    PREFERRED_QUALIFICATION_PATTERNS,
    REQUIRED_QUALIFICATION_PATTERNS,
    MarkdownHeaderPatterns,
    is_boilerplate_section,
    match_section_archetype,
)
from archer.utils.markdown import MarkdownTree, build_markdown_tree

# Known metadata field names (Title Case)
KNOWN_METADATA_FIELDS = {
    "Company",
    "Role",
    "Job ID",
    "Location",
    "Salary",
    "Source",
    "URL",
    "Focus",
    "Clearance",
    "Work Mode",
    "Date Posted",
}


@dataclass
class ParsedJobData:
    """
    Raw parsed job description data.

    This is the intermediate form between raw text and JobListing.
    JobListing.from_text() uses this to construct instances.
    """

    raw_text: str
    sections: dict[str, str]
    section_tree: Optional[MarkdownTree] = None
    required_qualifications_sections: list[str] = field(default_factory=list)
    preferred_qualifications_sections: list[str] = field(default_factory=list)
    section_archetypes: dict[str, str] = field(default_factory=dict)
    boilerplate_sections: set[str] = field(default_factory=set)
    metadata: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def extract_sections(text: str) -> tuple[dict[str, str], list[str]]:
    """
    Extract sections from markdown text.

    Sections identified by:
    - Bold markdown: **Section Name** or **Section Name:**
    - Hash headers: # Header, ## Header, ### Header, #### Header

    Text before the first section header is discarded with a warning.

    Args:
        text: Job description markdown (should be preprocessed first)

    Returns:
        Tuple of (sections dict, warnings list)
    """
    bold_pattern = MarkdownHeaderPatterns.BOLD_HEADER
    hash_pattern = MarkdownHeaderPatterns.HASH_HEADER

    sections = {}
    warnings = []
    current_section = None
    current_content = []
    preamble_content = []

    lines = text.split("\n")

    for line in lines:
        stripped = line.strip()

        # Try bold pattern first, then hash pattern
        bold_match = re.match(bold_pattern, stripped)
        hash_match = re.match(hash_pattern, stripped)

        if bold_match or hash_match:
            # Save previous section
            if current_section is None:
                # Warn about discarded preamble content
                preamble_text = "\n".join(preamble_content).strip()
                if preamble_text:
                    warnings.append(
                        f"Discarded preamble content before first heading: "
                        f"'{preamble_text[:80]}...'"
                        if len(preamble_text) > 80
                        else f"Discarded preamble content before first heading: '{preamble_text}'"
                    )
                preamble_content = []
            elif current_content:
                sections[current_section] = "\n".join(current_content).strip()
                current_content = []

            # Extract section name from whichever pattern matched
            if bold_match:
                current_section = bold_match.group(1).strip()
                remainder = stripped[bold_match.end() :].strip()
                if remainder:
                    current_content.append(remainder)
            else:
                current_section = hash_match.group(1).strip()
                # Hash headers don't have remainder on same line
        else:
            if current_section is None:
                preamble_content.append(line)
            else:
                current_content.append(line)

    if current_section is None and preamble_content:
        preamble_text = "\n".join(preamble_content).strip()
        if preamble_text:
            warnings.append(
                f"Discarded preamble content before first heading: '{preamble_text[:80]}...'"
                if len(preamble_text) > 80
                else f"Discarded preamble content before first heading: '{preamble_text}'"
            )
    elif current_section and current_content:
        sections[current_section] = "\n".join(current_content).strip()

    return sections, warnings


def identify_special_sections(sections: dict[str, str]) -> tuple[list[str], list[str]]:
    """
    Identify required and preferred qualification sections.

    Uses 3-pass matching logic:
    1. Strong patterns (REQUIRED/PREFERRED) - always match to their category
    2. Ambiguous patterns - assign based on what else exists (default to required)
    3. Fallback patterns - only if nothing else matched

    Args:
        sections: Dict of section name to content

    Returns:
        (required_section_names, preferred_section_names) - lists of matching section names
    """
    required = []
    preferred = []
    ambiguous = []

    # Pass 1: Strong patterns
    for section_name in sections:
        normalized = section_name.lower()

        # Check preferred FIRST (more specific, e.g., "nice if you have")
        is_preferred = False
        for pattern in PREFERRED_QUALIFICATION_PATTERNS:
            if re.search(pattern, normalized):
                preferred.append(section_name)
                is_preferred = True
                break

        # Only check required if not already matched as preferred
        if not is_preferred:
            for pattern in REQUIRED_QUALIFICATION_PATTERNS:
                if re.search(pattern, normalized):
                    required.append(section_name)
                    break

    # Pass 2: Ambiguous patterns (e.g., "Ideal Qualifications")
    for section_name in sections:
        if section_name not in required and section_name not in preferred:
            normalized = section_name.lower()
            for pattern in AMBIGUOUS_QUALIFICATION_PATTERNS:
                if re.search(pattern, normalized):
                    ambiguous.append(section_name)
                    break

    # Resolve ambiguous: fill whichever category is empty
    if ambiguous:
        if not required:
            # Required is empty, ambiguous fills it
            required.extend(ambiguous)
        elif not preferred:
            # Preferred is empty, ambiguous fills it
            preferred.extend(ambiguous)
        else:
            # Both exist, default ambiguous to required
            required.extend(ambiguous)

    # Pass 3: Fallback (only if nothing matched)
    if not required and not preferred:
        for section_name in sections:
            normalized = section_name.lower().strip()
            for pattern in FALLBACK_QUALIFICATION_PATTERNS:
                if re.search(pattern, normalized):
                    required.append(section_name)
                    break
            if required:  # Stop after first fallback match
                break

    return required, preferred


def categorize_sections(sections: dict[str, str]) -> dict[str, str]:
    """
    Assign archetype to each section.

    Args:
        sections: Dict of section name to content

    Returns:
        Dict mapping section name to archetype string
    """
    archetypes = {}

    for section_name in sections:
        archetype = match_section_archetype(section_name)
        if archetype:
            archetypes[section_name] = archetype
        else:
            archetypes[section_name] = "other"

    return archetypes


def detect_boilerplate_sections(sections: dict[str, str]) -> set[str]:
    """
    Identify boilerplate sections using known patterns.

    Args:
        sections: Dict of section name to content

    Returns:
        Set of section names marked as boilerplate
    """
    boilerplate = set()

    for section_name in sections:
        if is_boilerplate_section(section_name):
            boilerplate.add(section_name)

    return boilerplate


def parse_job_text(text: str) -> ParsedJobData:
    """
    Parse job description markdown into structured data.

    This is the main parsing function. It returns raw parsed data,
    not a JobListing. Use JobListing.from_text() to get a JobListing.

    Args:
        text: Raw job description markdown

    Returns:
        ParsedJobData with all extracted information
    """
    # Normalize markdown (flatten nested subsection headers)
    normalized_text = preprocess_job_markdown(text)

    # Extract sections from normalized markdown
    sections, warnings = extract_sections(normalized_text)

    # Identify required/preferred qualification sections
    required_qual, preferred_qual = identify_special_sections(sections)

    # Categorize sections by archetype
    section_archetypes = categorize_sections(sections)

    # Detect boilerplate sections
    boilerplate_sections = detect_boilerplate_sections(sections)

    return ParsedJobData(
        raw_text=text,
        sections=sections,
        required_qualifications_sections=required_qual,
        preferred_qualifications_sections=preferred_qual,
        section_archetypes=section_archetypes,
        boilerplate_sections=boilerplate_sections,
        warnings=warnings,
    )


def parse_job_file(file_path: Path) -> ParsedJobData:
    """
    Parse job description from file.

    Args:
        file_path: Path to markdown file

    Returns:
        ParsedJobData with all extracted information
    """
    text = file_path.read_text()
    return parse_job_text(text)


def extract_metadata(tree: MarkdownTree) -> dict[str, str]:
    """
    Extract metadata key-value pairs from a MarkdownTree.

    Looks for a `## Metadata` section and extracts its `###` children as
    key-value pairs. Falls back to scanning top-level `###` nodes for
    legacy files without a `## Metadata` wrapper.

    Args:
        tree: Parsed markdown tree

    Returns:
        Dict mapping field names to values (e.g., {"Company": "Acme Corp"})
    """
    metadata = {}

    # Primary: look for a ## Metadata section (case-insensitive)
    metadata_node = None
    for sub in tree.subsections:
        if sub.title.lower() == "metadata":
            metadata_node = sub
            break

    if metadata_node is not None:
        for child in metadata_node.subsections:
            if child.title and child.content:
                metadata[child.title] = child.content.strip()
        return metadata

    # Fallback: scan top-level ### nodes for known metadata fields (case-insensitive)
    canonical_names = {name.lower(): name for name in KNOWN_METADATA_FIELDS}
    for sub in tree.subsections:
        lower_title = sub.title.lower()
        # Check direct match first, then legacy aliases
        canonical = canonical_names.get(lower_title)
        if canonical and sub.content:
            metadata[canonical] = sub.content.strip()

    return metadata


def _flatten_tree_to_sections(tree: MarkdownTree) -> tuple[dict[str, str], list[str]]:
    """
    Flatten a MarkdownTree to a dict of section name -> content.

    Recursively collects all sections. For sections with subsections,
    content includes both the section's own content and all subsection content.
    Skips the Metadata section (handled separately by extract_metadata).

    Returns:
        Tuple of (sections dict, warnings list)
    """
    sections = {}
    warnings = []

    def collect(node: MarkdownTree, prefix: str = "") -> None:
        if node.title:
            # Collect this section's content plus all nested content
            all_content = [node.content] if node.content else []
            for sub in node.subsections:
                if sub.content:
                    all_content.append(sub.content)
            sections[node.title] = "\n".join(all_content)

        # Also add subsections as their own entries
        for sub in node.subsections:
            collect(sub)

    for sub in tree.subsections:
        # Skip the Metadata section (handled by extract_metadata)
        if sub.title.lower() == "metadata":
            continue
        collect(sub)

    # Warn about discarded preamble content
    if tree.content:
        preamble = tree.content.strip()
        if preamble:
            warnings.append(
                f"Discarded preamble content before first heading: '{preamble[:80]}...'"
                if len(preamble) > 80
                else f"Discarded preamble content before first heading: '{preamble}'"
            )

    return sections, warnings


def parse_job_structured_markdown(text: str) -> ParsedJobData:
    """
    Parse job description using hierarchical markdown parsing.

    Use this for job descriptions with proper markdown hierarchy (## and ###).
    For job descriptions with bold headers (**Header:**), use parse_job_text().

    Args:
        text: Job description markdown with ## and ### headers

    Returns:
        ParsedJobData with section_tree populated
    """
    # Build hierarchical tree
    tree = build_markdown_tree(text)

    # Extract metadata from tree
    metadata = extract_metadata(tree)

    # Flatten to dict for backwards compatibility
    sections, warnings = _flatten_tree_to_sections(tree)

    # Identify required/preferred qualification sections
    required_qual, preferred_qual = identify_special_sections(sections)

    # Categorize sections by archetype
    section_archetypes = categorize_sections(sections)

    # Detect boilerplate sections
    boilerplate_sections = detect_boilerplate_sections(sections)

    return ParsedJobData(
        raw_text=text,
        sections=sections,
        section_tree=tree,
        required_qualifications_sections=required_qual,
        preferred_qualifications_sections=preferred_qual,
        section_archetypes=section_archetypes,
        boilerplate_sections=boilerplate_sections,
        metadata=metadata,
        warnings=warnings,
    )
