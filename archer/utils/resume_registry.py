"""
Resume Registry Management

Provides authoritative source for resume names and status tracking.
Registry stored as CSV at outs/logs/resume_registry.csv.

Schema:
    resume_name (str): Unique identifier (PRIMARY KEY)
    resume_type (str): Category ("historical", "generated", or "test")
    status (str): Pipeline status ("targeting", "templating", "rendering", "completed", "failed")
    last_updated (str): ISO 8601 timestamp of last modification

Usage:
    from archer.utils.resume_registry import register_resume, update_resume_status

    # Register new resume
    register_resume("Res202510", resume_type="generated", status="targeting")

    # Update status
    update_resume_status("Res202510", "completed")
"""

import csv
import os
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from typing import Optional, List, Dict

from dotenv import load_dotenv

from archer.utils.event_logging import log_pipeline_event, log_status_change
from archer.utils.timestamp import now_exact

load_dotenv()
REGISTRY_FILE = Path(os.getenv("RESUME_REGISTRY"))
REGISTRY_COLUMNS = ['resume_name', 'resume_type', 'status', 'last_updated']


def ensure_registry_exists() -> None:
    """Create registry file with header if it doesn't exist."""
    if not REGISTRY_FILE.exists():
        REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(REGISTRY_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(REGISTRY_COLUMNS)


# Initialize registry on module load
ensure_registry_exists()


def resume_is_registered(resume_name: str) -> bool:
    """Check if a resume is already registered."""
    with open(REGISTRY_FILE, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['resume_name'] == resume_name:
                return True
    return False


def register_resume(
    resume_name: str,
    resume_type: str,
    source: str,
    status: str = "raw"
) -> None:
    """
    Register a new resume in the registry and log the event.

    For manual registrations (source="manual"), prompts for an optional reason
    that will be included in the registration event log.

    Args:
        resume_name: Unique identifier (e.g., "Res202510")
        resume_type: Resume category ("historical", "generated", or "test")
        source: Event source (e.g., "cli", "templating", "manual")
        status: Initial status (default: "raw")

    Raises:
        ValueError: If resume_name already exists
        KeyboardInterrupt: If user aborts during manual registration prompt
    """
    # Check if resume already exists
    if resume_is_registered(resume_name):
        raise ValueError(f"Resume '{resume_name}' already registered")

    # Log registration event (include reason if provided)
    event_data = {
        "event_type": "registration",
        "resume_name": resume_name,
        "source": source,
        "resume_type": resume_type,
        "status": status
    }

    # Interactive prompt for manual registrations
    reason = None
    if source == "manual":
        try:
            reason_input = input(
                "Reason for manual registration (press Enter to skip, Ctrl+C to abort): "
            ).strip()
            if reason_input:
                event_data["reason"] = reason_input
        except KeyboardInterrupt:
            print("\n✗ Registration aborted by user")
            raise

    # Append new entry with current timestamp
    timestamp = now_exact()
    with open(REGISTRY_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([resume_name, resume_type, status, timestamp])

    log_pipeline_event(**event_data)


def update_resume_status(
    updates: Dict[str, str],
    source: str,
    **extra_fields
) -> Dict[str, bool]:
    """
    Update status for one or more resumes and log events.

    Avoids I/O thrashing by reading once, updating in memory, writing once.
    Logs a status_change event for each successful update.

    Args:
        updates: Dict mapping resume_name → new_status
                 e.g., {"Res202506_...": "parsed"} for single update
                 or {"Res202506_...": "parsed", "Res202507_...": "parsed"} for batch
        source: Event source (e.g., "cli", "templating", "rendering")
        **extra_fields: Additional fields to include in status_change events

    Returns:
        Dict mapping resume_name → success (True if updated, False if not found)

    Examples:
        # Single update
        result = update_resume_status(
            updates={"Res202510": "parsed"},
            source="templating"
        )
        # result = {"Res202510": True}

        # Batch update with extra fields
        updated = update_resume_status(
            updates={
                "Res202508": "parsed",
                "Res202510": "parsed",
                "Res202511": "parsing_failed"
            },
            source="templating",
            batch_id="20251113_153045"
        )
        # updated = {"Res202508": True, "Res202510": True, "Res202511": True}
    """
    # Read all entries and track old statuses
    rows = []
    timestamp = now_exact()
    updated = {resume_name: False for resume_name in updates}
    old_statuses = {}

    with open(REGISTRY_FILE, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            resume_name = row['resume_name']
            if resume_name in updates:
                old_statuses[resume_name] = row['status']
                row['status'] = updates[resume_name]
                row['last_updated'] = timestamp
                updated[resume_name] = True
            rows.append(row)

    # Write to temp file first (atomic write pattern)
    temp_fd, temp_path = tempfile.mkstemp(suffix='.csv', text=True)
    try:
        with os.fdopen(temp_fd, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=REGISTRY_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

        # Only overwrite original if write succeeded
        shutil.move(temp_path, REGISTRY_FILE)
    except Exception:
        # Clean up temp file if write failed
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

    # Log status_change events for each successful update
    for resume_name, was_updated in updated.items():
        if was_updated:
            log_status_change(
                resume_name=resume_name,
                old_status=old_statuses[resume_name],
                new_status=updates[resume_name],
                source=source,
                **extra_fields
            )

    return updated



def get_resume_status(resume_name: str) -> Optional[Dict[str, str]]:
    """
    Get the full registry entry for a resume.

    Returns:
        Dict with resume metadata, or None if not found
    """
    with open(REGISTRY_FILE, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['resume_name'] == resume_name:
                return dict(row)
    return None


def list_resumes_by_status(status: str) -> List[Dict[str, str]]:
    """Get all resumes with a specific status."""
    resumes = []
    with open(REGISTRY_FILE, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['status'] == status:
                resumes.append(dict(row))
    return resumes


def list_resumes_by_type(resume_type: str) -> List[Dict[str, str]]:
    """Get all resumes with a specific type."""
    resumes = []
    with open(REGISTRY_FILE, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['resume_type'] == resume_type:
                resumes.append(dict(row))
    return resumes


def get_all_resumes() -> List[Dict[str, str]]:
    """Get all registered resumes."""
    resumes = []
    with open(REGISTRY_FILE, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            resumes.append(dict(row))
    return resumes


def count_resumes() -> Dict[str, int]:
    """
    Get counts of resumes by status and type.

    Returns:
        Dict with total count, counts by status, and counts by type
    """
    all_resumes = get_all_resumes()

    by_status = Counter()
    by_type = Counter()
    for resume in all_resumes:
        by_status[resume['status']] += 1
        by_type[resume['resume_type']] += 1

    return {
        'total': len(all_resumes),
        'by_status': by_status,
        'by_type': by_type
    }
