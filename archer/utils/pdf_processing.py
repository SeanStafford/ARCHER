"""
PDF processing utilities for text extraction with column and font filtering support.

Main class:
    PDFDocument: Parsed PDF with column-based text extraction and search.

Helper functions:
    page_count: Quick page count without full extraction.
    normalize_for_matching: Text normalization for fuzzy matching.
    is_text_font: Font family filtering for PDF extraction.
    cluster_by_y_tolerance: Y-coordinate clustering for line detection.
    find_section_header: Find header text in a list of lines.
"""

from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple, Union

import pdfplumber
from PyPDF2 import PdfReader


def page_count(pdf_path: Path) -> Optional[int]:
    """Get page count from PDF, or None if unreadable."""
    try:
        reader = PdfReader(str(pdf_path))
        return len(reader.pages)
    except Exception:
        return None


def normalize_for_matching(text: str) -> str:
    """Keep only lowercase alphanumeric characters for fuzzy text matching."""
    return "".join(c for c in text.lower() if c.isalnum())


def is_text_font(fontname: str, allowed_fonts: List[str]) -> bool:
    """Check if PDF font matches any allowed font family substring."""
    # PDF fonts have prefixes like "ABCDEE+EBGaramond-Bold" - strip to get family
    if "+" in fontname:
        fontname = fontname.split("+")[1]
    return any(allowed in fontname for allowed in allowed_fonts)


def cluster_by_y_tolerance(chars: List, tolerance: float = 3.0) -> List[List]:
    """
    Group characters into lines by Y-coordinate proximity.

    Handles baseline shifts between bold/regular text that would otherwise split lines.
    """
    if not chars:
        return []

    sorted_chars = sorted(chars, key=lambda c: c["top"])

    lines = []
    current_line = [sorted_chars[0]]
    current_y = sorted_chars[0]["top"]

    for char in sorted_chars[1:]:
        if abs(char["top"] - current_y) <= tolerance:
            # Within tolerance - same line
            current_line.append(char)
        else:
            # Y jumped beyond tolerance - start new line
            lines.append(current_line)
            current_line = [char]
            current_y = char["top"]

    if current_line:
        lines.append(current_line)

    return lines


def find_section_header(section_name: str, lines: List[str]) -> Optional[int]:
    """Find index of section header in lines using normalized exact match, or None."""
    section_norm = normalize_for_matching(section_name)

    for i, text in enumerate(lines):
        text_norm = normalize_for_matching(text)
        # Exact match prevents "Experience" matching "Experience (continued)"
        if section_norm == text_norm:
            return i

    return None


