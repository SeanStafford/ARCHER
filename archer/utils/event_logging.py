"""
Pipeline event logging utilities for ARCHER (Tier 2 logging).

Provides uniform interfaces for logging pipeline events to resume_pipeline_events.log.
This is for cross-context coordination via JSON Lines event log.

For detailed within-context logging (Tier 1), use archer.utils.logger instead.

Usage:
    from archer.utils.event_logging import log_status_change, log_pipeline_event

    # Update status with automatic event logging
    log_status_change(
        resume_name="Res202511",
        new_status="completed",
        source="rendering"
    )

    # Log custom pipeline event
    log_pipeline_event(
        event_type="parsing_started",
        resume_name="Res202506",
        source="templating",
        input_file="Res202506.tex"
    )
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

from archer.utils.timestamp import now_exact

load_dotenv()
LOGS_PATH = Path(os.getenv("LOGS_PATH", "outs/logs"))
PIPELINE_EVENTS_FILE = Path(os.getenv("PIPELINE_EVENTS_FILE"))

# Event types that mutate registry state
MUTATIVE_EVENTS = {"registration", "status_change"}

# Map event types to their status field names
STATUS_FIELD_BY_EVENT_TYPE = {
    "status_change": "new_status",
    "registration": "status",
}


def log_pipeline_event(event_type: str, resume_name: str, source: str, **extra_fields) -> None:
    """
    Log an event to the master pipeline event log.

    Events are appended to resume_pipeline_events.log in JSON Lines format
    (one JSON object per line). This enables streaming processing and easy
    filtering by event_type, resume_name, or source.

    Args:
        event_type: Type of event (e.g., "status_changed", "render_completed", "parsing_started")
        resume_name: Resume identifier
        source: Event source (e.g., "rendering", "templating", "cli", "manual")
        **extra_fields: Additional event-specific fields

    Example:
        log_pipeline_event(
            event_type="render_completed",
            resume_name="Res202511",
            source="rendering",
            success=True,
            compilation_time_s=3.2,
            warnings=3
        )
    """
    LOGS_PATH.mkdir(parents=True, exist_ok=True)

    event = {
        "timestamp": now_exact(),
        "event_type": event_type,
        "resume_name": resume_name,
        "source": source,
        **extra_fields,
    }

    # Append to pipeline event log (JSON Lines format)
    with open(PIPELINE_EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def log_status_change(
    resume_name: str, old_status: str, new_status: str, source: str, **extra_fields
) -> None:
    """
    Log status change event.

    Pure logging function - does NOT update the registry.
    Called by registry functions after they update the CSV.

    Args:
        resume_name: Resume identifier
        old_status: Previous status
        new_status: New status value (see docs/RESUME_STATUS_REFERENCE.md)
        source: Event source (e.g., "rendering", "templating", "cli", "manual")
        **extra_fields: Additional event-specific fields (e.g., error_message, compilation_time_s)
    """
    log_pipeline_event(
        event_type="status_change",
        resume_name=resume_name,
        old_status=old_status,
        new_status=new_status,
        source=source,
        **extra_fields,
    )


def get_recent_events(
    n: int = 10, resume_name: Optional[str] = None, event_type: Optional[str] = None
) -> list[dict]:
    """
    Get the last n events from the pipeline log, optionally filtered.

    Args:
        n: Number of recent events to return (default: 10)
        resume_name: Filter to only events for this resume (optional)
        event_type: Filter to only events of this type (optional)

    Returns:
        List of event dicts (most recent last)

    Example:
        # Last 10 events
        events = get_recent_events(10)

        # Last 20 status changes
        events = get_recent_events(20, event_type="status_change")

        # Last 5 events for specific resume
        events = get_recent_events(5, resume_name="Res202511")

        # Last 10 status changes for specific resume
        events = get_recent_events(10, resume_name="Res202511", event_type="status_change")
    """
    if not PIPELINE_EVENTS_FILE.exists():
        return []

    # Read all events from file
    events = []
    with open(PIPELINE_EVENTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                event = json.loads(line.strip())
                events.append(event)
            except json.JSONDecodeError:
                # Skip malformed lines
                continue

    # Apply filters
    if resume_name:
        events = [e for e in events if e.get("resume_name") == resume_name]

    if event_type:
        events = [e for e in events if e.get("event_type") == event_type]

    # Return last n events
    return events[-n:] if len(events) > n else events


def get_status_from_event(event: Dict) -> str:
    """Extract status from event based on event type."""
    event_type = event["event_type"]
    status_field = STATUS_FIELD_BY_EVENT_TYPE[event_type]
    return event[status_field]


def deduce_registry_from_events(event_order: str = "ascending") -> List[Dict[str, str]]:
    """
    Deduce registry state from pipeline events.

    Rebuilds registry by analyzing all pipeline events and determining
    the correct status and timestamp for each resume based on the most
    recent mutative event (registration or status_change).

    Args:
        event_order: Chronological order of events in log ("ascending" or "descending")
                    Default: "ascending" (oldest first, newest last)

    Returns:
        List of registry_entry dicts, each containing: resume_name, resume_type, status, and last_updated
        Sorted by registration order (chronological).

    Raises:
        ValueError: If event_order is not "ascending" or "descending"
        ValueError: If events are not in the specified chronological order
        ValueError: If no mutative events found for a registered resume
    """

    if event_order not in ("ascending", "descending"):
        raise ValueError(f"event_order must be 'ascending' or 'descending', got: {event_order}")

    # Load all events
    events = []
    with open(PIPELINE_EVENTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                event = json.loads(line.strip())
                events.append(event)
            except json.JSONDecodeError:
                # Skip malformed lines
                continue

    # Initialize registry from registration events (chronological order)
    registry = []
    for event in events:
        if event.get("event_type") == "registration":
            resume_name = event["resume_name"]
            resume_type = event["resume_type"]
            registry.append(
                {
                    "resume_name": resume_name,
                    "resume_type": resume_type,
                }
            )

    # Update each resume with most recent mutative event
    for resume_entry in registry:
        resume_name = resume_entry["resume_name"]
        # Get most recent mutative event for this resume
        pipeline_events = [
            event
            for event in events
            if event.get("resume_name") == resume_name
            and event.get("event_type") in MUTATIVE_EVENTS
        ]

        if not pipeline_events:
            raise ValueError(f"No mutative events found for registered resume: {resume_name}")
        elif len(pipeline_events) > 1:  # Verify events are in chronological order (sanity check)
            timestamps = [event["timestamp"] for event in pipeline_events]
            expected_order = (
                sorted(timestamps)
                if event_order == "ascending"
                else sorted(timestamps, reverse=True)
            )
            if timestamps != expected_order:
                raise ValueError(
                    f"Events are not in {event_order} chronological order for resume: {resume_name}. "
                    f"This indicates corruption in the pipeline events log."
                )

        # Get most recent event based on order
        most_recent = pipeline_events[-1] if event_order == "ascending" else pipeline_events[0]

        # Extract status from event
        status = get_status_from_event(most_recent)

        resume_entry["status"] = status
        resume_entry["last_updated"] = most_recent["timestamp"]

    return registry
