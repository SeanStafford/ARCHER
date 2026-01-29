"""
Heuristic metadata extraction from raw job markdown.

Attempts to extract job metadata fields using pattern matching before
falling back to LLM extraction. This module has no LLM dependencies.
"""

from pathlib import Path

from archer.contexts.intake.extraction_patterns import (
    JOB_ID_PATTERNS,
    LOCATION_PATTERNS,
    LocationPatterns,
    MetadataPatterns,
    SalaryPatterns,
)


def extract_metadata_heuristic(text: str, filename: str | None = None) -> dict[str, str]:
    """
    Extract metadata from raw markdown using heuristics.

    Args:
        text: Raw job description markdown
        filename: Optional filename for additional hints (e.g., MLEng_Disney_12345.md)

    Returns:
        Dict of field name to extracted value (only includes fields with values)
    """
    metadata = {}

    # Extract from filename if provided
    if filename:
        filename_meta = _extract_from_filename(filename)
        metadata.update(filename_meta)

    # Extract from text content
    text_meta = _extract_from_text(text)

    # Text extraction takes precedence over filename hints
    for field, value in text_meta.items():
        if value:
            metadata[field] = value

    return metadata


def _extract_from_filename(filename: str) -> dict[str, str]:
    """
    Extract hints from filename pattern.

    Expected patterns:
    - Role_Company_JobID.md (e.g., MLEng_Disney_12345.md)
    - Role_Company.md
    """
    metadata = {}

    # Remove extension
    stem = Path(filename).stem

    # Split by underscore
    parts = stem.split("_")

    if len(parts) >= 2:
        # Last part might be job ID if it looks like one
        if len(parts) >= 3 and _looks_like_job_id(parts[-1]):
            metadata["Job ID"] = parts[-1]
            # Second to last is likely company
            metadata["Company"] = parts[-2].replace("-", " ")
        else:
            # Last part is likely company
            metadata["Company"] = parts[-1].replace("-", " ")

    return metadata


def _looks_like_job_id(s: str) -> bool:
    """Check if string looks like a job ID (alphanumeric, often with numbers)."""
    if not s:
        return False
    # Job IDs typically have numbers and are relatively short
    has_digit = any(c.isdigit() for c in s)
    reasonable_length = 4 <= len(s) <= 30
    return has_digit and reasonable_length


def _extract_from_text(text: str) -> dict[str, str]:
    """Extract metadata fields from markdown text content."""
    metadata = {}

    # Extract role from first heading
    role = _extract_role_from_heading(text)
    if role:
        metadata["Role"] = role

    # Extract bold metadata fields
    bold_meta = _extract_bold_metadata(text)
    metadata.update(bold_meta)

    # Extract salary
    salary = _extract_salary(text)
    if salary:
        metadata["Salary"] = salary

    # Extract location
    location = _extract_location(text)
    if location:
        metadata["Location"] = location

    # Extract work mode
    work_mode = _extract_work_mode(text)
    if work_mode:
        metadata["Work Mode"] = work_mode

    # Extract job ID
    job_id = _extract_job_id(text)
    if job_id:
        metadata["Job ID"] = job_id

    return metadata


def _extract_role_from_heading(text: str) -> str | None:
    """Extract role from first # heading."""
    lines = text.strip().split("\n")
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _extract_bold_metadata(text: str) -> dict[str, str]:
    """Extract **Field:** Value patterns."""
    metadata = {}

    # Map of lowercase field names to canonical names
    field_map = {
        "company": "Company",
        "role": "Role",
        "title": "Role",
        "position": "Role",
        "location": "Location",
        "salary": "Salary",
        "pay": "Salary",
        "compensation": "Salary",
        "source": "Source",
        "url": "URL",
        "link": "URL",
        "job id": "Job ID",
        "job_id": "Job ID",
        "requisition": "Job ID",
        "req id": "Job ID",
        "clearance": "Clearance",
        "security clearance": "Clearance",
        "work mode": "Work Mode",
        "remote": "Work Mode",
        "date posted": "Date Posted",
        "posted": "Date Posted",
    }

    for match in MetadataPatterns.BOLD_FIELD.finditer(text):
        field_raw = match.group(1).strip().lower()
        value = match.group(2).strip()

        canonical = field_map.get(field_raw)
        if canonical and value:
            metadata[canonical] = value

    return metadata


def _extract_salary(text: str) -> str | None:
    """Extract salary range from text."""
    match = SalaryPatterns.SALARY_RANGE.search(text)
    if match:
        return match.group(0)
    return None


def _extract_location(text: str) -> str | None:
    """Extract location from text."""
    # Try city/state patterns only (not work mode)
    for pattern in LOCATION_PATTERNS[:2]:
        match = pattern.search(text)
        if match:
            return f"{match.group(1)}, {match.group(2)}"
    return None


def _extract_work_mode(text: str) -> str | None:
    """Extract work mode (Remote/Hybrid/On-site)."""
    match = LocationPatterns.WORK_MODE.search(text)
    if match:
        mode = match.group(1).lower()
        # Normalize
        if mode in ("remote",):
            return "Remote"
        elif mode in ("hybrid",):
            return "Hybrid"
        elif mode in ("onsite", "on-site", "inoffice", "in-office"):
            return "On-site"
    return None


def _extract_job_id(text: str) -> str | None:
    """Extract job ID from text."""
    for pattern in JOB_ID_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None
