"""
LaTeX Resume Cleaner

Core functions for cleaning LaTeX resume files by removing various types of comments
and suggestion blocks while preserving escaped percentages and line-ending formatting.
"""

import re
from pathlib import Path
from typing import List, Set


class CommentType:
    """Enum-like class for comment types"""

    DECORATIVE = "decorative"
    SECTION_HEADERS = "section_headers"
    DESCRIPTIVE = "descriptive"
    COMMENTED_CODE = "commented_code"
    INLINE_ANNOTATIONS = "inline_annotations"
    INLINE_DATES = "inline_dates"
    ALL = "all"
    NONE = "none"

    @classmethod
    def get_all_types(cls) -> Set[str]:
        """Return all comment types except ALL and NONE"""
        return {
            cls.DECORATIVE,
            cls.SECTION_HEADERS,
            cls.DESCRIPTIVE,
            cls.COMMENTED_CODE,
            cls.INLINE_ANNOTATIONS,
            cls.INLINE_DATES,
        }


def should_preserve_line(line: str) -> bool:
    """
    Check if a line should be preserved without modification.

    Preserves:
    - Lines with only escaped percentages (\\%)
    - Lines ending with '%' alone (whitespace suppression)

    Args:
        line: The line to check

    Returns:
        True if line should be preserved as-is
    """
    # Check if line contains only escaped percentages
    temp = line.replace(r"\%", "")
    if "%" not in temp:
        return True

    # Check if this is line-ending whitespace suppression (ends with just %)
    # Pattern: non-comment content followed by optional whitespace and single %
    if re.search(r"[^%\s]\s*%\s*$", line) and line.strip() != "%":
        # This is likely whitespace suppression - preserve it
        # But make sure it's not also a comment line
        stripped = line.strip()
        if not stripped.startswith("%") or re.match(r"^[^%]+%\s*$", line):
            return True

    return False


def matches_comment_type(line: str, comment_type: str) -> bool:
    """
    Check if a line matches a specific comment type.

    Args:
        line: The line to check
        comment_type: The type of comment to match against

    Returns:
        True if the line matches the comment type
    """
    if comment_type == CommentType.DECORATIVE:
        # Lines with only % characters (separators)
        return bool(re.match(r"^\s*%+\s*$", line))

    elif comment_type == CommentType.SECTION_HEADERS:
        # Lines like: %%%%  My imports  %%%%%%%%%%%%%
        return bool(re.match(r"^\s*%%%.*%%%", line))

    elif comment_type == CommentType.DESCRIPTIVE:
        # Simple descriptive comments: % text (not starting with - or \)
        # Excludes line-ending % and separator comments
        return bool(re.match(r"^\s*%\s+[^-\\%]", line))

    elif comment_type == CommentType.COMMENTED_CODE:
        # Commented-out LaTeX commands: % \command
        return bool(re.match(r"^\s*%\s*\\", line))

    elif comment_type == CommentType.INLINE_ANNOTATIONS:
        # Inline comments after code with dashes: \command % ---------
        return bool(re.search(r"[^\s%].*%\s*-+\s*$", line))

    elif comment_type == CommentType.INLINE_DATES:
        # Inline date comments: {}%Aug 2024 -- May 2025}
        return bool(re.search(r"}%[A-Za-z{]", line))

    return False


def remove_inline_comment(line: str, comment_types: Set[str]) -> str:
    """
    Remove inline comments from a line if they match enabled types.

    Args:
        line: The line to process
        comment_types: Set of enabled comment types

    Returns:
        Line with inline comments removed if applicable
    """
    # Check for inline dates pattern: }%{dates} or }%dates
    if CommentType.INLINE_DATES in comment_types:
        # Remove comments like: {}%Aug 2024 -- May 2025}
        line = re.sub(r"}%\{[^}]*\}", "}", line)
        line = re.sub(r"}%[^}]*\}(?=\s*$)", "}", line)
        # Also handle simpler cases: {}%comment at end
        line = re.sub(r"}%[^}]+$", "}", line)

    # Check for inline annotation pattern: % ------
    if CommentType.INLINE_ANNOTATIONS in comment_types:
        if re.search(r"%\s*-+\s*$", line):
            # Remove the comment part
            line = re.sub(r"\s*%\s*-+\s*$", "", line)

    return line


