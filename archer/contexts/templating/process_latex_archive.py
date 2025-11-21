"""
LaTeX Archive Processing

High-level functions for processing historical resume LaTeX files with two distinct modes:

1. **Clean Mode** (normalize=False):
   Granular control over comment removal. User specifies exactly which comment
   types to remove and whether to remove suggest blocks.

2. **Normalize Mode** (normalize=True):
   Opinionated full processing designed to match generated output conventions.
   Automatically removes ALL comments and suggest blocks, then applies format
   standardizations (blank lines, Education header, trailing whitespace).

The normalize flag is not an "add-on" - it's a mode selector that determines
the entire processing behavior. Normalization inherently requires full cleaning.

This module is specifically for processing the historical resume archive and uses
patterns defined in latex_patterns.py to ensure consistency with parsing/generation.
"""

import re
from pathlib import Path
from typing import List, Set

from archer.contexts.templating.latex_patterns import PageRegex, SectionRegex
from archer.utils.clean_latex import CommentType, clean_latex_content
from archer.utils.latex_parsing_tools import extract_environment_content
from archer.utils.text_processing import (
    normalize_par_to_blank_line,
    set_max_consecutive_blank_lines,
)

# ============================================================================
# Normalization Functions (Normalize Mode)
# ============================================================================


def normalize_textblock_position(content: str) -> str:
    """
    Move textblock to after page toggles using extract_environment_content.

    Textblocks can appear anywhere in a page but generation places them
    right after page setup toggles on page 2. This normalizes their position to
    match generation output and eliminate false-positive diffs.

    Note: textblock* has non-standard parameter format {width}(x,y), so we use
    extract_environment_content (no parameter parsing) instead of extract_environment.

    Args:
        content: LaTeX content

    Returns:
        Content with textblock repositioned after page setup toggles on page 2
    """
    # Try to extract textblock environment using extract_environment_content
    try:
        # Use extract_environment_content which returns (content, begin_end_pos, end_start_pos)
        # We need the full environment including \begin and \end
        _, start, end = extract_environment_content(
            content, "textblock*", include_env_command_in_positions=True
        )

        # Extract full textblock (including \begin{textblock*}...\end{textblock*})
        textblock_full = content[start:end]

        # Also capture any decoration commands immediately following textblock
        # (leftgrad, bottombar commands that are part of the decoration set)
        remaining = content[end:]
        decorations_match = re.match(PageRegex.DECORATIONS_FOLLOWING_TEXTBLOCK, remaining)
        if decorations_match:
            textblock_full += decorations_match.group(0)
            end += len(decorations_match.group(0))

        # Remove textblock from current position
        content = content[:start] + content[end:]

        # Find page setup after clearpage (page 2+)
        page_setup_match = re.search(PageRegex.PAGE_SETUP_AFTER_CLEARPAGE, content, re.DOTALL)

        if page_setup_match:
            # Insert after the page setup (at end of captured group 1)
            insert_pos = page_setup_match.end(1)
            content = (
                content[:insert_pos] + "\n\n" + textblock_full.strip() + "\n" + content[insert_pos:]
            )

    except ValueError:
        # No textblock found, return as-is
        pass

    return content


