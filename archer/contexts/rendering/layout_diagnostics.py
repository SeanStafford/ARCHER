"""
Layout diagnostics for PDF resume validation.

Compares rendered PDF against expected structure from ResumeDocument
to detect overflow, displacement, and missing sections using character
stream matching.

Detection capabilities:
- Page-to-page overflow: Content flowing from one page to the next
- Cascade effects: When overflow bumps subsequent sections to later pages
- Missing sections: Section header/content not found in expected location

Known limitation - horizontal (cross-column) overflow:
    This module extracts PDF text by column using a fixed split point (leftbarwidth
    from the resume's LaTeX preamble, typically 0.275 of page width). When text
    overflows horizontally past the column boundary (e.g., a long skill list item
    extends into the main column area), those characters are extracted into the
    wrong column. This can cause "section not found" or "end not found" errors
    even when the content is visually present.

    Horizontal overflow is caused by overfull hbox conditions in LaTeX, which
    emit warnings in the compilation log. When diagnostics are ambiguous (missing
    sections without clear page overflow), a feedback loop should re-compile with
    artifacts preserved and parse the .log file for overfull box warnings to
    identify the root cause. See TODO.md section 2 for implementation plan.

Assumption #1: Cascade overflow behavior
    The latex is opinionated about which page content is rendered on. This is
    realized through use of \switchcolumn at each page boundary indicating the intended
    end of the column on that page (for a total of n_cols * n_pages - 1 switches
    throughout the document). A natural consequence of this is synchromized overflow.
    When one column overflows to a new page, ALL columns shift together.
    However, if you let columns flow independently of page breaks and used \switchcolumn
    minimally (n_cols-1 switches throughout the document), then you would see different
    overflow behavior. The columns could overflow out of sync. However, ARCHER considers
    this nonstandard paracol usage and does not support it.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

from archer.contexts.templating.resume_data_structure import ResumeDocument
from archer.utils.pdf_processing import PDFDocument, find_section_header, normalize_for_matching

# Resume-specific font filtering
RESUME_TEXT_FONTS = ["Times", "Arial", "Helvetica", "Courier", "Consolas", "Garamond", "LMMono"]

# Region name -> column index mapping for two-column resume layout
REGIONS = {"left_column": 0, "main_column": 1}

# Character count for prefix/suffix matching
MATCH_LENGTH = 30


class IssueTemplates:
    """Centralized issue message templates (f-string style)."""

    # Document-level
    PAGE_COUNT_MISMATCH = "Page count mismatch: {actual} (expected {intended})"

    # Page-level
    PROFESSIONAL_PROFILE_NOT_FOUND = "Professional profile not found on page 1"

    # Column-level
    COLUMN_OVERFLOW = "'{region}' on page {page} overflowed by {amount} page(s)"
    CONTENT_BELOW_MARGIN = "'{region}' on page {page} has content below bottom margin"

    # Section-level
    BEYOND_PDF = "'{section}' ({region}): expected page does not exist in PDF"
    BEGINNING_NOT_FOUND = (
        "'{section}' ({region}): beginning not found "
        "(intended page {intended}, checked through page {last_checked})"
    )
    END_NOT_FOUND = (
        "'{section}' ({region}): end not found (checked pages {start} through {last_checked})"
    )


# =============================================================================
# Diagnostics Hierarchy
# =============================================================================


@dataclass
class Diagnostics:
    """Base class for hierarchical diagnostics."""

    components: List["Diagnostics"] = field(default_factory=list)

    def get_issues(self) -> List[str]:
        """Generate issues for this level based on field values. Override in subclasses."""
        return []

    def get_inherited_issues(self) -> List[str]:
        """Collect issues from this level and all descendants."""
        all_issues = list(self.get_issues())
        for component in self.components:
            all_issues.extend(component.get_inherited_issues())
        return all_issues

    @property
    def is_valid(self) -> bool:
        """True if no issues at this level or any descendant."""
        return len(self.get_inherited_issues()) == 0


@dataclass
class SectionDiagnostics(Diagnostics):
    """Diagnostics for a single section."""

    section_name: str = ""
    region_name: str = ""
    intended_page: Optional[int] = None
    expected_page: Optional[int] = None  # None means page doesn't exist in PDF
    actual_page: Optional[int] = None
    last_page_checked: Optional[int] = None
    beginning_found: bool = False
    end_found: bool = False
    overflowed_to: Optional[int] = None

    def get_issues(self) -> List[str]:
        issues = []
        if self.expected_page is None:
            issues.append(
                IssueTemplates.BEYOND_PDF.format(
                    section=self.section_name,
                    region=self.region_name,
                )
            )
        elif not self.beginning_found:
            issues.append(
                IssueTemplates.BEGINNING_NOT_FOUND.format(
                    section=self.section_name,
                    region=self.region_name,
                    intended=self.intended_page,
                    last_checked=self.last_page_checked,
                )
            )
        elif not self.end_found:
            issues.append(
                IssueTemplates.END_NOT_FOUND.format(
                    section=self.section_name,
                    region=self.region_name,
                    start=self.actual_page,
                    last_checked=self.last_page_checked,
                )
            )
        return issues


@dataclass
class ColumnDiagnostics(Diagnostics):
    """Diagnostics for a column on a page."""

    region_name: str = ""
    column_idx: int = 0
    intended_page: int = 0
    overflow_amount: int = 0
    content_below_margin: bool = False  # Stub: set during analysis if content exceeds bottom margin

    def get_issues(self) -> List[str]:
        issues = []
        if self.overflow_amount > 0:
            issues.append(
                IssueTemplates.COLUMN_OVERFLOW.format(
                    region=self.region_name,
                    page=self.intended_page,
                    amount=self.overflow_amount,
                )
            )
        if self.content_below_margin:
            issues.append(
                IssueTemplates.CONTENT_BELOW_MARGIN.format(
                    region=self.region_name,
                    page=self.intended_page,
                )
            )
        return issues


@dataclass
class PageDiagnostics(Diagnostics):
    """Diagnostics for a single intended page."""

    intended_page_number: int = 0
    professional_profile_found: Optional[bool] = (
        None  # Only checked on page 1; None = not applicable
    )

    def get_issues(self) -> List[str]:
        issues = []
        # TODO: Professional profile validation not yet implemented.
        # if self.professional_profile_found is False:
        #     issues.append(IssueTemplates.PROFESSIONAL_PROFILE_NOT_FOUND)
        return issues


@dataclass
class DocumentDiagnostics(Diagnostics):
    """Top-level diagnostics for the entire document."""

    actual_page_count: int = 0
    intended_page_count: int = 0

    def get_issues(self) -> List[str]:
        issues = []
        if self.actual_page_count != self.intended_page_count:
            issues.append(
                IssueTemplates.PAGE_COUNT_MISMATCH.format(
                    actual=self.actual_page_count,
                    intended=self.intended_page_count,
                )
            )
        return issues


# =============================================================================
# Helper Functions
# =============================================================================


def _get_section_character_stream(section) -> str:
    """Get normalized character stream for a section's content."""
    return normalize_for_matching(section.text or "")


