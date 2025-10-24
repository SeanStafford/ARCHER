"""
Resume Pattern Analysis Utilities

Analyzes keyword frequency patterns across LaTeX resume files to inform
template structure and understand common variations.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

from archer.utils.text_processing import truncate_display


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
    Extract all \\section*{VALUE} and \\section{VALUE} patterns from LaTeX content.

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


def enumerate_field_values(resume_dir):
    """
    Enumerate all unique values for each \\renewcommand field across all resumes.

    Args:
        resume_dir: Directory containing .tex resume files

    Returns:
        Dict mapping field names to dicts of {value: count}
        Example: {"brand": {"ML Engineer | Physicist": 15, "AI Engineer": 5, ...}}
    """
    tex_files = sorted(resume_dir.glob("*.tex"))

    if not tex_files:
        raise ValueError(f"No .tex files found in {resume_dir}")

    field_values = {}

    for tex_file in tex_files:
        content = tex_file.read_text(encoding="utf-8")
        fields = extract_latex_fields(content)

        for field_name, field_value in fields.items():
            if field_name not in field_values:
                field_values[field_name] = {}

            # Clean up value (strip whitespace, normalize)
            cleaned_value = field_value.strip()

            if cleaned_value not in field_values[field_name]:
                field_values[field_name][cleaned_value] = 0
            field_values[field_name][cleaned_value] += 1

    return field_values


def enumerate_section_values(resume_dir: Path) -> Dict[str, int]:
    """
    Enumerate all unique section names and count how many resumes contain each.

    Groups section names case-insensitively, but preserves original case for display.

    Args:
        resume_dir: Directory containing .tex resume files

    Returns:
        Dict mapping section names to resume count
        Example: {"Core Skills": 57, "Experience": 57, "HPC Highlights": 4, ...}
    """
    tex_files = sorted(resume_dir.glob("*.tex"))

    if not tex_files:
        raise ValueError(f"No .tex files found in {resume_dir}")

    section_counts = {}
    section_normalized_map = {}  # normalized_key -> canonical_display_name

    for tex_file in tex_files:
        content = tex_file.read_text(encoding="utf-8")
        sections = extract_sections(content)  # Already cleaned of LaTeX formatting

        # Track unique sections per resume (don't count duplicates within same resume)
        unique_sections = set(sections)

        for section in unique_sections:
            # Normalize for case-insensitive grouping
            normalized = section.lower()

            if normalized not in section_normalized_map:
                # First occurrence - use this as canonical display version
                section_normalized_map[normalized] = section
                section_counts[section] = 0

            # Always use the canonical display version for counting
            display_name = section_normalized_map[normalized]
            section_counts[display_name] += 1

    return section_counts


def count_pattern_matches(text: str, pattern: str, is_regex: bool = False) -> int:
    """
    Count occurrences of a pattern in text, supporting both exact and regex matching.

    Args:
        text: Text to search in
        pattern: Pattern to search for
        is_regex: If True, treat pattern as regex; if False, use exact substring matching

    Returns:
        Number of matches found
    """
    if is_regex:
        matches = re.findall(pattern, text)
        return len(matches)
    else:
        return text.count(pattern)


def analyze_keywords_in_field(
    resume_dir: Path,
    keyword_categories: Dict[str, List[str]],
    field_name: str,
    is_regex: bool = False,
) -> Tuple[int, int, Dict[str, int], Dict[str, int]]:
    """
    Analyze keyword frequencies within a specific LaTeX field across all resumes.

    Args:
        resume_dir: Directory containing .tex resume files
        keyword_categories: Dict mapping category names to lists of keywords/patterns
        field_name: LaTeX field to search within (e.g., "brand", "ProfessionalProfile")
        is_regex: If True, treat keywords as regex patterns

    Returns:
        Tuple of (num_resumes, total_chars, keyword_total_occurrences, keyword_resume_count)
    """
    tex_files = sorted(resume_dir.glob("*.tex"))

    if not tex_files:
        raise ValueError(f"No .tex files found in {resume_dir}")

    total_chars = 0
    all_keywords = [kw for keywords in keyword_categories.values() for kw in keywords]
    keyword_total_occurrences = {}
    keyword_resume_count = {}

    resumes_with_field = 0

    for tex_file in tex_files:
        content = tex_file.read_text(encoding="utf-8")
        fields = extract_latex_fields(content)

        # Only analyze if this resume has the specified field
        if field_name not in fields:
            continue

        resumes_with_field += 1
        field_content = fields[field_name]
        total_chars += len(field_content)

        for keyword in all_keywords:
            count = count_pattern_matches(field_content, keyword, is_regex)
            if keyword not in keyword_total_occurrences:
                keyword_total_occurrences[keyword] = 0
            keyword_total_occurrences[keyword] += count
            if count > 0:
                if keyword not in keyword_resume_count:
                    keyword_resume_count[keyword] = 0
                keyword_resume_count[keyword] += 1

    return (
        resumes_with_field,
        total_chars,
        dict(keyword_total_occurrences),
        dict(keyword_resume_count),
    )


def analyze_keyword_frequencies(
    resume_dir: Path,
    keyword_categories: Dict[str, List[str]],
    is_regex: bool = False,
) -> Tuple[int, int, Dict[str, int], Dict[str, int]]:
    """
    Analyze keyword frequencies across all .tex files in a directory.

    Args:
        resume_dir: Directory containing .tex resume files
        keyword_categories: Dict mapping category names to lists of keywords/patterns
        is_regex: If True, treat keywords as regex patterns; if False, exact substring matching

    Returns:
        Tuple of (num_resumes, total_chars, keyword_total_occurrences, keyword_resume_count)
        where:
        - num_resumes: Number of resume files analyzed
        - total_chars: Total characters across all resumes
        - keyword_total_occurrences: Dict of keyword -> total occurrence count
        - keyword_resume_count: Dict of keyword -> number of resumes containing it
    """
    tex_files = sorted(resume_dir.glob("*.tex"))

    if not tex_files:
        raise ValueError(f"No .tex files found in {resume_dir}")

    total_chars = 0
    all_keywords = [kw for keywords in keyword_categories.values() for kw in keywords]
    keyword_total_occurrences = {}
    keyword_resume_count = {}

    for tex_file in tex_files:
        content = tex_file.read_text(encoding="utf-8")
        total_chars += len(content)

        for keyword in all_keywords:
            count = count_pattern_matches(content, keyword, is_regex)
            if keyword not in keyword_total_occurrences:
                keyword_total_occurrences[keyword] = 0
            keyword_total_occurrences[keyword] += count
            if count > 0:
                if keyword not in keyword_resume_count:
                    keyword_resume_count[keyword] = 0
                keyword_resume_count[keyword] += 1

    return (
        len(tex_files),
        total_chars,
        dict(keyword_total_occurrences),
        dict(keyword_resume_count),
    )


def analyze_section_patterns(
    resume_dir: Path,
    section_categories: Dict[str, List[str]],
    is_regex: bool = False,
) -> Tuple[int, Dict[str, int], Dict[str, int]]:
    """
    Analyze section name patterns across all resumes.

    Args:
        resume_dir: Directory containing .tex resume files
        section_categories: Dict mapping category names to lists of section patterns
        is_regex: If True, patterns are regex; if False, exact substring matching

    Returns:
        Tuple of (num_resumes, pattern_total_occurrences, pattern_resume_count)
        where:
        - num_resumes: Number of resume files analyzed
        - pattern_total_occurrences: Dict of pattern -> total occurrence count across all sections
        - pattern_resume_count: Dict of pattern -> number of resumes containing matching section
    """
    tex_files = sorted(resume_dir.glob("*.tex"))

    if not tex_files:
        raise ValueError(f"No .tex files found in {resume_dir}")

    all_patterns = [p for patterns in section_categories.values() for p in patterns]
    pattern_total_occurrences = {}
    pattern_resume_count = {}

    for tex_file in tex_files:
        content = tex_file.read_text(encoding="utf-8")
        sections = extract_sections(content)  # Get cleaned section names

        # Convert sections to single string for pattern matching
        sections_text = "\n".join(sections)

        for pattern in all_patterns:
            # Count matches in this resume's sections
            count = count_pattern_matches(sections_text, pattern, is_regex)

            if pattern not in pattern_total_occurrences:
                pattern_total_occurrences[pattern] = 0
            pattern_total_occurrences[pattern] += count

            if count > 0:
                if pattern not in pattern_resume_count:
                    pattern_resume_count[pattern] = 0
                pattern_resume_count[pattern] += 1

    return (
        len(tex_files),
        dict(pattern_total_occurrences),
        dict(pattern_resume_count),
    )


def analyze_field_patterns( resume_dir, field_categories, is_regex ):

    tex_files = sorted(resume_dir.glob("*.tex"))

    if not tex_files:
        raise ValueError(f"No .tex files found in {resume_dir}")

    all_patterns = [p for patterns in field_categories.values() for p in patterns]
    pattern_total_occurrences = {}
    pattern_resume_count = {}

    for tex_file in tex_files:
        content = tex_file.read_text(encoding="utf-8")
        fields = extract_latex_fields(content)  # Get cleaned field names

        # Convert fields to single string for pattern matching
        fields_text = "\n".join(fields)

        for pattern in all_patterns:
            # Count matches in this resume's fields
            count = count_pattern_matches(fields_text, pattern, is_regex)

            if pattern not in pattern_total_occurrences:
                pattern_total_occurrences[pattern] = 0
            pattern_total_occurrences[pattern] += count

            if count > 0:
                if pattern not in pattern_resume_count:
                    pattern_resume_count[pattern] = 0
                pattern_resume_count[pattern] += 1

    return (
        len(tex_files),
        dict(pattern_total_occurrences),
        dict(pattern_resume_count),
    )


def format_analysis_report(
    num_resumes: int,
    total_chars: int,
    keyword_categories: Dict[str, List[str]],
    keyword_total_occurrences: Dict[str, int],
    keyword_resume_count: Dict[str, int],
    resume_dir: Path,
) -> str:
    """
    Format analysis results as a human-readable report.

    Args:
        num_resumes: Number of resumes analyzed
        total_chars: Total characters across all resumes
        keyword_categories: Dict mapping category names to keywords
        keyword_total_occurrences: Dict of keyword -> total occurrences
        keyword_resume_count: Dict of keyword -> number of resumes with keyword
        resume_dir: Path to resume directory (for header)

    Returns:
        Formatted report string
    """
    lines = []
    lines.append(f"\nAnalyzed {num_resumes} resume files from {resume_dir}")
    lines.append(f"Total characters across all resumes: {total_chars:,}\n")

    for category, keywords in keyword_categories.items():
        lines.append("=" * 100)
        lines.append(category)
        lines.append("=" * 100)
        lines.append(f"{'Keyword':<50} {'In N Resumes':<15} {'% Resumes':<15} {'Occurrences':<12}")
        lines.append("-" * 100)

        # Sort by prevalence (% of resumes)
        sorted_keywords = sorted(
            keywords, key=lambda k: keyword_resume_count.get(k, 0), reverse=True
        )

        for keyword in sorted_keywords:
            resumes_with = keyword_resume_count.get(keyword, 0)
            percent_resumes = (resumes_with / num_resumes) * 100
            total_occur = keyword_total_occurrences.get(keyword, 0)

            lines.append(
                f"{truncate_display(keyword, 48):<50} {resumes_with:<15} "
                f"{percent_resumes:>13.1f}% {total_occur:>11}"
            )

        lines.append("")

    return "\n".join(lines)


def format_field_enumeration_report(
    field_values: Dict[str, Dict[str, int]],
    num_resumes: int,
    resume_dir: Path,
) -> str:
    """
    Format field value enumeration as a human-readable report.

    Args:
        field_values: Dict mapping field names to dicts of {value: count}
        num_resumes: Total number of resumes analyzed
        resume_dir: Path to resume directory (for header)

    Returns:
        Formatted report string
    """
    lines = []
    lines.append("\n" + "=" * 100)
    lines.append("LATEX FIELD VALUE ENUMERATION")
    lines.append("=" * 100)
    lines.append(f"Analyzed {num_resumes} resume files from {resume_dir}\n")

    # Sort fields by name for consistent output
    for field_name in sorted(field_values.keys()):
        values = field_values[field_name]

        lines.append("=" * 100)
        lines.append(f"Field: \\renewcommand{{\\{field_name}}}")
        lines.append("=" * 100)
        lines.append(f"{'Value':<70} {'Count':<10} {'% Resumes':<15}")
        lines.append("-" * 100)

        # Sort by count (descending)
        sorted_values = sorted(values.items(), key=lambda x: x[1], reverse=True)

        for value, count in sorted_values:
            percent = (count / num_resumes) * 100

            lines.append(f"{truncate_display(value, 68):<70} {count:<10} {percent:>13.1f}%")

        lines.append(f"\nTotal unique values: {len(values)}")
        lines.append("")

    return "\n".join(lines)


def format_section_enumeration_report(
    section_counts: Dict[str, int],
    num_resumes: int,
    resume_dir: Path,
) -> str:
    """
    Format section enumeration as a human-readable report.

    Args:
        section_counts: Dict mapping section names to resume count
        num_resumes: Total number of resumes analyzed
        resume_dir: Path to resume directory (for header)

    Returns:
        Formatted report string
    """
    lines = []
    lines.append("\n" + "=" * 100)
    lines.append("SECTION USAGE ACROSS RESUMES")
    lines.append("=" * 100)
    lines.append(f"Analyzed {num_resumes} resume files from {resume_dir}\n")

    lines.append(f"{'Section Name':<50} {'Count':<10} {'% Resumes':<15}") # header line
    lines.append("-" * 100)

    # Sort by count (descending)
    sorted_sections = sorted(section_counts.items(), key=lambda x: x[1], reverse=True)

    for section_name, count in sorted_sections:
        percent = (count / num_resumes) * 100

        lines.append(f"{truncate_display(section_name, 48):<50} {count:<10} {percent:>13.1f}%")

    lines.append(f"\nTotal unique sections: {len(section_counts)}")
    lines.append("")

    return "\n".join(lines)


def format_section_pattern_report(
    num_resumes: int,
    section_categories: Dict[str, List[str]],
    pattern_total_occurrences: Dict[str, int],
    pattern_resume_count: Dict[str, int],
    resume_dir: Path,
) -> str:
    """
    Format section pattern analysis as a human-readable report.

    Args:
        num_resumes: Number of resumes analyzed
        section_categories: Dict mapping category names to patterns
        pattern_total_occurrences: Dict of pattern -> total occurrences
        pattern_resume_count: Dict of pattern -> number of resumes with match
        resume_dir: Path to resume directory (for header)

    Returns:
        Formatted report string
    """
    lines = []
    lines.append("\n" + "=" * 100)
    lines.append("SECTION PATTERN MATCHING")
    lines.append("=" * 100)
    lines.append(f"Analyzed {num_resumes} resume files from {resume_dir}\n")

    for category, patterns in section_categories.items():
        lines.append("=" * 100)
        lines.append(category)
        lines.append("=" * 100)
        lines.append(f"{'Pattern':<50} {'In N Resumes':<15} {'% Resumes':<15} {'Occurrences':<12}")
        lines.append("-" * 100)

        # Sort by prevalence (% of resumes)
        sorted_patterns = sorted(
            patterns, key=lambda p: pattern_resume_count.get(p, 0), reverse=True
        )

        for pattern in sorted_patterns:
            resumes_with = pattern_resume_count.get(pattern, 0)
            percent_resumes = (resumes_with / num_resumes) * 100
            total_occur = pattern_total_occurrences.get(pattern, 0)

            lines.append(
                f"{truncate_display(pattern, 48):<50} {resumes_with:<15} "
                f"{percent_resumes:>13.1f}% {total_occur:>11}"
            )
            
        lines.append("-" * 100)
        lines.append("")

    return "\n".join(lines)



def format_field_pattern_report(
    num_resumes: int,
    field_categories: Dict[str, List[str]],
    pattern_total_occurrences: Dict[str, int],
    pattern_resume_count: Dict[str, int],
    resume_dir: Path,
) -> str:

    lines = []
    lines.append("\n" + "=" * 100)
    lines.append("FIELD PATTERN MATCHING")
    lines.append("=" * 100)
    lines.append(f"Analyzed {num_resumes} resume files from {resume_dir}\n")

    for category, patterns in field_categories.items():
        lines.append("=" * 100)
        lines.append(category)
        lines.append("=" * 100)
        lines.append(f"{'Pattern':<50} {'In N Resumes':<15} {'% Resumes':<15} {'Occurrences':<12}")
        lines.append("-" * 100)

        # Sort by prevalence (% of resumes)
        sorted_patterns = sorted(
            patterns, key=lambda p: pattern_resume_count.get(p, 0), reverse=True
        )

        for pattern in sorted_patterns:
            resumes_with = pattern_resume_count.get(pattern, 0)
            percent_resumes = (resumes_with / num_resumes) * 100
            total_occur = pattern_total_occurrences.get(pattern, 0)

            lines.append(
                f"{truncate_display(pattern, 48):<50} {resumes_with:<15} "
                f"{percent_resumes:>13.1f}% {total_occur:>11}"
            )
            
        lines.append("-" * 100)
        lines.append("")

    return "\n".join(lines)