def clean_latex_content(
    content: str, comment_types: Set[str], remove_suggest_blocks: bool = False
) -> str:
    """
    Clean LaTeX content by removing specified comment types and suggestion blocks.

    Args:
        content: The LaTeX content to clean
        comment_types: Set of comment types to remove (use CommentType constants)
        remove_suggest_blocks: Whether to remove \\suggest{...} blocks

    Returns:
        Cleaned LaTeX content
    """
    # Expand "all" to all specific types
    if CommentType.ALL in comment_types:
        comment_types = CommentType.get_all_types()
    elif CommentType.NONE in comment_types:
        comment_types = set()

    lines = content.split("\n")
    cleaned_lines = []

    for line in lines:
        # First check if we should preserve this line entirely
        if should_preserve_line(line):
            cleaned_lines.append(line)
            continue

        # Separate inline comment types from full-line comment types
        inline_types = {CommentType.INLINE_ANNOTATIONS, CommentType.INLINE_DATES}
        full_line_types = comment_types - inline_types

        # Check if this is a full-line comment that should be removed entirely
        should_remove = False
        for comment_type in full_line_types:
            if matches_comment_type(line, comment_type):
                should_remove = True
                break

        if should_remove:
            continue  # Skip this line entirely

        # Check for inline comments that should have their comment part removed
        line = remove_inline_comment(line, comment_types)

        cleaned_lines.append(line)

    result = "\n".join(cleaned_lines)

    # Remove \suggest{...} blocks if requested
    if remove_suggest_blocks:
        result = remove_suggest_blocks_from_content(result)

    return result


def remove_suggest_blocks_from_content(content: str) -> str:
    """
    Remove all \\suggest{...} blocks from LaTeX content.

    Uses a simple state machine to track brace matching.

    Args:
        content: The LaTeX content

    Returns:
        Content with \\suggest{...} blocks removed
    """
    result = []
    i = 0

    while i < len(content):
        # Look for \suggest{
        if content[i : i + 9] == r"\suggest{":
            # Found a suggest block - skip it and its contents
            i += 9  # Skip '\suggest{'
            brace_count = 1

            # Find the matching closing brace
            while i < len(content) and brace_count > 0:
                if content[i] == "{" and (i == 0 or content[i - 1] != "\\"):
                    brace_count += 1
                elif content[i] == "}" and (i == 0 or content[i - 1] != "\\"):
                    brace_count -= 1
                i += 1
        else:
            result.append(content[i])
            i += 1

    return "".join(result)


def process_file(
    input_path: Path,
    output_path: Path,
    comment_types: Set[str],
    remove_suggest_blocks: bool = False,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """
    Process a single LaTeX file.

    Args:
        input_path: Path to input .tex file
        output_path: Path to output .tex file
        comment_types: Set of comment types to remove
        remove_suggest_blocks: Whether to remove \\suggest{...} blocks
        dry_run: If True, don't write output file

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Read input file
        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Clean content
        cleaned_content = clean_latex_content(content, comment_types, remove_suggest_blocks)

        # Calculate statistics
        original_lines = len(content.split("\n"))
        cleaned_lines = len(cleaned_content.split("\n"))
        removed_lines = original_lines - cleaned_lines

        message = (
            f"Processed {input_path.name}: "
            f"{removed_lines} lines removed ({original_lines} → {cleaned_lines})"
        )

        # Write output file unless dry run
        if not dry_run:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(cleaned_content)
        else:
            message += " [DRY RUN - no changes written]"

        return True, message

    except Exception as e:
        return False, f"Error processing {input_path.name}: {str(e)}"


def process_directory(
    directory_path: Path,
    comment_types: Set[str],
    remove_suggest_blocks: bool = False,
    dry_run: bool = False,
) -> List[tuple[bool, str]]:
    results = []

    # Find all .tex files
    tex_files = sorted(directory_path.glob("*.tex"))

    if not tex_files:
        return [(False, f"No .tex files found in {directory_path}")]

    for tex_file in tex_files:
        # Process in-place (overwrite)
        success, message = process_file(
            tex_file, tex_file, comment_types, remove_suggest_blocks, dry_run
        )
        results.append((success, message))

    return results
