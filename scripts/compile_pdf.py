#!/usr/bin/env python3
"""
PDF Compilation and Validation CLI

Compiles LaTeX resume files to PDF and validates compiled PDFs using the rendering context.

Commands:
    compile  - Compile a single LaTeX file to PDF
    validate - Validate a compiled PDF resume
    batch    - Compile multiple resumes (not yet implemented)

Examples:\n

    compile_pdf.py compile Res202511                          # Compile using identifier

    compile_pdf.py compile data/resume_archive/Res202506.tex  # Compile using path

    compile_pdf.py compile Res202511 --verbose                # Verbose output

    compile_pdf.py validate Res202511                         # Validate using identifier

    compile_pdf.py validate path/to/resume.pdf                # Validate using path
"""

import os
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from typing_extensions import Annotated

from archer.contexts.rendering import compile_resume
from archer.contexts.rendering.validator import validate_resume

load_dotenv()
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT"))
LATEX_COMPILER = Path(os.getenv("LATEX_COMPILER"))


def display_path(path: Path) -> str:
    """Return path relative to PROJECT_ROOT for cleaner display."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


app = typer.Typer(
    help="Compile LaTeX resumes to PDF and validate compiled PDFs with registry tracking",
    add_completion=False,
    invoke_without_command=True,
)


@app.callback()
def main(ctx: typer.Context):
    """Show help by default when no command is provided."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command("compile")
def compile_command(
    resume_identifier: Annotated[
        str,
        typer.Argument(
            help="Resume identifier (must be registered)",
        ),
    ],
    num_passes: Annotated[
        int,
        typer.Option(
            "--passes",
            "-p",
            help="Number of compiler passes (default: 2 for cross-references)",
            min=1,
            max=5,
        ),
    ] = 2,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show detailed compilation output (compiler stdout/stderr)",
        ),
    ] = False,
    keep_artifacts: Annotated[
        bool,
        typer.Option(
            "--keep-artifacts",
            "-k",
            help="Keep LaTeX artifacts (.aux, .log, etc.) on successful compilation",
        ),
    ] = False,
    no_overwrite: Annotated[
        bool,
        typer.Option(
            "--no-overwrite",
            help="Prevent overwriting existing compiled PDFs",
        ),
    ] = False,
):
    """
    Compile a LaTeX resume to PDF.

    Requires the resume to be registered in the registry. Uses the rendering
    context's compile_resume() function with full tracking and logging.

    Examples:\n

        $ compile_pdf.py compile Res202511                     # Compile resume

        $ compile_pdf.py compile Res202511 --verbose           # Verbose output

        $ compile_pdf.py compile Res202511 --passes 3          # Three compilation passes
    """
    # Display compilation info
    typer.secho(f"\nCompiling: {resume_identifier}", fg=typer.colors.BLUE, bold=True)
    typer.echo(f"Passes: {num_passes}")
    typer.echo("")

    # Compile the resume
    try:
        result = compile_resume(
            resume_name=resume_identifier,
            num_passes=num_passes,
            verbose=verbose,
            keep_artifacts_on_success=keep_artifacts,
            overwrite_allowed=not no_overwrite,
        )
    except ValueError as e:
        typer.secho(f"Error: {e}\n", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.echo("")
    # Display results
    if result.success:
        typer.secho("✓ Compilation succeeded", fg=typer.colors.GREEN, bold=True)

        typer.echo(f"  {LATEX_COMPILER} warnings: {len(result.warnings)}")
        if verbose and result.warnings:
            typer.echo(f"\n{LATEX_COMPILER} warnings:")
            for warning in result.warnings[:10]:  # Limit to first 10
                typer.echo(f"  - {warning}")
            if len(result.warnings) > 10:
                typer.echo(f"  ... and {len(result.warnings) - 10} more")

        typer.echo(f"  PDF: {display_path(result.pdf_path)}")
    else:
        typer.secho(
            f"✗ Compilation failed with {len(result.errors)} errors", fg=typer.colors.RED, bold=True
        )

        if result.errors:
            typer.echo("\nErrors:")
            for error in result.errors[:10]:  # Limit to first 10
                if "Compiled PDF already exists: " in error:
                    error += " Retry without --no-overwrite to replace the existing PDF."
                typer.secho(f"  - {error}", fg=typer.colors.RED)
            if len(result.errors) > 10:
                typer.echo(f"  ... and {len(result.errors) - 10} more")

    if result.compile_dir:
        typer.echo(f"  Log: {display_path(result.compile_dir / 'render.log')}")
    typer.echo("")

    # Exit with appropriate code
    raise typer.Exit(code=0 if result.success else 1)


@app.command("validate")
def validate_command(
    resume_identifier: Annotated[
        str,
        typer.Argument(
            help="Resume identifier (must be registered)",
        ),
    ],
):
    """
    Validate a compiled resume against its structured YAML.

    Compares the PDF layout against expected structure from YAML to detect
    overflow, displaced sections, and page count issues. Generates actionable
    feedback for the targeting context when validation fails.

    Examples:\n

        $ compile_pdf.py validate Res202511                     # Validate resume

        $ compile_pdf.py validate _test_Res202511_Fry_MomCorp   # Validate test resume

    """
    # Display validation info
    typer.secho(f"\nValidating: {resume_identifier}", fg=typer.colors.BLUE, bold=True)
    typer.echo("")

    # Validate the resume
    try:
        result = validate_resume(resume_name=resume_identifier)
    except ValueError as e:
        typer.secho(f"Error: {e}\n", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # Display results
    if result.is_valid:
        typer.secho("\n✓ Validation passed", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"  Page count: {result.page_count}")
    else:
        typer.secho("\n✗ Validation failed", fg=typer.colors.RED, bold=True)
        typer.echo(f"  Page count: {result.page_count}")
        typer.echo(f"  Diagnostic issues: {len(result.issues)}")

    if result.log_dir:
        typer.echo(f"  Log: {display_path(result.log_dir / 'render.log')}")
    typer.echo("")

    raise typer.Exit(code=0 if result.is_valid else 1)


@app.command("batch")
def batch_command(
    pattern: Annotated[
        Optional[str],
        typer.Argument(help="Glob pattern for selecting resumes (e.g., 'Res2025*.tex')"),
    ] = None,
    resume_type: Annotated[
        Optional[str],
        typer.Option(
            "--type",
            "-t",
            help="Resume type to compile (e.g., 'test', 'historical')",
        ),
    ] = None,
):
    """
    Compile multiple resumes in batch mode.

    NOT YET IMPLEMENTED - This is a stub for future batch compilation support.

    Planned features:
    - Parallel compilation with multiprocessing
    - Progress reporting
    - Summary statistics (X/Y succeeded, total time)
    - Filter by resume type or glob pattern

    Examples (when implemented):\n

        $ compile_pdf.py batch --type test         # Compile all test resumes

        $ compile_pdf.py batch "Res2025*.tex"      # Compile by pattern

        $ compile_pdf.py batch --type historical   # Compile all historical resumes
    """
    typer.secho("\nBatch compilation not yet implemented.", fg=typer.colors.YELLOW, bold=True)
    typer.echo("This feature is planned for future development.")
    typer.echo("\nPlanned features:")
    typer.echo("  - Parallel compilation")
    typer.echo("  - Progress reporting")
    typer.echo("  - Summary statistics")
    typer.echo("  - Filter by type or pattern")
    typer.echo("\nFor now, use the 'compile' command for single resumes.")
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