def normalize_sean_resume_structure(content: str) -> str:
    """
    Apply Sean's resume-specific structural normalization rules.

    This function enforces Sean's specific LaTeX formatting opinions for resume structure.
    It should only be used for Sean's resume format, not general LaTeX documents.

    Rules (applied in priority order):
    0. Convert tabs to spaces (4 spaces per tab)
    0.5. Strip all leading whitespace from lines (indentation is for readability only)
    1. Education header: Convert old \\phantomsection format → \\section*{Education}
    2. Remove \\vspace at top of column (after \\switchcolumn)
    3. Remove \\vspace at bottom of column (before \\switchcolumn)
    4. Exactly 1 blank line after \\begin{itemize...} (all variants)
    5. At least 1 blank line before \\begin{itemize...} (all variants)
    6. Exactly 2 blank lines before and after \\section*{...} commands
    7. Exactly 1 blank line before \\end{...} (all environment closings)
    8. Exactly 2 blank lines after \\end{...} (all environment closings)
    9. Exactly 1 blank line before \\item[...] (all item types)
    10. Zero blank lines around \\renewcommand, \\setlength, \\deflen (unless overridden)
    11. Normalize textblock position (move to after page setup toggles)
    12. Remove space between ] and { in \\item[...] commands
    13. Collapse multiple spaces to single space after \\item commands
    14. Remove trailing % with only whitespace before it on line
    15. Remove \\vspace between nested project environments (itemizeAProject, itemizeKeyProject)

    Args:
        content: The LaTeX content to normalize

    Returns:
        Content with Sean's structural rules applied
    """
    # Rule 0: Convert tabs to spaces (standardize indentation)
    result = content.replace("\t", "        ")  # 1 tab = 8 spaces (matches Education template)

    # Rule 0.5: Strip all leading whitespace from lines
    result = "\n".join(line.lstrip() for line in result.split("\n"))

    # Rule 1: Convert old Education header format (from normalize_education_header)
    result = re.sub(
        SectionRegex.OLD_EDUCATION_HEADER, r"\\section*{Education}\n", result, flags=re.DOTALL
    )

    # Rule 2: Remove \vspace at top of column (after \switchcolumn)
    # This doen't affect layout since they're at column boundaries
    result = re.sub(r"(\\switchcolumn)\n+\\vspace\{[^}]+\}\n+", r"\1\n\n", result)

    # Rule 3: Remove \vspace at bottom of column (before \switchcolumn)
    # This doen't affect layout since they're at column boundaries
    result = re.sub(r"\n+\\vspace\{[^}]+\}\n+(\\switchcolumn)", r"\n\n\1", result)

    # Rule 10 (apply early, lower priority): Zero blank lines around preamble commands
    # Remove blank lines before \renewcommand, \setlength, \deflen
    result = re.sub(r"\n\n+(\\renewcommand)", r"\n\1", result)
    result = re.sub(r"\n\n+(\\setlength)", r"\n\1", result)
    result = re.sub(r"\n\n+(\\deflen)", r"\n\1", result)
    # Remove blank lines after these commands
    result = re.sub(r"(\\renewcommand\{[^}]+\}\{[^}]*\})\n\n+", r"\1\n", result)
    result = re.sub(r"(\\setlength\{[^}]+\}\{[^}]*\})\n\n+", r"\1\n", result)
    result = re.sub(r"(\\deflen\{[^}]+\}\{[^}]*\})\n\n+", r"\1\n", result)

    # Rule 9: Exactly 1 blank line before \item[...] and variants (\itemLL, \itemi, etc.)
    # Pattern \item[^ ]* matches \item followed by any non-space characters
    result = re.sub(r"\n+(\s*\\item[^ ]*)", r"\n\n\1", result)

    # Rule 8: Exactly 2 blank lines after \end{...}
    # Match \end{environment_name}, then strip blanks and add 2
    result = re.sub(r"( *\\end\{[^}]+\})\n+", r"\1\n\n\n", result)

    # Rule 7: Exactly 1 blank line before \end{...}
    # First remove all blank lines before \end{, then add exactly 1
    result = re.sub(r"\n+( *\\end\{[^}]+\})", r"\n\n\1", result)

    # Rule 6: Exactly 2 blank lines before and after \section*{...}
    # Before: strip blanks and add 2
    result = re.sub(r"\n+(\\section\*\{[^}]+\})", r"\n\n\n\1", result)
    # After: strip blanks and add 2
    result = re.sub(r"(\\section\*\{[^}]+\})\n+", r"\1\n\n\n", result)

    # Rule 5: At least 1 blank line before \begin{itemize...}
    # Match \begin{itemize variants} - if no blank line, add 1
    result = re.sub(r"([^\n])\n( *\\begin\{itemize[^}]*\})", r"\1\n\n\2", result)

    # Rule 4: Exactly 1 blank line after \begin{itemize...}
    # Strip all blanks after, then add exactly 1
    result = re.sub(r"(\\begin\{itemize[^}]*\})\n+", r"\1\n\n", result)

    # Rule 11: Normalize textblock position (move to after page toggles)
    result = normalize_textblock_position(result)

    # Rule 12: Remove space between ] and { in \item[...] commands
    # Matches: \item[...] { → \item[...]{
    result = re.sub(r"(\\item\[[^\]]*\])\s+\{", r"\1{", result)

    # Rule 13: Collapse multiple spaces to single space after \item commands
    # Matches: \itemLL  \texttt → \itemLL \texttt
    result = re.sub(r"(\\item\w+)\s{2,}", r"\1 ", result)

    # Rule 14: Remove trailing % with only whitespace before it on line
    # Matches: \paperwidth} % → \paperwidth}
    # Preserves line-ending % used for whitespace suppression (when % is at end after content)
    result = re.sub(r"\s+%\s*$", "", result, flags=re.MULTILINE)

    # Rule 15: Remove \vspace between nested project environments
    # Matches: \end{itemizeKeyProject}\n\n\vspace{5pt}\n\n\begin{itemizeKeyProject}
    # This vspace is an artifact that doesn't affect layout (projects have their own spacing)
    result = re.sub(
        r"(\\end\{itemize(?:Key)?Project\})\n+\\vspace\{[^}]+\}\n+(\\begin\{itemize(?:Key)?Project\})",
        r"\1\n\n\n\2",
        result,
    )

    return result


