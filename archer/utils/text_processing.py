"""
Text processing utilities for formatting and display.

Note: extract_environment_content() moved to archer.utils.latex_parsing_tools
"""

import difflib
import re
from pathlib import Path
from typing import List, Tuple


def extract_balanced_delimiters(
    text: str,
    start_pos: int,
    open_char: str = '{',
    close_char: str = '}',
    escape_char: str = '\\'
) -> Tuple[str, int]:
    """
    Extract content between balanced delimiters, handling escaped characters.

    Assumes start_pos is AT or AFTER an opening delimiter. Counts nested delimiters
    to find the matching closing delimiter, skipping escaped characters.

    Args:
        text: Text containing delimited content
        start_pos: Position at or after opening delimiter
        open_char: Opening delimiter character (default: '{')
        close_char: Closing delimiter character (default: '}')
        escape_char: Character used for escaping (default: '\\')

    Returns:
        (content, end_pos) where:
        - content: Text between the delimiters (excluding delimiters themselves)
        - end_pos: Position after the closing delimiter

    Raises:
        ValueError: If delimiters are unmatched

    Example:
        >>> text = "foo {bar {nested} baz} qux"
        >>> content, end = extract_balanced_delimiters(text, 4)  # At opening {
        >>> content
        'bar {nested} baz'
        >>> text2 = "code [list [1, 2] more] end"
        >>> content2, end2 = extract_balanced_delimiters(text2, 5, '[', ']')
        >>> content2
        'list [1, 2] more'
    """
    depth = 1  # Start at 1 (already inside opening delimiter)
    pos = start_pos

    while pos < len(text) and depth > 0:
        if text[pos] == escape_char:
            # Skip escaped character
            pos += 2
            continue
        elif text[pos] == open_char:
            depth += 1
        elif text[pos] == close_char:
            depth -= 1
        pos += 1

    if depth != 0:
        raise ValueError(
            f"Unmatched {open_char}{close_char} delimiters starting at position {start_pos}"
        )

    # content is from start_pos to pos-1 (excluding closing delimiter)
    content = text[start_pos:pos - 1]
    return content, pos


def extract_regex_matches(text: str, pattern: str) -> List[dict]:
    """
    Extract all regex matches with named capture groups.

    General-purpose regex extraction that returns all matches as a list of dicts.
    Each dict contains all named capture groups from that match. This is useful
    for config-driven parsing where the regex pattern is specified in YAML.

    Args:
        text: Text to search
        pattern: Regex pattern with named capture groups (e.g., r'\\item\[(?P<icon>...)\]')

    Returns:
        List of dicts, one per match, with all named capture groups.
        Returns empty list if no matches found.

    Example:
        >>> pattern = r'\\item\[(?P<icon>[^\]]+)\]\s*(?P<text>[^\n]+)'
        >>> text = '\\item[\\faDatabase] PostgreSQL\\n\\item[\\faCode] Python'
        >>> extract_regex_matches(text, pattern)
        [
            {'icon': '\\faDatabase', 'text': 'PostgreSQL'},
            {'icon': '\\faCode', 'text': 'Python'}
        ]

        >>> pattern = r'\\section\{(?P<title>[^}]+)\}'
        >>> text = '\\section{Introduction}'
        >>> extract_regex_matches(text, pattern)
        [{'title': 'Introduction'}]

        >>> extract_regex_matches('no matches', r'(?P<foo>bar)')
        []
    """
    return [match.groupdict() for match in re.finditer(pattern, text)]


def truncate_display(text: str, max_len: int) -> str:
    """
    Truncate text for display with ellipsis if needed.

    Args:
        text: Text to truncate
        max_len: Maximum length including ellipsis

    Returns:
        Original text if within max_len, otherwise truncated with "..."

    Example:
        >>> truncate_display("short", 10)
        "short"
        >>> truncate_display("this is a very long string", 10)
        "this is..."
    """
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def normalize_par_to_blank_line(content: str) -> str:
    """
    Replace \\par at line endings with blank lines (paragraph breaks).

    LaTeX treats blank lines and \\par as equivalent paragraph breaks.
    Normalizing to blank lines makes files more consistent and reduces diff noise.

    Excludes lines containing \\centering where \\par has special behavior.

    Args:
        content: LaTeX content with potential \\par commands

    Returns:
        Content with \\par replaced by blank lines (except in centering contexts)

    Example:
        >>> normalize_par_to_blank_line("Machine Learning (ML)\\par\\nNext section")
        'Machine Learning (ML)\\n\\nNext section'
        >>> normalize_par_to_blank_line("\\centering Text here\\par\\n")
        '\\centering Text here\\par\\n'  # Unchanged - centering preserved
    """
    # Import here to avoid circular dependency
    from archer.contexts.templating.latex_patterns import SectionRegex

    # Replace: "text\par\n" -> "text\n\n" (but not on lines with \centering)
    # Pattern captures content before \par in group 1
    return re.sub(SectionRegex.PAR_AT_LINE_END, r'\1\n\n', content, flags=re.MULTILINE)


