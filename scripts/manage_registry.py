#!/usr/bin/env python3
"""
Command-line interface for managing the resume registry.

The resume registry (outs/logs/resume_registry.csv) tracks all resumes and their
pipeline status. This script provides commands for initialization, querying, and
manual status updates.

Commands:
    init     - Initialize registry with historical resumes
    register - Register new test or experimental resume
    list     - List resumes (optionally filter by status/type)
    stats    - Show registry statistics
    status   - Get status of a specific resume
    update   - Manually update resume status
    locate   - Get file path for a resume by identifier
"""

import os
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

from archer.utils.resume_registry import (
    EXPERIMENTAL_STATUSES,
    TEST_STATUSES,
    count_resumes,
    get_all_resumes,
    get_resume_file,
    get_resume_status,
    list_resumes_by_status,
    list_resumes_by_type,
    prompt_for_reason,
    register_resume,
    resume_is_registered,
    update_resume_status,
)

load_dotenv()
RESUME_ARCHIVE_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH"))
STRUCTURED_ARCHIVE_PATH = Path(os.getenv("STRUCTURED_ARCHIVE_PATH"))
RAW_ARCHIVE_PATH = Path(os.getenv("RAW_ARCHIVE_PATH"))

app = typer.Typer(
    add_completion=False,
    help="Manage the resume registry (resume_registry.csv)",
    invoke_without_command=True,
)