def apply_normalization_until_convergence(content: str, max_passes: int = 10) -> str:
    """
    Apply normalization rules repeatedly until output converges (no more changes).

    This ensures idempotency and catches cases where one rule creates conditions
    for another rule (e.g., textblock repositioning making vspace adjacent to switchcolumn).

    Args:
        content: LaTeX content to normalize
        max_passes: Maximum number of passes to prevent infinite loops (default 10)

    Returns:
        Fully normalized content
    """
    previous = content
    for pass_num in range(max_passes):
        current = normalize_sean_resume_structure(previous)
        if current == previous:
            # Converged - no more changes
            return current
        previous = current

    # If we hit max_passes, return what we have (with warning in future)
    return current


def strip_trailing_whitespace(content: str) -> str:
    """
    Remove trailing spaces and tabs from lines.

    Preserves line-ending % (LaTeX whitespace suppression).

    Args:
        content: The LaTeX content

    Returns:
        Content with trailing whitespace removed

    Example:
        >>> strip_trailing_whitespace("text   \\n")
        'text\\n'
        >>> strip_trailing_whitespace("text %\\n")  # Preserves line-ending %
        'text %\\n'
    """
    lines = content.split("\n")
    cleaned_lines = []

    for line in lines:
        # Check if line ends with % (whitespace suppression)
        if line.rstrip().endswith("%"):
            # Strip only spaces/tabs before the %, keep the %
            # Find the last % and preserve everything from there
            stripped = line.rstrip(" \t")
        else:
            # Normal line - strip all trailing whitespace
            stripped = line.rstrip()

        cleaned_lines.append(stripped)

    return "\n".join(cleaned_lines)


def _apply_normalizations(content: str) -> str:
    """
    Apply all format normalization operations to LaTeX content.

    This internal helper applies normalizations in the correct order:
    1. Replace \\par with blank lines (general purpose - consistent paragraph breaks)
    2. Normalize blank lines (general purpose - reduce multiple consecutive blanks)
    3. Normalize Sean's resume structure (opinionated spacing rules)
    4. Strip trailing whitespace (general purpose)

    Args:
        content: The LaTeX content to normalize

    Returns:
        Fully normalized LaTeX content
    """
    # Order matters: normalize structure first, then whitespace
    result = content
    result = strip_trailing_whitespace(result)
    result = normalize_par_to_blank_line(result)
    result = set_max_consecutive_blank_lines(result, max_consecutive=1)
    result = apply_normalization_until_convergence(result)
    result = strip_trailing_whitespace(result)

    return result