def _find_section_beginning(
    section_stream: str,
    column_stream: str,
    section_name: str,
    page_lines: List[str],
) -> Optional[int]:
    """
    Find beginning of section in column stream.

    Two conditions must be met:
    1. Section header found as whole line in page_lines
    2. First MATCH_LENGTH chars of section_stream found in column_stream

    Args:
        section_stream: Normalized content from ResumeSection.text
        column_stream: Normalized text from PDF column
        section_name: Section header text to match
        page_lines: Raw text lines from PDF column (for header matching)

    Returns:
        Index in column_stream where content begins, or None if not found.
    """
    header_idx = find_section_header(section_name, page_lines)
    if header_idx is None:
        return None

    if not section_stream:
        return 0

    prefix = section_stream[: min(MATCH_LENGTH, len(section_stream))]
    idx = column_stream.find(prefix)
    return idx if idx >= 0 else None


def _find_section_end(
    section_stream: str,
    column_stream: str,
    begin_idx: int,
) -> bool:
    """
    Check if section's end appears in column stream.

    Searches for last MATCH_LENGTH chars of section_stream in the portion
    of column_stream starting at begin_idx.

    Args:
        section_stream: Normalized content from ResumeSection.text
        column_stream: Normalized text from PDF column (may span multiple pages)
        begin_idx: Index where section beginning was found (search starts here)

    Returns:
        True if section's ending content found, False otherwise.
    """
    if not section_stream:
        return True

    search_region = column_stream[begin_idx:]
    suffix = section_stream[-min(MATCH_LENGTH, len(section_stream)) :]
    return suffix in search_region


