"""
Job identifier nomenclature and source resolution for the Intake context.

Handles mapping between job identifiers and their sources (markdown files or databases).
This is a minimal initial implementation; source resolution will be extended as new
backends (e.g., database lookups) are added.

Job Identifier Format (detailed in docs/JOB_NOMENCLATURE_GUIDELINES.md):
    [Title]_[Seniority]_[Focus]_[Company]_[Source]_[ID]

Required: Title, Company. All others optional.

Examples:
    >>> build_job_identifier("ML Engineer", "Acme Corp", job_id="10130042")
    MLEng_AcmeCorp_10130042
    >>> build_job_identifier("Senior Data Scientist", "MomCorp", job_id="R20251101")
    DataSci_Sen_MomCorp_R20251101
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


# =============================================================================
# JOB IDENTIFIER
# =============================================================================


@dataclass
class JobIdentifier:
    """
    Parsed components of a job identifier.

    Format: [Title]_[Seniority]_[Focus]_[Company]_[Source]_[ID]
    Required: title, company. All others optional.
    """

    title: str
    company: str
    seniority: str = ""
    focus: str = ""
    source: str = ""
    job_id: str = ""

    def __str__(self):
        parts = [self.title]
        if self.seniority:
            parts.append(self.seniority)
        if self.focus:
            parts.append(self.focus)
        parts.append(self.company)
        if self.source:
            parts.append(self.source)
        if self.job_id:
            parts.append(self.job_id)
        return "_".join(parts)


# Abbreviation tables loaded from configs/nomenclature.yaml
_config = OmegaConf.load(Path(os.getenv("JOB_NOMENCLATURE_PATH")))
WORD_ABBREVIATIONS = list(_config.word_abbreviations.items())
SENIORITY = dict(_config.seniority)
SENIORITY_MARKERS = set(SENIORITY.values())
COMPANY_ABBREVIATIONS = dict(_config.companies)
COMPANY_SUFFIXES = list(_config.company_suffixes_to_strip)
SOURCE_ABBREVIATIONS = dict(_config.sources)
SOURCE_MARKERS = set(SOURCE_ABBREVIATIONS.values())
del _config


def _infer_seniority(role: str) -> tuple[str, str]:
    """
    Extract seniority prefix from a role title.

    Args:
        role: Role title string (e.g., "Senior Machine Learning Engineer")

    Returns:
        Tuple of (role_without_seniority, seniority_abbreviation).
        Seniority is empty string if not found.
    """
    for term, abbrev in SENIORITY.items():
        if role.startswith(term + " ") or role.startswith(term + ","):
            return role[len(term) :].lstrip(" ,"), abbrev
    return role, ""


def _infer_focus(role: str) -> tuple[str, str]:
    """
    Extract focus area from a role title by splitting on comma or dash separators.

    Matches " - ", " – ", " — ", or "," but NOT bare hyphens in words like "Pre-training".

    Args:
        role: Role title string (e.g., "ML Engineer - Infrastructure")

    Returns:
        Tuple of (role_without_focus, focus_string).
        Focus is empty string if not found.
    """
    parts = re.split(r"\s+[-–—]\s+|,\s*", role, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return role, ""


def _abbreviate_role(role: str) -> str:
    """
    Abbreviate a role title using word abbreviation tables.

    Drops slash-delimited alternatives (e.g., "AI/ML Engineer" → "AI Engineer"),
    applies word abbreviations, and removes whitespace/hyphens.

    Args:
        role: Role title with seniority and focus already stripped

    Returns:
        Concatenated abbreviated title (e.g., "MLEng")
    """
    clean_role = role.strip()

    # Drop slash-delimited alternatives, keeping the first term and the trailing
    # role noun. E.g., "AI/ML Engineer" → drop "ML" → "AI Engineer"
    if "/" in clean_role:
        before_slash = clean_role.split("/")[0]
        after_last_slash = clean_role.split("/")[-1]
        trailing_words = after_last_slash.split()[1:]
        if trailing_words:
            clean_role = before_slash + " " + " ".join(trailing_words)

    # Apply word abbreviations in order
    result = clean_role
    for full_phrase, abbrev in WORD_ABBREVIATIONS:
        result = result.replace(full_phrase, abbrev)

    # Remove spaces and hyphens to form concatenated abbreviation
    return result.replace(" ", "").replace("-", "")


def _abbreviate_company(company: str) -> str:
    """Abbreviate a company name using known abbreviations, or strip punctuation and suffixes."""
    if company in COMPANY_ABBREVIATIONS:
        return COMPANY_ABBREVIATIONS[company]
    cleaned = re.sub(r"[,.\-']", "", company)
    for suffix in COMPANY_SUFFIXES:
        cleaned = re.sub(rf"\s+{re.escape(suffix)}$", "", cleaned)
    cleaned = cleaned.replace(" ", "")
    return cleaned


def build_job_identifier(
    role: str,
    company: str,
    *,
    seniority: str = "",
    focus: str = "",
    source: str = "",
    job_id: str = "",
) -> Optional[JobIdentifier]:
    """
    Build a job identifier from role and company, with optional components.

    Abbreviates role and company as specified in nomeclature config. If seniority
    or focus are not provided, attempts to infer them from role title.

    Args:
        role: Full role title (e.g., "Senior Machine Learning Engineer - Infrastructure")
        company: Company name
        seniority: Seniority level. If empty, inferred from role.
        focus: Focus area. If empty, inferred from role.
        source: Third-party source name (e.g., "LinkedIn")
        job_id: Job requisition ID

    Returns:
        JobIdentifier with abbreviated components, or None if role or company is empty
    """

    if not role or not company:
        return None

    clean_role = role.strip()
    clean_role, inferred_seniority = _infer_seniority(clean_role)
    clean_role, inferred_focus = _infer_focus(clean_role)
    title_abbrev = _abbreviate_role(clean_role)
    company_abbrev = _abbreviate_company(company)

    # Map source to abbreviation if it's a known third-party
    source_abbrev = SOURCE_ABBREVIATIONS.get(source, source)

    return JobIdentifier(
        title=title_abbrev,
        company=company_abbrev,
        seniority=seniority or inferred_seniority,
        focus=focus or inferred_focus,
        source=source_abbrev,
        job_id=job_id,
    )


def parse_identifier(identifier: str) -> JobIdentifier:
    """
    Parse job identifier string into components.

    This is a best-effort parser — identifiers don't have a strict grammar.

    Args:
        identifier: Job identifier string (e.g., "MLEng_Sen_AcmeCorp_10130042")

    Returns:
        JobIdentifier with parsed components (fields may be empty)
    """
    parts = identifier.split("_")

    if not parts:
        return JobIdentifier(title="", company="")

    title = parts[0]
    seniority = ""
    focus = ""
    company = ""
    source = ""
    job_id = ""

    # Peel off from the end: last part is requisition ID
    if len(parts) > 1:
        job_id = parts[-1]
        parts = parts[:-1]

    # Check if new last part is a known source marker
    if len(parts) > 1 and parts[-1] in SOURCE_MARKERS:
        source = parts[-1]
        parts = parts[:-1]

    # Next from end is company
    if len(parts) > 1:
        company = parts[-1]
        parts = parts[:-1]

    # Remaining middle parts are seniority/focus
    if len(parts) > 1:
        for part in parts[1:]:
            if part in SENIORITY_MARKERS:
                seniority = part
            else:
                focus = part

    return JobIdentifier(
        title=title,
        company=company,
        seniority=seniority,
        focus=focus,
        source=source,
        job_id=job_id,
    )


def identifier_from_filename(filename: str) -> str:
    """
    Extract job identifier from a filename.

    Args:
        filename: Filename with or without extension (e.g., "MLEng_AcmeCorp_10130042.md")

    Returns:
        Job identifier (filename stem)
    """
    return Path(filename).stem