# ============================================================================
# Processing Functions (Clean Mode + Normalize Mode)
# ============================================================================


def process_file(
    input_path: Path,
    output_path: Path,
    comment_types: Set[str],
    remove_suggest_blocks: bool = False,
    normalize: bool = False,
    dry_run: bool = False,
    preamble_comment_types: Set[str] | None = None,
) -> tuple[bool, str]:
    """
    Process a single LaTeX file with either Clean Mode or Normalize Mode.

    **Clean Mode** (normalize=False):
    - Uses provided comment_types and remove_suggest_blocks parameters
    - Granular control over what gets removed

    **Normalize Mode** (normalize=True):
    - Overrides ALL parameters to ensure full cleaning + normalization
    - Removes ALL comments (including preamble comments)
    - Removes ALL suggest blocks
    - Applies format standardizations (blank lines, Education header, trailing whitespace)

    Args:
        input_path: Path to input .tex file
        output_path: Path to output .tex file
        comment_types: Set of comment types to remove (ignored if normalize=True)
        remove_suggest_blocks: Whether to remove \\suggest{...} blocks (ignored if normalize=True)
        normalize: If True, enables Normalize Mode (overrides cleaning parameters)
        dry_run: If True, don't write output file
        preamble_comment_types: Set of comment types for preamble (ignored if normalize=True)

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Normalize Mode: Override all cleaning parameters for full processing
        if normalize:
            # Override specifications to remove ALL comments and suggest blocks
            remove_suggest_blocks = True
            comment_types = {CommentType.ALL}
            preamble_comment_types = {CommentType.ALL}
        # Read input file
        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Step 1: Clean (remove comments and suggest blocks)
        cleaned_content = clean_latex_content(
            content, comment_types, remove_suggest_blocks, preamble_comment_types
        )

        # Step 2: Normalize Mode only - apply format standardizations
        if normalize:
            final_content = _apply_normalizations(cleaned_content)
        else:
            final_content = cleaned_content

        # Calculate statistics
        original_lines = len(content.split("\n"))
        final_lines = len(final_content.split("\n"))
        removed_lines = original_lines - final_lines

        message = (
            f"Processed {input_path.name}: "
            f"{removed_lines} lines removed ({original_lines} → {final_lines})"
        )
        if normalize:
            message += " [normalized]"

        # Write output file unless dry run
        if not dry_run:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_content)
        else:
            message += " [DRY RUN - no changes written]"

        return True, message

    except Exception as e:
        return False, f"Error processing {input_path.name}: {str(e)}"


def process_directory(
    directory_path: Path,
    comment_types: Set[str],
    remove_suggest_blocks: bool = False,
    normalize: bool = False,
    dry_run: bool = False,
    preamble_comment_types: Set[str] | None = None,
) -> List[tuple[bool, str]]:
    """
    Process all .tex files in a directory.

    See process_file() for details on Clean Mode vs Normalize Mode.

    Args:
        directory_path: Path to directory containing .tex files
        comment_types: Set of comment types to remove (ignored if normalize=True)
        remove_suggest_blocks: Whether to remove \\suggest{...} blocks (ignored if normalize=True)
        normalize: If True, enables Normalize Mode (overrides cleaning parameters)
        dry_run: If True, don't write output files
        preamble_comment_types: Set of comment types for preamble (ignored if normalize=True)

    Returns:
        List of (success, message) tuples for each file
    """
    results = []

    # Find all .tex files
    tex_files = sorted(directory_path.glob("*.tex"))

    if not tex_files:
        return [(False, f"No .tex files found in {directory_path}")]

    for tex_file in tex_files:
        # Process in-place (overwrite)
        success, message = process_file(
            tex_file,
            tex_file,
            comment_types,
            remove_suggest_blocks,
            normalize,
            dry_run,
            preamble_comment_types,
        )
        results.append((success, message))

    return results
