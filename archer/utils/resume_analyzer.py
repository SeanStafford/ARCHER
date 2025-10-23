"""
Resume Pattern Analysis Utilities

Analyzes keyword frequency patterns across LaTeX resume files to inform
template structure and understand common variations.
"""

import re
from pathlib import Path
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
    pattern = r'\\renewcommand\{\\([^}]+)\}\{'

    for match in re.finditer(pattern, content):
        # find the match to get field name and starting position
        field_name = match.group(1)
        start_pos = match.end()

        # Count braces to find the matching closing brace
        brace_count = 1
        pos = start_pos


        while pos < len(content) and brace_count > 0:
            
            # Handle escaped backslashes
            if content[pos] == '\\':
                pos += 2
                continue
            elif content[pos] == '{':
                brace_count += 1
            elif content[pos] == '}':
                brace_count -= 1
            pos += 1

        if brace_count == 0:
            field_value = content[start_pos:pos-1]
            fields[field_name] = field_value
        else:
            # Unmatched braces, skip this field
            continue

    return fields


def extract_sections(content: str) -> List[str]:
    """
    Extract all \\section*{VALUE} and \\section{VALUE} patterns from LaTeX content.

    Args:
        content: LaTeX file content as string

    Returns:
        List of section names (e.g., ["Core Skills", "Experience", ...])
    """
    sections = []

    # Pattern matches both \section*{...} and \section{...}
    pattern = r'\\section\*?\{([^}]+)\}'

    for match in re.finditer(pattern, content):
        section_name = match.group(1)
        sections.append(section_name)

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

    for tex_file in tex_files:
        content = tex_file.read_text(encoding="utf-8")
        sections = extract_sections(content)

        # Track unique sections per resume (don't count duplicates within same resume)
        unique_sections = set(sections)

        for section in unique_sections:
            if section not in section_counts:
                section_counts[section] = 0
            section_counts[section] += 1

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
    is_regex: bool = False
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
    resume_dir: Path, keyword_categories: Dict[str, List[str]]
) -> Tuple[int, int, Dict[str, int], Dict[str, int]]:
    """
    Analyze keyword frequencies across all .tex files in a directory.

    Args:
        resume_dir: Directory containing .tex resume files
        keyword_categories: Dict mapping category names to lists of keywords

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
            count = content.count(keyword)
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

            display_keyword = keyword if len(keyword) <= 48 else keyword[:45] + "..."

            lines.append(
                f"{display_keyword:<50} {resumes_with:<15} "
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

            # Truncate long values for display
            display_value = value if len(value) <= 68 else value[:65] + "..."

            lines.append(f"{display_value:<70} {count:<10} {percent:>13.1f}%")

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

    lines.append(f"{'Section Name':<50} {'Count':<10} {'% Resumes':<15}")
    lines.append("-" * 100)

    # Sort by count (descending)
    sorted_sections = sorted(section_counts.items(), key=lambda x: x[1], reverse=True)

    for section_name, count in sorted_sections:
        percent = (count / num_resumes) * 100

        # Truncate long section names for display
        display_name = section_name if len(section_name) <= 48 else section_name[:45] + "..."

        lines.append(f"{display_name:<50} {count:<10} {percent:>13.1f}%")

    lines.append(f"\nTotal unique sections: {len(section_counts)}")
    lines.append("")

    return "\n".join(lines)
