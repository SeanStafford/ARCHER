"""
PDF validation for compiled resumes.

Validates PDF quality including page count, content density, and layout constraints.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from PyPDF2 import PdfReader

from archer.contexts.rendering.logger import (
    log_validation_result,
    log_validation_start,
    setup_rendering_logger,
)
from archer.utils.resume_registry import resume_is_registered, update_resume_status
from archer.utils.timestamp import now

load_dotenv()

LOGS_PATH = Path(os.getenv("LOGS_PATH"))


@dataclass
class ValidationResult:
    """
    Result of PDF validation.

    Attributes:
        is_valid: Whether the PDF passes all validation checks
        page_count: Number of pages in the PDF
        issues: List of validation issues found (warnings or errors)
    """

    is_valid: bool
    page_count: int
    issues: List[str] = field(default_factory=list)


def validate_pdf(pdf_path: Path, expected_pages: int = 2) -> ValidationResult:
    """
    Validate a compiled resume PDF.

    Checks:
    - PDF file exists and is readable
    - Page count matches expected value (default: 2 pages)

    Args:
        pdf_path: Path to the PDF file to validate
        expected_pages: Expected number of pages (default: 2 for ARCHER resumes)

    Returns:
        ValidationResult with validation status and any issues found

    Example:
        >>> result = validate_pdf(Path("resume.pdf"))
        >>> if result.is_valid:
        ...     print(f"Valid PDF with {result.page_count} pages")
        ... else:
        ...     print(f"Issues: {result.issues}")
    """
    issues = []
    page_count = 0

    # Check if PDF exists
    if not pdf_path.exists():
        return ValidationResult(is_valid=False, page_count=0, issues=["PDF file not found"])

    # Check if PDF is readable and count pages
    try:
        reader = PdfReader(str(pdf_path))
        page_count = len(reader.pages)

    except Exception as e:
        return ValidationResult(
            is_valid=False, page_count=0, issues=[f"Failed to read PDF: {str(e)}"]
        )

    # Validate page count
    if page_count != expected_pages:
        issue = f"Page count mismatch: expected {expected_pages} pages, got {page_count} pages"
        issues.append(issue)

    # Determine overall validity
    is_valid = len(issues) == 0

    return ValidationResult(is_valid=is_valid, page_count=page_count, issues=issues)


def validate_resume(
    resume_name: str,
    pdf_path: Path,
    expected_pages: int = 2,
    verbose: bool = False,
) -> ValidationResult:
    """
    Validate a compiled resume PDF with registry tracking and logging.

    Orchestration function that wraps validate_pdf() with ARCHER-specific
    resume tracking via the registry system. Logs status changes to the
    pipeline event log (Tier 2 logging) and detailed validation results
    to render.log (Tier 1 logging).

    Args:
        resume_name: Resume identifier (must be registered)
        pdf_path: Path to the PDF file to validate
        expected_pages: Expected number of pages (default: 2 for ARCHER resumes)
        verbose: Show detailed validation issues (default: False)

    Returns:
        ValidationResult with validation status and any issues found

    Example:
        >>> from pathlib import Path
        >>> result = validate_resume(
        ...     "Res202511_MLEng", Path("data/resumes/experimental/compiled/Res202511_MLEng.pdf")
        ... )
        >>> print(f"Valid: {result.is_valid}, Pages: {result.page_count}")
    """
    pdf_path = Path(pdf_path).resolve()

    # Early validation before any registry updates
    if not pdf_path.exists():
        return ValidationResult(is_valid=False, page_count=0, issues=[f"PDF file not found: {pdf_path}"])

    # Verify resume is registered
    if not resume_is_registered(resume_name):
        return ValidationResult(is_valid=False, page_count=0, issues=[f"Resume not registered: {resume_name}"])

    # Create timestamped log directory for this validation
    timestamp = now()
    log_dir = LOGS_PATH / f"validate_{timestamp}"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Setup loguru logger with provenance
    setup_rendering_logger(log_dir)

    # Create symlink in log directory pointing to PDF being validated
    pdf_symlink = log_dir / "resume.pdf"
    pdf_symlink.symlink_to(pdf_path)

    # Log start of validation (Tier 1)
    log_validation_start(resume_name, pdf_path)

    # Log start of validation to pipeline events by setting status to 'validating' (Tier 2)
    update_resume_status(updates={resume_name: "validating"}, source="rendering")

    # Perform validation
    result = validate_pdf(pdf_path, expected_pages=expected_pages)

    # Log validation result (Tier 1)
    log_validation_result(resume_name, result, verbose=verbose)

    # Log result to pipeline events (Tier 2)
    if result.is_valid:
        update_resume_status(
            updates={resume_name: "validating_completed"},
            source="rendering",
            page_count=result.page_count,
        )
    else:
        update_resume_status(
            updates={resume_name: "validating_failed"},
            source="rendering",
            page_count=result.page_count,
            validation_issues=result.issues,
        )

    return result
