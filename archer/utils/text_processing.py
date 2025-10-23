"""Text processing utilities for formatting and display."""


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
