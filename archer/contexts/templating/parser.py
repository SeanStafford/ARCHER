"""
LaTeX Resume Parser

Extracts structured data from LaTeX resume files.
Functions in this module are used by ResumeDocument.from_tex() to convert
.tex files into structured format.
"""

import re
from typing import Dict, List, Tuple


def extract_latex_fields(content: str) -> Dict[str, str]:
    """
    Extract all \\renewcommand{<field>}{<value>} patterns from LaTeX content.

    Args:
        content: LaTeX file content as string

    Returns:
        Dict mapping field names to their values (e.g., {"brand": "ML Engineer | Physicist"})
    """
    fields = {}

    # Pattern matches \renewcommand{\fieldname}{
    pattern = r"\\renewcommand\{\\([^}]+)\}\{"

    for match in re.finditer(pattern, content):
        # find the match to get field name and starting position
        field_name = match.group(1)
        start_pos = match.end()

        # Count braces to find the matching closing brace
        brace_count = 1
        pos = start_pos

        while pos < len(content) and brace_count > 0:
            # Handle escaped backslashes
            if content[pos] == "\\":
                pos += 2
                continue
            elif content[pos] == "{":
                brace_count += 1
            elif content[pos] == "}":
                brace_count -= 1
            pos += 1

        if brace_count == 0:
            field_value = content[start_pos : pos - 1]
            fields[field_name] = field_value
        else:
            # Unmatched braces, skip this field
            continue

    return fields


def _clean_section_name(raw_name: str) -> str:
    """
    Clean LaTeX formatting commands and escapes from section name.

    Args:
        raw_name: Raw section name with LaTeX formatting

    Returns:
        Cleaned section name with formatting removed
    """
    cleaned = raw_name

    # First, remove spacing/positioning commands entirely (including their arguments)
    spacing_commands = ["hspace", "vspace", "color", "colorbox"]
    for cmd in spacing_commands:
        cleaned = re.sub(rf"\\{cmd}\{{[^}}]*\}}", "", cleaned)

    # Then unwrap formatting commands (keep their content)
    # Pattern matches: \command{content} and keeps just content
    max_iterations = 10  # Prevent infinite loop
    for _ in range(max_iterations):
        before = cleaned
        cleaned = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", cleaned)
        if cleaned == before:
            break

    # Remove any remaining standalone braces (e.g., from \color{red}{Content})
    cleaned = re.sub(r"^\{([^}]*)\}$", r"\1", cleaned)
    cleaned = re.sub(r"\{([^}]*)\}", r"\1", cleaned)

    # Replace LaTeX escapes
    cleaned = cleaned.replace(r"\&", "&")
    cleaned = cleaned.replace(r"\%", "%")
    cleaned = cleaned.replace(r"\_", "_")
    cleaned = cleaned.replace(r"\$", "$")

    # Strip whitespace
    return cleaned.strip()


def extract_sections(content: str) -> List[str]:
    """
    Extract all \\section*{VALUE} and \\section{VALUE} names from LaTeX content.

    Cleans LaTeX formatting commands and escapes from section names.
    Handles nested braces correctly.

    Args:
        content: LaTeX file content as string

    Returns:
        List of cleaned section names (e.g., ["Core Skills", "Experience", ...])
    """
    sections = []

    # Pattern matches \section or \section* followed by {
    pattern = r"\\section\*?\{"

    for match in re.finditer(pattern, content):
        start_pos = match.end()

        # Count braces to find the matching closing brace
        brace_count = 1
        pos = start_pos

        while pos < len(content) and brace_count > 0:
            if content[pos] == "\\":
                # Skip escaped characters
                pos += 2
                continue
            elif content[pos] == "{":
                brace_count += 1
            elif content[pos] == "}":
                brace_count -= 1
            pos += 1

        if brace_count == 0:
            section_name = content[start_pos : pos - 1]
            cleaned_name = _clean_section_name(section_name)
            sections.append(cleaned_name)

    return sections


def extract_all_sections_with_content(content: str) -> List[Tuple[str, str]]:
    """
    Extract all sections with their content from LaTeX document.

    For each section, extracts:
    - Cleaned section name
    - Raw LaTeX content from after section header until next section or end of document

    Args:
        content: LaTeX file content as string

    Returns:
        List of (section_name, section_content) tuples

    Example:
        [
            ("Core Skills", "\\begin{itemizeLL}...\\end{itemizeLL}"),
            ("Experience", "\\begin{itemizeAcademic}..."),
            ...
        ]
    """
    sections_with_content = []

    # Pattern matches \section or \section* followed by {
    pattern = r"\\section\*?\{"

    # Find all section positions
    section_positions = []
    for match in re.finditer(pattern, content):
        start_pos = match.end()

        # Count braces to find the matching closing brace for section name
        brace_count = 1
        pos = start_pos

        while pos < len(content) and brace_count > 0:
            if content[pos] == "\\":
                pos += 2
                continue
            elif content[pos] == "{":
                brace_count += 1
            elif content[pos] == "}":
                brace_count -= 1
            pos += 1

        if brace_count == 0:
            section_name = content[start_pos : pos - 1]
            cleaned_name = _clean_section_name(section_name)
            content_start = pos  # Content starts after closing brace

            section_positions.append((cleaned_name, content_start))

    # Extract content between sections
    for i, (name, content_start) in enumerate(section_positions):
        # Content ends at start of next section, or end of document
        if i + 1 < len(section_positions):
            content_end = section_positions[i + 1][1] - len(r"\section*{")
            # Back up to before the \section command
            # Find the actual start of \section
            search_start = max(0, content_end - 100)
            search_region = content[search_start:content_end + 50]
            section_match = re.search(r"\\section\*?\{", search_region)
            if section_match:
                content_end = search_start + section_match.start()
        else:
            content_end = len(content)

        section_content = content[content_start:content_end].strip()
        sections_with_content.append((name, section_content))

    return sections_with_content


def extract_section_content(content: str, section_name: str, case_sensitive: bool = False) -> str:
    """
    Extract content for a specific section by name.

    Args:
        content: LaTeX file content as string
        section_name: Name of section to find (will be matched after cleaning)
        case_sensitive: Whether to match section name case-sensitively

    Returns:
        Section content as string, or empty string if section not found

    Example:
        content = extract_section_content(tex_content, "Core Skills")
        # Returns LaTeX content between "Core Skills" section and next section
    """
    sections = extract_all_sections_with_content(content)

    if case_sensitive:
        for name, sect_content in sections:
            if name == section_name:
                return sect_content
    else:
        section_name_lower = section_name.lower()
        for name, sect_content in sections:
            if name.lower() == section_name_lower:
                return sect_content

    return ""
