#!/usr/bin/env python3
"""
LaTeX Normalization CLI

Normalizes historical LaTeX resume files with registry tracking and logging.

Commands:
    normalize - Normalize a single resume by identifier
    batch     - Normalize all historical resumes with status 'raw' (or all historical with --renormalize)

Examples:
    # Single resume
    python scripts/normalize_latex.py normalize _test_Res202511_Fry_MomCorp

    # Single resume, allow re-normalizing
    python scripts/normalize_latex.py normalize _test_Res202511_Fry_MomCorp --renormalize

    # Batch: all historical resumes with status 'raw'
    python scripts/normalize_latex.py batch

    # Batch: re-normalize all historical resumes
    python scripts/normalize_latex.py batch --renormalize
"""

import os
from pathlib import Path

import typer
from dotenv import load_dotenv
from typing_extensions import Annotated

from archer.contexts.templating import normalize_resume
from archer.utils.resume_registry import list_resumes_by_type

load_dotenv()
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT"))

app = typer.Typer(
    help="Normalize LaTeX resume files with registry tracking",
    add_completion=False,
    invoke_without_command=True,
)


@app.callback()
def main(ctx: typer.Context):
    """Show help by default when no command is provided."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def display_path(path: Path) -> str:
    """Return path relative to PROJECT_ROOT for cleaner display."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


@app.command("normalize")
def normalize_command(
    resume_identifier: Annotated[
        str,
        typer.Argument(help="Resume identifier (must be registered)"),
    ],
    renormalize: Annotated[
        bool,
        typer.Option(
            "--renormalize",
            "-r",
            help="Allow re-normalizing already normalized resumes",
        ),
    ] = False,
):
    """
    Normalize a single resume by identifier.

    The resume must be registered and have appropriate type/status:
    - Historical: must have status 'raw' (unless --renormalize)
    - Test: any status allowed
    - Experimental/generated: not allowed

    Examples:\n

        $ normalize_latex.py normalize Res202511

        $ normalize_latex.py normalize Res202511 --renormalize
    """

    typer.secho(f"\nNormalizing: {resume_identifier}\n", fg=typer.colors.BLUE, bold=True)

    # Call orchestration function (ValueError raised for pre-validation errors)
    try:
        result = normalize_resume(resume_identifier, allow_overwrite=renormalize)
    except ValueError as e:
        typer.secho(f"Error: {e}\n", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    if result.success:
        typer.secho("✓ Normalization succeeded", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"  Time: {result.time_s:.2f}s")
        typer.echo(f"  Output: {display_path(result.output_path)}")
    else:
        typer.secho("✗ Normalization failed", fg=typer.colors.RED, bold=True)
        typer.echo(f"  Time: {result.time_s:.2f}s")
        if result.error:
            typer.echo(f"  Error: {result.error}")

    # Always show log location
    if result.log_dir:
        typer.echo(f"  Log: {display_path(result.log_dir / 'template.log')}")
    typer.echo("")

    # Exit with appropriate code
    raise typer.Exit(code=0 if result.success else 1)


@app.command("batch")
def batch_command(
    renormalize: Annotated[
        bool,
        typer.Option(
            "--renormalize",
            "-r",
            help="Re-normalize all historical resumes (not just those with status 'raw')",
        ),
    ] = False,
):
    """
    Batch normalize resumes from registry.

    By default, normalizes all historical resumes with status 'raw'.
    With --renormalize, normalizes all historical resumes regardless of status.

    Examples:\n

        $ normalize_latex.py batch                # All 'raw' status historical resumes

        $ normalize_latex.py batch --renormalize  # All historical resumes
    """

    # Get resumes to process (historical only)
    historical_resume_statuses = list_resumes_by_type("historical")

    if renormalize:
        filtered_resumes = [r["resume_name"] for r in historical_resume_statuses]
        mode_desc = "historical resumes"
    else:
        # Filter for historical resumes with status 'raw'
        filtered_resumes = [
            r["resume_name"] for r in historical_resume_statuses if r["status"] == "raw"
        ]
        mode_desc = "historical resumes with status 'raw'"

    # Early exit if no resumes to process
    if not filtered_resumes:
        typer.secho(f"\nNo {mode_desc} found in registry.\n", fg=typer.colors.YELLOW)
        raise typer.Exit(code=0)

    typer.secho(
        f"\nBatch normalizing {len(filtered_resumes)} {mode_desc}...\n", fg=typer.colors.BLUE
    )

    success_count = 0
    error_count = 0
    for resume_name in filtered_resumes:
        try:
            result = normalize_resume(resume_name, allow_overwrite=renormalize)
            if result.success:
                success_count += 1
                typer.secho(f"✓ {resume_name}", fg=typer.colors.GREEN)
                typer.echo(f"  Output: {display_path(result.output_path)}")
            else:
                error_count += 1
                typer.secho(f"✗ {resume_name}: {result.error}", fg=typer.colors.RED, err=True)
        except ValueError as e:
            # Pre-validation error (not registered, wrong type/status)
            # Must separate failure case, because no result object exists in this case
            error_count += 1
            typer.secho(f"✗ {resume_name}: {e}", fg=typer.colors.RED, err=True)

    typer.echo("")
    if error_count == 0:
        typer.secho(
            f"Summary: {success_count} succeeded, {error_count} failed",
            fg=typer.colors.GREEN,
        )
    else:
        typer.secho(
            f"Summary: {success_count} succeeded, {error_count} failed",
            fg=typer.colors.YELLOW,
        )
    typer.echo("")

    # Exit with appropriate code
    raise typer.Exit(code=1 if error_count > 0 else 0)


if __name__ == "__main__":
    app()
