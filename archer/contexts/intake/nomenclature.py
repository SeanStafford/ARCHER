"""
Job identifier nomenclature and source resolution for the Intake context.

Handles mapping between job identifiers and their sources (markdown files or databases).
This is a minimal initial implementation; source resolution will be extended as new
backends (e.g., database lookups) are added.

Job Identifier Format (from docs/NORMALIZED_JOB.md):
    [JobIdentifier]_[ID]

Where JobIdentifier = [Title]_[Seniority]_[Focus]_[Company]

Examples:
    MLEng_AcmeCorp_10130042
    TPSReportCollator_Sen_Initech_R0229614
    DataSci_MomCorp_R20251101
"""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# Environment paths
DATA_PATH = Path(os.getenv("DATA_PATH", "data"))
JOBS_PATH = DATA_PATH / "jobs"


class JobSource(Enum):
    """Source type for a job listing."""

    MARKDOWN = "markdown"
    DATABASE = "database"


@dataclass
class JobSourceInfo:
    """Information about where a job listing comes from."""

    source: JobSource
    identifier: str
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    file_path: Optional[Path] = None


def identifier_from_filename(filename: str) -> str:
    """
    Extract job identifier from a filename.

    Args:
        filename: Filename with or without extension (e.g., "MLEng_AcmeCorp_10130042.md")

    Returns:
        Job identifier (filename stem)
    """
    return Path(filename).stem


def parse_identifier(identifier: str) -> dict:
    """
    Parse job identifier into components.

    This is a best-effort parser - identifiers don't have a strict grammar.

    Args:
        identifier: Job identifier string

    Returns:
        Dict with parsed components (may be incomplete)
    """
    parts = identifier.split("_")

    result = {
        "raw": identifier,
        "title": None,
        "seniority": None,
        "focus": None,
        "company": None,
        "source": None,
        "requisition_id": None,
    }

    if not parts:
        return result

    # Known sources (third-party job boards and staffing agencies)
    known_sources = {"LI", "Indeed", "GH", "ICONMA", "Hired"}
    # Known seniority markers
    seniority_markers = {
        "Sen",
        "Prin",
        "Staff",
        "Lead",
        "Head",
        "Mid",
        "Jr",
        "Junior",
        "Senior",
        "Chief",
        "I",
        "II",
        "III",
        "IV",
        "V",
    }

    # First part is always title
    result["title"] = parts[0]

    # Last part is always requisition ID
    if len(parts) > 1:
        result["requisition_id"] = parts[-1]
        parts = parts[:-1]

    # Check if second-to-last (after removing req ID) is a known source
    if len(parts) > 1 and parts[-1] in known_sources:
        result["source"] = parts[-1]
        parts = parts[:-1]

    # Next part from end is company
    if len(parts) > 1:
        result["company"] = parts[-1]
        parts = parts[:-1]

    # Middle parts are seniority/focus
    if len(parts) > 1:
        for part in parts[1:]:
            if part in seniority_markers:
                result["seniority"] = part
            else:
                # Assume it's focus
                result["focus"] = part

    return result


def find_markdown_job(identifier: str) -> Optional[Path]:
    """
    Find markdown file for a job identifier.

    Searches data/jobs/ for a matching file.

    Args:
        identifier: Job identifier (filename stem)

    Returns:
        Path to markdown file, or None if not found
    """
    # Try exact match first
    exact_path = JOBS_PATH / f"{identifier}.md"
    if exact_path.exists():
        return exact_path

    # Try case-insensitive search
    for path in JOBS_PATH.glob("*.md"):
        if path.stem.lower() == identifier.lower():
            return path

    return None


def resolve_job_source(identifier: str) -> Optional[JobSourceInfo]:
    """
    Resolve a job identifier to its source and data.

    Tries markdown files first, then databases.

    Args:
        identifier: Job identifier

    Returns:
        JobSourceInfo with resolved data, or None if not found
    """
    # Try markdown first
    md_path = find_markdown_job(identifier)
    if md_path:
        text = md_path.read_text()
        # Extract title from first line
        first_line = text.split("\n")[0].strip().lstrip("#").strip()
        return JobSourceInfo(
            source=JobSource.MARKDOWN,
            identifier=identifier,
            title=first_line,
            description=text,
            file_path=md_path,
        )

    # TODO: Database source resolution (not yet implemented)
    return None


def get_job_text(identifier: str) -> Optional[str]:
    """
    Get job description text for an identifier.

    Convenience function that resolves source and returns description.

    Args:
        identifier: Job identifier

    Returns:
        Job description text, or None if not found
    """
    source_info = resolve_job_source(identifier)
    if source_info:
        return source_info.description
    return None
