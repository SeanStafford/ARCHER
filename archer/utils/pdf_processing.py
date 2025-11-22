"""
PDF processing utilities.

Shared utilities for working with PDF files across ARCHER contexts.
"""

from pathlib import Path
from typing import Optional

from PyPDF2 import PdfReader


def page_count(pdf_path: Path) -> Optional[int]:
    """
    Get page count from PDF file.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Number of pages, or None if PDF cannot be read

    Example:
        >>> from pathlib import Path
        >>> count = page_count(Path("resume.pdf"))
        >>> if count is not None:
        ...     print(f"PDF has {count} pages")
    """
    try:
        reader = PdfReader(str(pdf_path))
        return len(reader.pages)
    except Exception:
        return None
