"""
Markdown Utilities

Utilities for converting LaTeX formatting to markdown.
"""

import re
from typing import List

from archer.utils.latex_parsing_tools import replace_command
from archer.utils.text_processing import extract_balanced_delimiters


def _remove_href_keep_text(text: str) -> str:
    """Remove \\href{url}{text} commands, keeping only the display text.

    Handles nested braces in the text argument using balanced delimiter matching.
    """
    result = text

    while True:
        pos = result.find(r"\href{")
        if pos == -1:
            break

        # Position after '\href{'
        url_start = pos + 6

        try:
            # Extract URL (first argument)
            url, url_end = extract_balanced_delimiters(result, url_start)

            # Next char should be '{'
            if url_end >= len(result) or result[url_end] != "{":
                break

            # Extract text (second argument)
            text_start = url_end + 1
            display_text, text_end = extract_balanced_delimiters(result, text_start)

            # Strip leading/trailing whitespace from extracted text
            display_text = display_text.strip()

            # Replace entire \href{url}{text} with just display_text
            result = result[:pos] + display_text + result[text_end:]
        except ValueError:
            break

    return result


def latex_to_markdown(text: str) -> str:
    """
    Convert LaTeX formatting to markdown.

    Handles common LaTeX commands and converts them to markdown equivalents
    where appropriate, otherwise strips to plaintext.

    Args:
        text: Text with LaTeX formatting

    Returns:
        Text with markdown formatting
    """
    if not text:
        return ""

    # Convert commands to markdown equivalents (handles nested braces)
    text = replace_command(text, "textbf", "**", "**")
    text = replace_command(text, "coloremph", "**", "**")
    text = replace_command(text, "textit", "*", "*")
    text = replace_command(text, "texttt", "`", "`")

    # Remove href, keep just the link text
    text = _remove_href_keep_text(text)

    # Convert special symbols
    text = text.replace("\\texttimes", "×")

    # Convert LaTeX line breaks to spaces (in inline text like skill names)
    text = text.replace("\\\\", " ")

    # Remove color commands
    text = re.sub(r"\\color\{[^}]+\}", "", text)

    # Remove page/line break hints (no visual effect in markdown)
    text = text.replace("\\nolinebreak", "")
    text = text.replace("\\nopagebreak", "")

    # Remove common formatting commands
    text = text.replace("\\centering", "")
    text = text.replace("\\par", "")
    text = text.replace("\\hfill", "")

    # Remove remaining LaTeX commands (keep content)
    text = re.sub(r"\\[a-zA-Z]+\{([^}]+)\}", r"\1", text)

    # Remove stray braces and backslashes
    text = text.replace("{", "").replace("}", "")
    text = text.replace("\\", "")

    # Clean up whitespace
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text


def format_list_markdown(items: List[str], section_name: str) -> str:
    """
    Format a simple list as markdown.

    Args:
        items: List of items
        section_name: Name to use as header

    Returns:
        Markdown-formatted list
    """
    parts = [f"## {section_name}\n"]

    for item in items:
        item_text = latex_to_markdown(item)
        parts.append(f"- {item_text}")

    return "\n".join(parts)
