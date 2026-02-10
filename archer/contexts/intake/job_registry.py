"""
Job listing registry for tracking parsed jobs in a CSV file.

Provides a simple CSV-based registry at outs/logs/job_registry.csv that stores job identifiers
and metadata. Entries are populated from JobListing instances.
Temporary solution until a database is set up.
"""

import csv
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
REGISTRY_PATH = Path(os.getenv("JOB_REGISTRY"))

# Columns: identifier + common metadata fields
FIELDNAMES = [
    "job_identifier",
    "Company",
    "Role",
    "Location",
    "Salary",
    "Work Mode",
    "Job ID",
    "Source",
    "Clearance",
    "Focus",
    "List Date",
]


def _initialize_registry():
    """Create the registry CSV with headers if it doesn't exist."""
    if REGISTRY_PATH.exists():
        return
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL)
        writer.writeheader()


def _read_registry() -> list[dict]:
    """Read all rows from the registry CSV."""
    _initialize_registry()
    with open(REGISTRY_PATH, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _write_registry(rows: list[dict]):
    """Write rows to the registry CSV."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def register_job(job) -> bool:
    """
    Add a JobListing to the registry. Skips if job_identifier already exists.

    Args:
        job: A JobListing instance with job_identifier and metadata.

    Returns:
        True if added, False if already registered.
    """
    if not job.job_identifier:
        raise ValueError("JobListing must have a job_identifier to register")

    rows = _read_registry()
    existing_ids = {row["job_identifier"] for row in rows}

    if job.job_identifier in existing_ids:
        return False

    row = {"job_identifier": job.job_identifier}
    for key in FIELDNAMES[1:]:
        row[key] = job.metadata.get(key, "")

    rows.append(row)
    _write_registry(rows)
    return True


def register_jobs(jobs) -> tuple[int, int]:
    """
    Register multiple JobListing instances. Skips duplicates.

    Returns:
        Tuple of (added_count, skipped_count).
    """
    rows = _read_registry()
    existing_ids = {row["job_identifier"] for row in rows}

    added = 0
    for job in jobs:
        if not job.job_identifier:
            continue
        if job.job_identifier in existing_ids:
            continue

        row = {"job_identifier": job.job_identifier}
        for key in FIELDNAMES[1:]:
            row[key] = job.metadata.get(key, "")

        rows.append(row)
        existing_ids.add(job.job_identifier)
        added += 1

    if added > 0:
        _write_registry(rows)

    return added, len(jobs) - added if hasattr(jobs, "__len__") else added


def list_registered_jobs() -> list[dict]:
    """Return all registered jobs as list of dicts."""
    return _read_registry()


def is_registered(job_identifier: str) -> bool:
    """Check if a job identifier is already in the registry."""
    rows = _read_registry()
    return any(row["job_identifier"] == job_identifier for row in rows)