def set_max_consecutive_blank_lines(content: str, max_consecutive: int = 1) -> str:
    """
    Normalize consecutive blank lines to a maximum number.

    Replaces 2 or more consecutive blank lines with max_consecutive blank lines.
    This standardizes spacing in text documents for consistent formatting.

    Args:
        content: The text content to normalize
        max_consecutive: Maximum number of consecutive blank lines to allow.
                        Use 0 to remove all blank lines, 1 for standard
                        normalization (default: 1)

    Returns:
        Content with normalized blank lines

    Example:
        >>> set_max_consecutive_blank_lines("text\\n\\n\\n\\nmore", max_consecutive=1)
        'text\\n\\nmore'
        >>> set_max_consecutive_blank_lines("text\\n\\n\\n\\nmore", max_consecutive=0)
        'text\\nmore'
    """
    # When max_consecutive=0, we want to remove ALL blank lines (including single ones)
    # When max_consecutive>0, we only normalize runs of 2+ blank lines
    if max_consecutive == 0:
        # Match ANY blank lines (1 or more)
        # \n\s*\n matches first blank line, (\s*\n)* matches zero or more additional
        pattern = r'\n\s*\n(\s*\n)*'
    else:
        # Match 2+ consecutive blank lines only
        # \n\s*\n matches first blank line, (\s*\n)+ matches one or more additional
        pattern = r'\n\s*\n(\s*\n)+'

    # Replacement is max_consecutive+1 newlines
    # (e.g., max_consecutive=1 means "\n\n" which is 1 blank line)
    replacement = '\n' * (max_consecutive + 1)

    return re.sub(pattern, replacement, content)


def get_meaningful_diff(
    file1: Path,
    file2: Path,
    context_lines: int = 3
) -> Tuple[List[str], int]:
    """
    Compare two files ignoring blank line differences.

    Removes all blank lines from both files before comparing. This is useful
    for comparing LaTeX files where blank line placement may vary but doesn't
    affect the compiled output.

    Args:
        file1: First file to compare
        file2: Second file to compare
        context_lines: Number of context lines around differences (default: 3)

    Returns:
        Tuple of (diff_lines, num_differences):
        - diff_lines: List of unified diff output lines
        - num_differences: Count of actual content differences (excluding headers)

    Example:
        >>> diff_lines, num_diffs = get_meaningful_diff(
        ...     Path("original.tex"),
        ...     Path("modified.tex")
        ... )
        >>> if num_diffs == 0:
        ...     print("Files are identical (ignoring blank lines)")
        >>> else:
        ...     print(f"Found {num_diffs} differences")
        ...     for line in diff_lines:
        ...         print(line)
    """
    content1 = file1.read_text(encoding='utf-8')
    content2 = file2.read_text(encoding='utf-8')

    # Remove all blank lines for comparison
    lines1 = set_max_consecutive_blank_lines(content1, max_consecutive=0).split('\n')
    lines2 = set_max_consecutive_blank_lines(content2, max_consecutive=0).split('\n')

    if lines1 == lines2:
        return [], 0

    # Use difflib for detailed comparison
    diff = list(difflib.unified_diff(
        lines1,
        lines2,
        fromfile=str(file1.name),
        tofile=str(file2.name),
        lineterm='',
        n=context_lines
    ))

    # Count actual differences (lines starting with + or -, excluding headers)
    num_diffs = sum(1 for line in diff if line.startswith(('+', '-')))
    header_lines = sum(1 for line in diff if line.startswith(('---', '+++')))
    num_diffs -= header_lines

    return diff, num_diffs
