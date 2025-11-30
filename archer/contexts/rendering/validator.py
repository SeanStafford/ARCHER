"""
Resume validation with actionable feedback for targeting.

Validates compiled resumes against their structured YAML using layout diagnostics.
Generates actionable feedback reports when validation fails, enabling the
targeting context to make efficient adjustments in the feedback loop.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

from archer.contexts.rendering.layout_diagnostics import (
    DocumentDiagnostics,
    analyze_layout,
)
from archer.contexts.rendering.logger import (
    log_validation_result,
    log_validation_start,
    setup_rendering_logger,
)
from archer.utils.resume_registry import (
    get_resume_file,
    get_resume_status,
    resume_is_registered,
    update_resume_status,
)
from archer.utils.timestamp import now

load_dotenv()

LOGS_PATH = Path(os.getenv("LOGS_PATH"))


@dataclass
class ValidationResult:
    """
    Result of resume validation.

    Attributes:
        is_valid: Whether the resume passes all validation checks
        diagnostics: Layout diagnostics from PDF/YAML comparison
        feedback: Actionable feedback for targeting (only if invalid)
        log_dir: Directory containing validation logs
    """

    is_valid: bool
    diagnostics: DocumentDiagnostics
    feedback: Optional[Dict[str, str]] = None
    log_dir: Optional[Path] = None

    @property
    def issues(self) -> List[str]:
        """All issues from diagnostics hierarchy."""
        return self.diagnostics.get_inherited_issues()

    @property
    def page_count(self) -> int:
        """Actual page count from PDF."""
        return self.diagnostics.actual_page_count


def generate_feedback_report(diagnostics: DocumentDiagnostics) -> str:
    """
    Generate actionable feedback for the targeting context.

    Reports:
    - Sections not found (may indicate horizontal overflow)
    - Column overflows with list of sections in that column
    """
    lines = []

    recommendations_counter = 0
    recommendations_counter_str = "\n#{counter}"

    # Collect all sections not found (across all pages/columns)
    for page_diag in diagnostics.components:
        for column_diag in page_diag.components:
            for section_diag in column_diag.components:
                if not section_diag.end_found:
                    section = section_diag.section_name
                    region = section_diag.region_name
                    page = section_diag.intended_page

                    recommendations_counter += 1
                    lines.append(
                        recommendations_counter_str.format(counter=recommendations_counter)
                    )

                    lines.append(
                        f"issue:section_missing::section:{section}::region:{region}::page:{page}"
                    )
                    lines.append(f"action: Check for horizontal overflow in section '{section}'")

    # Report column overflows
    for page_diag in diagnostics.components:
        for column_diag in page_diag.components:
            if column_diag.overflow_amount > 0:
                page_num = page_diag.intended_page_number
                region = column_diag.region_name

                recommendations_counter += 1
                lines.append(recommendations_counter_str.format(counter=recommendations_counter))
                lines.append(
                    f"issue:column_overflow::region:{region}::page:{page_num}::overflow_amount:{column_diag.overflow_amount}"
                )
                sections_string = ", ".join(f"'{s.section_name}'" for s in column_diag.components)
                lines.append(
                    f"action: Shorten one or more section(s) in this column: {sections_string}"
                )

    return "\n".join(lines)


def validate_resume(resume_name: str) -> ValidationResult:
    """
    Validate a compiled resume against its structured YAML.

    Orchestration function that:
    1. Resolves file paths from the registry
    2. Runs layout diagnostics (PDF vs YAML comparison)
    3. Generates actionable feedback if validation fails
    4. Logs to both Tier 1 (render.log) and Tier 2 (pipeline events)

    Args:
        resume_name: Resume identifier (must be registered)

    Returns:
        ValidationResult with diagnostics and feedback (if invalid)

    Example:
        >>> result = validate_resume("Res202511_MLEng")
        >>> if result.is_valid:
        ...     print("Ready for final approval")
        ... else:
        ...     print(result.feedback)
    """
    # Verify resume is registered
    if not resume_is_registered(resume_name):
        raise ValueError(f"Resume not registered: {resume_name}")

    # Reject validation of historical resumes (read-only reference, already approved)
    if get_resume_status(resume_name).get("resume_type") == "historical":
        raise ValueError(
            "Cannot validate historical resumes (read-only reference, already approved)"
        )

    # Get file paths from registry
    yaml_path = get_resume_file(resume_name, "yaml")
    pdf_path = get_resume_file(resume_name, "pdf")

    # Create timestamped log directory for this validation
    timestamp = now()
    log_dir = LOGS_PATH / f"validate_{timestamp}"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Setup loguru logger with provenance
    log_file = setup_rendering_logger(log_dir)

    # Create symlink in log directory pointing to PDF being validated
    pdf_symlink = log_dir / "resume.pdf"
    pdf_symlink.symlink_to(pdf_path)

    # Log start of validation (Tier 1)
    log_validation_start(resume_name, pdf_path, log_file)

    # Log start of validation to pipeline events (Tier 2)
    update_resume_status(updates={resume_name: "validating"}, source="rendering")

    # Run layout diagnostics
    diagnostics = analyze_layout(yaml_path, pdf_path)

    # Generate feedback if invalid
    feedback = None if diagnostics.is_valid else generate_feedback_report(diagnostics)

    result = ValidationResult(
        is_valid=diagnostics.is_valid,
        diagnostics=diagnostics,
        feedback=feedback,
        log_dir=log_dir,
    )

    # Log validation result (Tier 1)
    log_validation_result(resume_name, result)

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