@app.callback()
def main(ctx: typer.Context):
    """Show help by default when no command is provided."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def _infer_archive_status(resume_name: str) -> str:
    """
    Determine status based on file existence.

    Logic:
    - If YAML exists in structured/ → parsed
    - Else if .tex exists in archive/ → normalized
    - Else → raw
    """
    yaml_file = STRUCTURED_ARCHIVE_PATH / f"{resume_name}.yaml"
    tex_file = RESUME_ARCHIVE_PATH / f"{resume_name}.tex"

    if yaml_file.exists():
        return "parsed"
    elif tex_file.exists():
        return "normalized"
    else:
        return "raw"


@app.command("init")
def init_command(
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be registered without making changes"
    ),
):
    """
    Initialize registry with historical resumes from archive.

    Scans data/resume_archive/raw/ for .tex files and registers each as
    resume_type="historical" with status determined by file existence.

    Examples:\n

        $ manage_registry.py init --dry-run  # Dry run to preview

        $ manage_registry.py init            # Initialize registry
    """

    # Get all .tex files from archive
    tex_files = sorted(RAW_ARCHIVE_PATH.glob("*.tex"))

    if not tex_files:
        typer.secho(f"No .tex files found in {RAW_ARCHIVE_PATH}", fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(code=1)

    typer.secho(f"\nFound {len(tex_files)} resume(s) in archive", fg=typer.colors.BLUE, bold=True)

    if dry_run:
        typer.echo("Running in DRY RUN mode (no changes will be made)\n")

    registered_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0

    # Collect updates for batch processing (efficiency)
    to_register = []  # (resume_name, status)
    to_update = {}  # resume_name -> new_status

    for tex_file in tex_files:
        resume_name = tex_file.stem
        status = _infer_archive_status(resume_name)

        # Check if already registered
        if resume_is_registered(resume_name):
            typer.echo(f"⊘ {resume_name} (already registered)")
            skipped_count += 1
            continue
        else:
            # New registration
            to_register.append((resume_name, status))
            if dry_run:
                typer.echo(f"• {resume_name} → {status}")
                registered_count += 1

    # Perform batch operations (if not dry run)
    if not dry_run:
        # Register new resumes
        for resume_name, status in to_register:
            try:
                register_resume(
                    resume_name=resume_name, resume_type="historical", source="cli", status=status
                )
                typer.secho(f"✓ {resume_name} → {status}", fg=typer.colors.GREEN)
                registered_count += 1

            except Exception as e:
                typer.secho(f"✗ {resume_name}: {e}", fg=typer.colors.RED)
                error_count += 1

        # Batch update existing resumes (single file write!)
        if to_update:
            results = update_resume_status(updates=to_update, source="cli")

            for resume_name, success in results.items():
                if success:
                    typer.secho(
                        f"⟳ {resume_name} → {to_update[resume_name]}", fg=typer.colors.YELLOW
                    )
                    updated_count += 1
                else:
                    typer.secho(f"✗ {resume_name}: not found in registry", fg=typer.colors.RED)
                    error_count += 1

    # Summary
    typer.echo("\n" + "=" * 80)
    typer.echo("Summary:")
    typer.echo(f"  Registered: {registered_count}")
    if updated_count > 0:
        typer.echo(f"  Updated:    {updated_count}")
    typer.echo(f"  Skipped:    {skipped_count}")
    if error_count > 0:
        typer.secho(f"  Errors:     {error_count}", fg=typer.colors.RED)

    if not dry_run:
        # Show registry stats
        counts = count_resumes()
        typer.echo(f"\nTotal resumes in registry: {counts['total']}")
        typer.echo(f"  By status: {dict(counts['by_status'])}")
        typer.echo(f"  By type:   {dict(counts['by_type'])}")

    if dry_run:
        typer.echo("\nDry run complete. Run without --dry-run to make changes.")


@app.command("register")
def register_command(
    resume_name: str = typer.Argument(
        ..., help="Resume name (e.g., _test_Simple or Res202511_MLEng_Company)"
    ),
    resume_type: str = typer.Argument(..., help="Resume type: 'test' or 'experimental' only"),
    status: str = typer.Argument(..., help="Initial status (see allowed statuses by type below)"),
):
    """
    Manually register a new test or experimental resume.

    This command is restricted to test and experimental resume types only. Historical resumes should be registered via 'init', and generated resumes are registered automatically by the pipeline.

    You will be prompted for an optional reason that will be logged with the registration event.

    Status validation uses EXPERIMENTAL_STATUSES or TEST_STATUSES from archer.utils.resume_registry. If an invalid status is provided, the command will show the complete list of allowed statuses for that type.

    Examples:\n

        $ manage_registry.py register _test_Simple test raw                         # Register test resume

        $ manage_registry.py register Res202511_MLEng_Disney experimental drafting  # Register experimental resume

        $ manage_registry.py register _test_EdgeCase test parsing_failed            # Register test with failure status
    """
    # Validate resume type
    allowed_types = {"test", "experimental"}
    if resume_type not in allowed_types:
        typer.secho(
            f"Error: resume_type must be 'test' or 'experimental', got '{resume_type}'",
            fg=typer.colors.RED,
            err=True,
        )
        typer.echo(f"\nAllowed types for manual registration: {', '.join(sorted(allowed_types))}")
        typer.echo("Note: Use 'init' command for historical resumes")
        raise typer.Exit(code=1)

    # Get allowed statuses for this resume type
    allowed_statuses = EXPERIMENTAL_STATUSES if resume_type == "experimental" else TEST_STATUSES

    # Validate status
    if status not in allowed_statuses:
        typer.secho(
            f"Error: Invalid status '{status}' for resume_type '{resume_type}'",
            fg=typer.colors.RED,
            err=True,
        )
        typer.echo(f"\nAllowed statuses for {resume_type} resumes:")
        typer.echo(" | ".join(sorted(allowed_statuses)))
        # for s in sorted(allowed_statuses):
        #     typer.echo(f"  - {s}")
        typer.echo("")
        raise typer.Exit(code=1)

    # Check if already registered
    if resume_is_registered(resume_name):
        typer.secho(
            f"Error: Resume '{resume_name}' is already registered", fg=typer.colors.RED, err=True
        )
        entry = get_resume_status(resume_name)
        typer.echo(f"  Current type:   {entry['resume_type']}")
        typer.echo(f"  Current status: {entry['status']}")
        typer.echo("\nUse 'update' command to change status")
        raise typer.Exit(code=1)

    # Prompt for optional reason
    try:
        reason = prompt_for_reason("Reason for registration")
    except KeyboardInterrupt:
        raise typer.Exit(code=1)

    # Register the resume
    try:
        register_resume(
            resume_name=resume_name,
            resume_type=resume_type,
            source="cli",
            status=status,
            reason=reason,
        )

        typer.secho(
            f"✓ Registered {resume_name} as {resume_type} with status '{status}'",
            fg=typer.colors.GREEN,
        )

        if reason:
            typer.echo(f"  Reason: {reason}")

    except Exception as e:
        typer.secho(f"✗ Failed to register: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@app.command("list")
def list_command(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    resume_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter by type (historical, generated, experimental, or test)"
    ),
):
    """
    List resumes in the registry.

    Examples:\n

        $ manage_registry.py list                    # List all resumes

        $ manage_registry.py list --status parsed    # List only parsed resumes

        $ manage_registry.py list --type historical  # List only historical resumes
    """
    if status:
        resumes = list_resumes_by_status(status)
        typer.secho(f"\nResumes with status '{status}':", fg=typer.colors.BLUE, bold=True)
    elif resume_type:
        resumes = list_resumes_by_type(resume_type)
        typer.secho(f"\nResumes of type '{resume_type}':", fg=typer.colors.BLUE, bold=True)
    else:
        resumes = get_all_resumes()
        typer.secho("\nAll resumes:", fg=typer.colors.BLUE, bold=True)

    if not resumes:
        typer.echo("  (none)")
        return

    # Find longest name for alignment
    max_name_len = max(len(r["resume_name"]) for r in resumes)

    for resume in resumes:
        padding = " " * (max_name_len - len(resume["resume_name"]))
        typer.echo(
            f"  {resume['resume_name']}{padding}  {resume['resume_type']:10}  {resume['status']}"
        )

    typer.echo(f"\nTotal: {len(resumes)}")


@app.command("stats")
def stats_command():
    """
    Show registry statistics.

    Examples:\n

        $ manage_registry.py stats
    """
    counts = count_resumes()

    typer.secho("\nRegistry Statistics", fg=typer.colors.BLUE, bold=True)
    typer.echo("=" * 80)
    typer.echo(f"Total resumes: {counts['total']}")

    typer.echo("\nBy Status:")
    for status, count in sorted(counts["by_status"].items()):
        typer.echo(f"  {status:20} {count}")

    typer.echo("\nBy Type:")
    for resume_type, count in sorted(counts["by_type"].items()):
        typer.echo(f"  {resume_type:20} {count}")


@app.command("status")
def status_command(resume_name: str = typer.Argument(..., help="Resume name (e.g., Res202510)")):
    """
    Get status of a specific resume.

    Examples:\n

        $ manage_registry.py status Res202510
    """
    entry = get_resume_status(resume_name)

    if entry is None:
        typer.secho(f"Resume '{resume_name}' not found in registry", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.secho(f"\n{resume_name}", fg=typer.colors.BLUE, bold=True)
    typer.echo(f"  Type:   {entry['resume_type']}")
    typer.echo(f"  Status: {entry['status']}")


@app.command("update")
def update_command(
    resume_name: str = typer.Argument(..., help="Resume name to update"),
    new_status: str = typer.Argument(
        ..., help="New status value (see docs/RESUME_STATUS_REFERENCE.md)"
    ),
    reason: Optional[str] = typer.Option(None, "--reason", "-r", help="Reason for manual update"),
):
    """
    Manually update resume status.

    Prompts for an optional reason if not provided via --reason flag.
    Logs the update as a status change event with source="cli".

    Examples:\n

        $ manage_registry.py update Res202510 completed                       # Mark as completed (prompts for reason)

        $ manage_registry.py update Res202511 failed --reason "LaTeX errors" # Mark as failed with reason
    """
    if not resume_is_registered(resume_name):
        typer.secho(f"Resume '{resume_name}' not found in registry", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # Get current status
    entry = get_resume_status(resume_name)
    old_status = entry["status"]

    if old_status == new_status:
        typer.secho(f"Resume is already in status '{new_status}'", fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(code=0)

    # Prompt for reason if not provided via --reason flag
    if not reason:
        try:
            reason = prompt_for_reason("Reason for status update")
        except KeyboardInterrupt:
            raise typer.Exit(code=1)

    # Update status
    try:
        extra_fields = {}
        if reason:
            extra_fields["reason"] = reason

        update_resume_status(updates={resume_name: new_status}, source="manual", **extra_fields)

        typer.secho(f"✓ Updated {resume_name}: {old_status} → {new_status}", fg=typer.colors.GREEN)

        if reason:
            typer.echo(f"  Reason: {reason}")

    except Exception as e:
        typer.secho(f"✗ Failed to update: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@app.command("locate")
def locate_command(
    resume_name: str = typer.Argument(
        ..., help="Resume identifier (e.g. _test_Res202511_Fry_MomCorp)"
    ),
    file_type: str = typer.Option(
        "tex", "--type", "-t", help="File type: tex, pdf, yaml, or raw (default: tex)"
    ),
):
    """
    Get file path for a resume by identifier.

    Uses the registry to determine resume_type and constructs the expected file path.
    Shows whether the file exists at the expected location.

    Examples:\n

        $ manage_registry.py locate Res202510             # Locate .tex file

        $ manage_registry.py locate Res202510 --type pdf  # Locate .pdf file

        $ manage_registry.py locate Res202510 -t yaml     # Locate .yaml file
    """
    try:
        file_path = get_resume_file(resume_name, file_type)
        typer.echo(file_path)

    except FileNotFoundError as e:
        # Extract expected path from error message
        expected_path = str(e).split("expected path:\n")[-1]
        typer.echo(expected_path)
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)


if __name__ == "__main__":
    app()
