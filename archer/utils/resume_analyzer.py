"""
Resume Pattern Analysis Utilities

Analyzes keyword frequency patterns across LaTeX resume files to inform
template structure and understand common variations.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple


# Extract field patterns from LaTeX content.
def extract_latex_fields(content: str) -> Dict[str, str]:
    
    fields = {}

    pattern = r'\\renewcommand\{\\([^}]+)\}\{'

    for match in re.findall(pattern, content):
        # find the match to get field name and starting position
        field_name = match.group(1)
        start_pos = match.end() # position after the opening brace

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



def count_pattern_matches(text: str, pattern: str, is_regex: bool = False) -> int:
    """
    Count occurrences of a pattern in text, supporting both exact and regex matching.

    Returns:
        Number of matches found
    """
    if is_regex:
        matches = re.findall(pattern, text)
        return len(matches)
    else:
        return text.count(pattern)

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
