"""
Markdown Utilities

Utilities for converting LaTeX formatting to markdown and parsing markdown structure.
"""

import re
from dataclasses import dataclass, field
from typing import Any, List, Optional

import mistune

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


@dataclass
class MarkdownTree:
    """
    Hierarchical representation of a markdown document.

    Represents nested heading structure where each node has:
    - title: The heading text (empty string for root)
    - content: Text content under this heading (before any subheadings)
    - subsections: Child headings nested under this one
    """

    title: str = ""
    content: str = ""
    subsections: List["MarkdownTree"] = field(default_factory=list)
    truncation: Optional[int] = 50

    def __str__(self) -> str:
        """Print tree structure from this node down."""
        lines = []
        self._format_tree(lines, indent=0, truncation=self.truncation)
        return "\n".join(lines)

    def _format_tree(self, lines: List[str], indent: int, truncation: Optional[int]) -> None:
        """Recursively format tree into lines."""
        prefix = "  " * indent
        title = self.title or "(root)"
        content_preview = self.content.replace("\n", " ")
        if truncation is not None and len(content_preview) > truncation:
            content_preview = content_preview[: truncation - 3] + "..."
        lines.append(f"{prefix}{title}: '{content_preview}'")
        for sub in self.subsections:
            sub._format_tree(lines, indent + 1, truncation)


def _extract_text_from_token(token: dict[str, Any]) -> str:
    """Recursively extract text from a mistune token."""
    if token["type"] == "text":
        return token["raw"]
    if "children" in token:
        return "".join(_extract_text_from_token(c) for c in token["children"])
    if "raw" in token:
        return token["raw"]
    return ""


def _tokens_to_text(tokens: List[dict[str, Any]]) -> str:
    """Convert list of mistune tokens to plain text."""
    parts = []
    for tok in tokens:
        if tok["type"] == "paragraph":
            parts.append(_extract_text_from_token(tok))
        elif tok["type"] == "list":
            for item in tok["children"]:
                item_text = _extract_text_from_token(item)
                parts.append(f"* {item_text}")
    return "\n".join(parts)


# build_markdown_tree written by Claude Code
def build_markdown_tree(text: str) -> MarkdownTree:
    """
    Parse markdown text into a hierarchical tree structure.

    Uses mistune to tokenize markdown, then builds a tree based on heading levels.
    Each heading becomes a node, with deeper headings (e.g., ### under ##)
    becoming children in the subsections list.

    Args:
        text: Markdown text to parse

    Returns:
        MarkdownTree with nested structure reflecting heading hierarchy
    """
    md = mistune.create_markdown(renderer=None)
    tokens = md(text)

    root = MarkdownTree()
    stack = [(0, root)]  # List[tuple[int, MarkdownTree]]
    pending_content = []  # List[dict[str, Any]]

    for tok in tokens:
        if tok["type"] == "blank_line":
            continue

        if tok["type"] == "heading":
            level = tok["attrs"]["level"]
            title = _extract_text_from_token(tok)

            # Flush pending content to current node
            if pending_content:
                _, current = stack[-1]
                current.content = _tokens_to_text(pending_content)
                pending_content = []

            # Pop stack until we find parent level
            while stack and stack[-1][0] >= level:
                stack.pop()

            # Create new node
            new_node = MarkdownTree(title=title)

            # Add to parent's subsections
            if stack:
                _, parent = stack[-1]
                parent.subsections.append(new_node)

            stack.append((level, new_node))
        else:
            pending_content.append(tok)

    # Flush final content
    if pending_content and stack:
        _, current = stack[-1]
        current.content = _tokens_to_text(pending_content)

    return root