def _check_overflow(
    section_stream: str,
    pdf: PDFDocument,
    column_idx: int,
    start_page: int,
    initial_stream: str,
    max_overflows: int = -1,
) -> Optional[int]:
    """
    Check for section end on subsequent pages by extending the search stream.

    Progressively appends content from subsequent pages to initial_stream
    until section end is found or pages are exhausted.

    Args:
        section_stream: Normalized content from ResumeSection.text
        pdf: PDFDocument for extracting page content
        column_idx: Column index to search
        start_page: Page where section begins
        initial_stream: Content from start_page after section beginning
        max_overflows: Max pages to check beyond start_page (-1 = no limit)

    Returns:
        Page number where section end was found, or None if not found.
    """
    last_page_to_check = pdf.page_count if max_overflows < 0 else start_page + max_overflows

    extended_stream = initial_stream
    for end_page in range(start_page + 1, last_page_to_check + 1):
        extended_stream += pdf.get_character_stream(end_page, column_idx)
        if _find_section_end(section_stream, extended_stream, 0):
            return end_page

    return None


# =============================================================================
# Main Analysis Function
# =============================================================================


def analyze_layout(
    yaml_path: Union[str, Path],
    pdf_path: Union[str, Path],
) -> DocumentDiagnostics:
    """
    Analyze PDF layout against expected structure from YAML.

    Builds a hierarchical diagnostics tree (Document -> Page -> Column -> Section)
    by comparing section locations in the PDF against intended locations from YAML.
    Detects page overflow, missing sections, and tracks cascade effects.

    Args:
        yaml_path: Path to structured resume YAML
        pdf_path: Path to compiled PDF

    Returns:
        DocumentDiagnostics tree. Call .get_inherited_issues() for all issues,
        or .is_valid to check if document passes validation.
    """
    yaml_path = Path(yaml_path)
    pdf_path = Path(pdf_path)

    # Load resume structure
    resume_document = ResumeDocument(yaml_path, mode="plaintext")
    intended_page_count = resume_document.page_count
    intended_pages = range(1, intended_page_count + 1)

    # Load PDF with column-based extraction
    pdf = PDFDocument(
        pdf_path,
        column_splits=[resume_document.left_column_ratio],
        allowed_fonts=RESUME_TEXT_FONTS,
    )

    # Initialize document diagnostics
    document_diagnostics = DocumentDiagnostics(
        actual_page_count=pdf.page_count,
        intended_page_count=intended_page_count,
    )

    # Group sections by intended page and region
    sections_by_page_and_region = {
        page_num: {region: [] for region in REGIONS} for page_num in intended_pages
    }
    for section in resume_document.sections:
        sections_by_page_and_region[section.page_number][section.region].append(section)

    # Accumulated offset from overflows on previous pages (shared across columns due to cascade assumption)
    page_offset_from_previous_pages = 0

    # Process each intended page
    for intended_page in intended_pages:
        page_diagnostics = PageDiagnostics(intended_page_number=intended_page)
        max_overflow_on_this_page = 0

        for region_name, column_idx in REGIONS.items():
            sections_in_this_column = sections_by_page_and_region[intended_page][region_name]
            if not sections_in_this_column:
                continue

            column_diagnostics = ColumnDiagnostics(
                region_name=region_name,
                column_idx=column_idx,
                intended_page=intended_page,
            )

            # Within-column offset (resets for each column)
            column_offset_current = 0

            for section in sections_in_this_column:
                section_expected_page = (
                    intended_page + page_offset_from_previous_pages + column_offset_current
                )
                section_expected_page = (
                    None if section_expected_page > pdf.page_count else section_expected_page
                )

                section_diagnostics = SectionDiagnostics(
                    section_name=section.name,
                    region_name=region_name,
                    intended_page=intended_page,
                    expected_page=section_expected_page,
                )

                # Check if beyond PDF pages (expected_page = None signals this)
                if section_expected_page is None:
                    column_diagnostics.components.append(section_diagnostics)
                    continue

                # Get streams for current expected page
                section_stream = _get_section_character_stream(section)
                column_stream = pdf.get_character_stream(section_expected_page, column_idx)
                page_lines = pdf.get_lines(section_expected_page, column_idx)

                # Find beginning
                begin_idx = _find_section_beginning(
                    section_stream, column_stream, section.name, page_lines
                )

                if begin_idx is None:
                    # Try next page (section might have been bumped)
                    if section_expected_page < pdf.page_count:
                        next_page_stream = pdf.get_character_stream(
                            section_expected_page + 1, column_idx
                        )
                        next_page_lines = pdf.get_lines(section_expected_page + 1, column_idx)
                        next_begin_idx = _find_section_beginning(
                            section_stream, next_page_stream, section.name, next_page_lines
                        )
                        if next_begin_idx is not None:
                            # Found on next page - section was bumped
                            column_offset_current += 1
                            section_expected_page += 1
                            column_stream = next_page_stream
                            page_lines = next_page_lines
                            begin_idx = next_begin_idx

                if begin_idx is None:
                    # Section not found
                    section_diagnostics.last_page_checked = min(
                        section_expected_page + 1, pdf.page_count
                    )
                    column_diagnostics.components.append(section_diagnostics)
                    continue

                # Beginning found
                section_diagnostics.beginning_found = True
                section_diagnostics.actual_page = section_expected_page

                # Check for end
                end_found = _find_section_end(section_stream, column_stream, begin_idx)

                if end_found:
                    section_diagnostics.end_found = True
                else:
                    # Check for overflow (end on subsequent pages)
                    # Future: could expose _check_overflow's max_overflows param here (would require
                    # adding new logic to section_diagnostics.last_page_checked determination)
                    initial_stream = column_stream[begin_idx:]
                    overflowed_to_page = _check_overflow(
                        section_stream,
                        pdf,
                        column_idx,
                        section_expected_page,
                        initial_stream,
                    )

                    if overflowed_to_page is not None:
                        section_diagnostics.end_found = True
                        section_diagnostics.overflowed_to = overflowed_to_page
                        overflow_amount = overflowed_to_page - section_expected_page
                        column_offset_current += overflow_amount
                    else:
                        # End not found anywhere - possible horizontal overflow
                        section_diagnostics.last_page_checked = pdf.page_count

                column_diagnostics.components.append(section_diagnostics)

            # Record column overflow amount (get_issues() will generate issue if > 0)
            column_diagnostics.overflow_amount = column_offset_current

            # Track max overflow across columns for this page
            max_overflow_on_this_page = max(max_overflow_on_this_page, column_offset_current)

            page_diagnostics.components.append(column_diagnostics)

        # Apply this page's overflow to cumulative offset for next page
        page_offset_from_previous_pages += max_overflow_on_this_page

        document_diagnostics.components.append(page_diagnostics)

    return document_diagnostics