class PDFDocument:
    """
    Parsed PDF with column-based text extraction.

    Provides character-level extraction with support for:
    - Arbitrary column layouts via configurable split points
    - Font filtering to exclude symbols/icons (FontAwesome, bullet chars, etc.)
    - Y-coordinate clustering to handle baseline variations between fonts

    Page data is lazily loaded and cached on first access.

    Args:
        pdf_path: Path to PDF file
        column_splits: X-coordinate ratios (0.0-1.0) defining column boundaries.
                      [0.25] creates 2 columns (0-25%, 25%-100%).
                      [0.25, 0.5, 0.75] creates 4 equal columns.
                      None (default) = single full-width column.
        allowed_fonts: Font family substrings to include (None = all fonts).
                      ["Garamond", "LMMono"] would exclude FontAwesome, CMSY10, etc.
        y_tolerance: Max Y-distance (points) to group characters as same line.

    Example:
        >>> pdf = PDFDocument(Path("document.pdf"), column_splits=[0.3])
        >>> for line in pdf.get_lines(page=1, column=0):
        ...     print(line)
    """

    def __init__(
        self,
        pdf_path: Union[str, Path],
        column_splits: Optional[List[float]] = None,
        allowed_fonts: Optional[List[str]] = None,
        y_tolerance: float = 3.0,
    ):
        # Accept string or Path
        pdf_path = Path(pdf_path) if isinstance(pdf_path, str) else pdf_path
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        self.pdf_path = pdf_path
        self.column_splits = sorted(column_splits or [])
        self.num_columns = len(self.column_splits) + 1
        self.allowed_fonts = allowed_fonts
        self.y_tolerance = y_tolerance
        self._pages_cache: Optional[Dict[int, List[List[str]]]] = None
        self._page_count: Optional[int] = None

    @property
    def page_count(self) -> int:
        if self._page_count is None:
            self._page_count = page_count(self.pdf_path) or 0
        return self._page_count

    def _extract_pages(self, max_pages: int = 100) -> Dict[int, List[List[str]]]:
        """
        Extract text lines from all pages, grouped by column.

        Process:
        1. Convert column_splits ratios to absolute x-coordinates
        2. Bin each character into its column based on x-position
        3. Within each column, cluster characters into lines by y-tolerance
        4. Filter to allowed fonts if specified

        Returns:
            Dict mapping page_num (1-indexed) to list of columns,
            where each column is a list of text lines.
        """
        pages_data: Dict[int, List[List[str]]] = {}

        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages[:max_pages], start=1):
                page_width = page.width
                chars = page.chars

                # Convert ratios to absolute x-coordinates
                # e.g., splits=[0.3] on 600pt page -> boundaries=[0, 180, 600]
                boundaries = (
                    [0.0] + [page_width * ratio for ratio in self.column_splits] + [page_width]
                )

                # Bin each character into its column by x-position
                column_chars: List[List] = [[] for _ in range(self.num_columns)]
                for char in chars:
                    x = char["x0"]
                    for col_idx in range(self.num_columns):
                        if boundaries[col_idx] <= x < boundaries[col_idx + 1]:
                            column_chars[col_idx].append(char)
                            break

                # Convert each column's characters to text lines
                column_lines: List[List[str]] = []
                for col_chars in column_chars:
                    lines = self._chars_to_lines(col_chars)
                    column_lines.append(lines)

                pages_data[page_num] = column_lines

        return pages_data

    def _chars_to_lines(self, chars: List) -> List[str]:
        """Convert character list to text lines with font filtering and Y-clustering."""
        # Filter to allowed fonts if specified
        if self.allowed_fonts is not None:
            chars = [c for c in chars if is_text_font(c.get("fontname", ""), self.allowed_fonts)]

        # Cluster by Y-coordinate
        line_clusters = cluster_by_y_tolerance(chars, tolerance=self.y_tolerance)

        # Reconstruct text for each line (sorted by X)
        text_lines = []
        for char_objs in line_clusters:
            char_objs.sort(key=lambda c: c["x0"])
            line_text = "".join(c["text"] for c in char_objs)
            text_lines.append(line_text)

        return text_lines

    def _ensure_loaded(self) -> None:
        """Lazily load page data if not already cached."""
        if self._pages_cache is None:
            self._pages_cache = self._extract_pages()

    def get_lines(self, page: int, column: int = 0) -> List[str]:
        """
        Get text lines for a specific page and column.

        Args:
            page: Page number (1-indexed)
            column: Column index (0-indexed). Default 0.

        Returns:
            List of text lines, top-to-bottom order.
            Empty list if page/column doesn't exist.
        """
        self._ensure_loaded()
        if self._pages_cache is None:
            return []

        page_data = self._pages_cache.get(page)
        if page_data is None or column >= len(page_data):
            return []

        return page_data[column]

    def find(
        self, text: str, whole_line: bool = False, column: Optional[int] = None
    ) -> Optional[Tuple[int, int, int]]:
        """
        Find first occurrence of text in the document.

        Args:
            text: Text to search for (normalized: lowercase, alphanumeric only)
            whole_line: If True, text must match entire line. If False, substring match.
            column: Limit search to specific column (None = all columns)

        Returns:
            Tuple of (page, column, line_index) for first match, or None.
        """
        result = self.find_all(text, whole_line=whole_line, column=column, limit=1)
        return result[0] if result else None

    def find_all(
        self,
        text: str,
        whole_line: bool = False,
        column: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Tuple[int, int, int]]:
        """
        Find all occurrences of text in the document.

        Args:
            text: Text to search for (normalized: lowercase, alphanumeric only)
            whole_line: If True, text must match entire line. If False, substring match.
            column: Limit search to specific column (None = all columns)
            limit: Maximum number of results to return (None = all)

        Returns:
            List of (page, column, line_index) tuples for each match.
        """
        self._ensure_loaded()
        if self._pages_cache is None:
            return []

        results: List[Tuple[int, int, int]] = []
        text_norm = normalize_for_matching(text)

        for page_num in sorted(self._pages_cache.keys()):
            page_data = self._pages_cache[page_num]
            columns_to_search = [column] if column is not None else range(len(page_data))

            for col_idx in columns_to_search:
                if col_idx >= len(page_data):
                    continue

                for line_idx, line in enumerate(page_data[col_idx]):
                    line_norm = normalize_for_matching(line)
                    match = (text_norm == line_norm) if whole_line else (text_norm in line_norm)
                    if match:
                        results.append((page_num, col_idx, line_idx))
                        if limit and len(results) >= limit:
                            return results

        return results

    def iter_pages(self) -> Iterator[int]:
        """Iterate over page numbers (1-indexed)."""
        self._ensure_loaded()
        if self._pages_cache is None:
            return iter([])
        return iter(sorted(self._pages_cache.keys()))
