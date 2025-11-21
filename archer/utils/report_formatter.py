"""
Utility functions for formatting text-based reports and tables.

Provides consistent table formatting for resume analysis reports.
"""

from typing import Any, List


class Column:
    """Column definition for table formatting."""

    def __init__(self, name: str, width: int, align: str = "<"):
        """
        Args:
            name: Column header name
            width: Column width in characters
            align: Alignment ('<' left, '>' right, '^' center)
        """
        self.name = name
        self.width = width
        self.align = align

    def format_header(self) -> str:
        """Format column header with alignment."""
        return f"{self.name:{self.align}{self.width}}"

    def format_value(self, value: Any) -> str:
        """Format column value with alignment."""
        return f"{value:{self.align}{self.width}}"


class TableFormatter:
    """Builder for formatted text tables with aligned columns."""

    def __init__(self, columns: List[Column], total_width: int = 100):
        """
        Args:
            columns: List of Column definitions
            total_width: Total report width for separators
        """
        self.columns = columns
        self.total_width = total_width
        self.lines: List[str] = []

    def add_section_header(self, title: str) -> "TableFormatter":
        """
        Add section header with top/bottom separator lines.

        Args:
            title: Section title

        Returns:
            Self for method chaining
        """
        self.lines.append("=" * self.total_width)
        self.lines.append(title)
        self.lines.append("=" * self.total_width)
        return self

    def add_table_header(self) -> "TableFormatter":
        """
        Add table header row with column names.

        Returns:
            Self for method chaining
        """
        header_parts = [col.format_header() for col in self.columns]
        self.lines.append(" ".join(header_parts))
        return self

    def add_separator(self, char: str = "-") -> "TableFormatter":
        """
        Add horizontal separator line.

        Args:
            char: Character to use for separator

        Returns:
            Self for method chaining
        """
        self.lines.append(char * self.total_width)
        return self

    def add_row(self, values: List[Any]) -> "TableFormatter":
        """
        Add data row with column values.

        Args:
            values: List of values (one per column)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If number of values doesn't match columns
        """
        if len(values) != len(self.columns):
            raise ValueError(f"Expected {len(self.columns)} values, got {len(values)}")

        row_parts = [col.format_value(val) for col, val in zip(self.columns, values)]
        self.lines.append(" ".join(row_parts))
        return self

    def add_summary(self, text: str) -> "TableFormatter":
        """
        Add summary line (typically after table data).

        Args:
            text: Summary text

        Returns:
            Self for method chaining
        """
        self.lines.append(f"\n{text}")
        return self

    def add_blank_line(self) -> "TableFormatter":
        """
        Add blank line.

        Returns:
            Self for method chaining
        """
        self.lines.append("")
        return self

    def add_text(self, text: str) -> "TableFormatter":
        """
        Add arbitrary text line.

        Args:
            text: Text to add

        Returns:
            Self for method chaining
        """
        self.lines.append(text)
        return self

    def render(self) -> str:
        """
        Render accumulated lines to string.

        Returns:
            Formatted report string
        """
        return "\n".join(self.lines)


def format_percentage(count: int, total: int, decimal_places: int = 1) -> str:
    """
    Format count as percentage of total.

    Args:
        count: Count value
        total: Total value
        decimal_places: Number of decimal places

    Returns:
        Formatted percentage string (e.g., "75.0%")
    """
    if total == 0:
        return "0.0%"
    percent = (count / total) * 100
    return f"{percent:.{decimal_places}f}%"
