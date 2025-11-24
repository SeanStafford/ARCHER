#!/usr/bin/env python3
"""
View recent pipeline events from resume_pipeline_events.log.

Provides filtered access to the event log with options to filter by
resume name and event type.
"""

import csv
import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

from archer.utils.event_logging import deduce_registry_from_events, get_recent_events
from archer.utils.resume_registry import count_resumes, resume_is_registered
from archer.utils.timestamp import format_timestamp

# Load environment variables
load_dotenv()
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT"))
RESUME_REGISTRY = Path(os.getenv("RESUME_REGISTRY")).relative_to(PROJECT_ROOT)
PIPELINE_EVENTS_FILE = Path(os.getenv("PIPELINE_EVENTS_FILE")).relative_to(PROJECT_ROOT)

app = typer.Typer(
    add_completion=False,
    help="View recent pipeline events",
)


@app.command()
def main(
    n: int = typer.Option(10, "--num", "-n", help="Number of recent events to show"),
    resume: Optional[str] = typer.Option(
        None, "--resume", "-r", help="Filter to events for this resume"
    ),
    event_type: Optional[str] = typer.Option(
        None, "--event-type", "-e", help="Filter to events of this type"
    ),
    compact: bool = typer.Option(
        False, "--compact", "-c", help="Print one event per line (no pretty formatting)"
    ),
):
    """
    Show the last n events from the pipeline log.

    Examples:\n

        $ python scripts/tail_log.py                      # Last 10 events

        $ python scripts/tail_log.py --num 20             # Last 20 events

        $ python scripts/tail_log.py -e status_change     # Last 10 status changes

        $ python scripts/tail_log.py -n 5 -r Res202511    # Last 5 events for specified resume

        $ python scripts/tail_log.py -n 20 --compact      # Compact output (one line per event)
    """
    # Check if resume exists in registry when filtering by resume
    if resume and not resume_is_registered(resume):
        typer.secho(f"Resume '{resume}' not found in registry", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    events = get_recent_events(n=n, resume_name=resume, event_type=event_type)

    if not events:
        typer.secho("No events found", fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(code=1)

    # Show filter info if filters applied (skip header in compact mode)
    if not compact:
        filters = []
        if resume:
            filters.append(f"resume={resume}")
        if event_type:
            filters.append(f"type={event_type}")

        if filters:
            typer.secho(
                f"\nShowing last {len(events)} event(s) [{', '.join(filters)}]:",
                fg=typer.colors.BLUE,
            )
        else:
            typer.secho(f"\nShowing last {len(events)} event(s):", fg=typer.colors.BLUE)

        typer.echo("")

    # Print events
    for event in events:
        if compact:
            typer.echo(json.dumps(event))
        else:
            typer.echo(json.dumps(event, indent=2))
            typer.echo("")


@app.command()
def track(
    resume_name: str = typer.Argument(..., help="Resume name to track"),
    n: int = typer.Option(
        None, "--num", "-n", help="Maximum number of status changes to show (default: all)"
    ),
    relative: bool = typer.Option(
        False, "--relative", "-r", help="Show relative timestamps (e.g., '2 hours ago')"
    ),
):
    """
    Show status history timeline for a resume.

    Displays a vertical timeline of status changes, from oldest to current.

    Examples:\n

        $ python scripts/tail_log.py track Res202506                # Full history

        $ python scripts/tail_log.py track Res202506 -n 5           # Last 5 status changes

        $ python scripts/tail_log.py track Res202506 --relative     # With relative timestamps
    """
    # Check if resume exists in registry
    if not resume_is_registered(resume_name):
        typer.secho(f"Resume '{resume_name}' not found in registry", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # Get all status_change events for this resume
    events = get_recent_events(
        n=n if n else 9999,  # Large number to get all if n not specified
        resume_name=resume_name,
        event_type="status_change",
    )

    if not events:
        typer.secho(f"No status changes found for {resume_name}", fg=typer.colors.YELLOW)
        return

    # Validate status history continuity
    discontinuities = []
    for i in range(1, len(events)):
        prev_new_status = events[i - 1]["new_status"]
        curr_old_status = events[i]["old_status"]
        if prev_new_status != curr_old_status:
            discontinuities.append((i, prev_new_status, curr_old_status))

    # Show warning if discontinuities found
    if discontinuities:
        typer.secho(
            f"\n⚠ Warning: Status history has {len(discontinuities)} discontinuity(ies)",
            fg=typer.colors.RED,
            bold=True,
        )
        for idx, prev, curr in discontinuities:
            typer.secho(
                f"  Event {idx}: expected old_status='{prev}', found '{curr}'", fg=typer.colors.RED
            )
        typer.echo("")

    # Use minimum width of 30 for consistency across resumes
    center_width = max(30, len(resume_name))

    # typer.secho(f"\nStatus history for {resume_name}:", fg=typer.colors.BLUE, bold=True)
    centered = "Status history for".center(30)
    typer.secho(f"\n {centered}", bold=True)
    typer.secho(f" {resume_name}".center(30), fg=typer.colors.BLUE, bold=True)
    typer.echo("")

    # Arrow should be at the center position
    arrow_indent = center_width // 2

    # Display timeline (oldest first)
    for i, event in enumerate(events):
        # Show old status
        typer.echo(event["old_status"].center(center_width))

        # Show arrow with timestamp (arrow centered)
        typer.echo(
            f"{' ' * arrow_indent}↓ {format_timestamp(event['timestamp'], relative=relative)}"
        )

        # For final event, show new status and mark as current
        if i == len(events) - 1:
            centered = event["new_status"].center(center_width)
            # Trim trailing spaces and add suffix within the center_width
            trimmed = centered.rstrip()
            typer.secho(trimmed, nl=False)
            typer.secho(" (current)", fg=typer.colors.GREEN)

    typer.echo("")


@app.command()
def deduce(
    simple: bool = typer.Option(
        False, "--simple", "-s", help="Simple output: skip statistics and next steps"
    ),
):
    """
    Deduce registry from pipeline events and save to file.

    Creates a new registry CSV by analyzing all pipeline events. The output
    file will have '_deduced' suffix to prevent accidental overwrites.
    Saved to the same directory as the events log.

    Examples:\n

        $ python scripts/tail_log.py deduce                    # Deduce and save

        $ python scripts/tail_log.py deduce --simple           # Skip stats and advice
    """
    # Output path: same directory as events log (relative to project root)
    output_path = PIPELINE_EVENTS_FILE.parent / f"{RESUME_REGISTRY.stem}_deduced.csv"

    # Safety check: don't overwrite existing file
    if output_path.exists():
        typer.secho(
            f"\n✗ Error: Output file already exists: {output_path}", fg=typer.colors.RED, err=True
        )
        typer.secho(
            "  Remove it first to generate a fresh deduced registry.\n", fg=typer.colors.RED
        )
        raise typer.Exit(code=1)

    # Deduce registry from events
    typer.secho("\nDeducing Registry from Pipeline Events", fg=typer.colors.BLUE, bold=True)
    typer.echo("=" * 80)

    try:
        registry = deduce_registry_from_events(event_order="ascending")
    except ValueError as e:
        typer.secho(f"\n✗ Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.secho(f"✓ Deduced registry with {len(registry)} resumes", fg=typer.colors.GREEN)

    # Write to CSV
    with open(output_path, "w", newline="") as f:
        fieldnames = ["resume_name", "resume_type", "status", "last_updated"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(registry)

    typer.secho(f"✓ Wrote deduced registry to {output_path}", fg=typer.colors.GREEN)

    # Show statistics (unless --simple)
    if not simple:
        # Get stats from both current and deduced registry
        current_counts = count_resumes()
        deduced_counts = count_resumes(output_path)

        # Check if stats are identical
        stats_identical = (
            current_counts["total"] == deduced_counts["total"]
            and current_counts["by_status"] == deduced_counts["by_status"]
            and current_counts["by_type"] == deduced_counts["by_type"]
        )

        typer.secho("\nRegistry Statistics", fg=typer.colors.YELLOW, bold=True)
        typer.echo("-" * 80)

        if stats_identical:
            typer.echo(
                "Deduced registry and existing registry have identical statistics. (See `make registry-stats`)"
            )
        else:
            typer.echo(f"Total resumes: {deduced_counts['total']}")

            typer.echo("\nBy Status:")
            for status, count in sorted(deduced_counts["by_status"].items()):
                typer.echo(f"  {status:20} {count}")

            typer.echo("\nBy Type:")
            for resume_type, count in sorted(deduced_counts["by_type"].items()):
                typer.echo(f"  {resume_type:20} {count}")

        # Show next steps
        typer.secho("\nNext steps:", fg=typer.colors.YELLOW, bold=True)
        typer.echo("-" * 80)
        typer.echo("  1. Review the deduced registry:")
        typer.echo(f"     cat {output_path}")
        typer.echo("  2. Compare with current registry:")
        typer.echo(f"     diff {RESUME_REGISTRY} {output_path}")
        typer.echo("  3. If correct, replace the registry:")
        typer.echo(f"     mv {output_path} {RESUME_REGISTRY}")
        typer.echo("")
    else:
        typer.echo("")


if __name__ == "__main__":
    # Default to 'main' command if no command specified
    # This allows: python tail_log.py -n 20 (instead of: python tail_log.py main -n 20)
    if len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1].startswith("-")):
        sys.argv.insert(1, "main")
    app()
