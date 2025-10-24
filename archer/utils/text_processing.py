"""Text processing utilities for formatting and display."""

from typing import Tuple


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


def extract_environment_content(
    text: str, env_name: str, start_pos: int = 0
) -> Tuple[str, int, int]:
    """
    Extract content from LaTeX environment, handling nested environments.

    Finds \\begin{env_name} and matching \\end{env_name}, correctly handling
    nested environments of the same name.

    Args:
        text: LaTeX text
        env_name: Environment name (e.g., 'itemize', 'itemizeMain')
        start_pos: Position to start searching (default: 0)

    Returns:
        (content, begin_end_pos, end_start_pos) where:
        - content: Text between \\begin{env} and \\end{env}
        - begin_end_pos: Position after \\begin{env_name}
        - end_start_pos: Position at \\end{env_name}

    Raises:
        ValueError: If environment is not found or unmatched

    Example:
        >>> text = "\\\\begin{itemize} foo \\\\begin{itemize} bar \\\\end{itemize} \\\\end{itemize}"
        >>> content, begin_end, end_start = extract_environment_content(text, 'itemize')
        >>> content
        ' foo \\\\begin{itemize} bar \\\\end{itemize} '
    """
    import re

    # Find \begin{env_name}
    begin_pattern = rf'\\begin\{{{env_name}\}}'
    begin_match = re.search(begin_pattern, text[start_pos:])

    if not begin_match:
        raise ValueError(f"No \\begin{{{env_name}}} found")

    begin_end_pos = start_pos + begin_match.end()

    # Count nested environments to find matching \end{env_name}
    pos = begin_end_pos
    depth = 1

    begin_nested_pattern = rf'\\begin\{{{env_name}\}}'
    end_nested_pattern = rf'\\end\{{{env_name}\}}'

    while pos < len(text) and depth > 0:
        begin_nested = re.search(begin_nested_pattern, text[pos:])
        end_nested = re.search(end_nested_pattern, text[pos:])

        if end_nested:
            if begin_nested and begin_nested.start() < end_nested.start():
                # Found nested \begin before \end
                depth += 1
                pos += begin_nested.end()
            else:
                # Found \end
                depth -= 1
                if depth == 0:
                    end_start_pos = pos + end_nested.start()
                    content = text[begin_end_pos:end_start_pos]
                    return content, begin_end_pos, end_start_pos
                pos += end_nested.end()
        else:
            break

    raise ValueError(f"Unmatched \\begin{{{env_name}}}")


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
