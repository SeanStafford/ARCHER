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
import sys
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from typing_extensions import Annotated

from archer.contexts.rendering import compile_resume
from archer.contexts.rendering.validator import validate_resume
from archer.utils import get_resume_file

load_dotenv()
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT"))

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
    tex_source: Annotated[
        str,
        typer.Argument(
            help="LaTeX resume file path OR resume identifier",
        ),
    ],
    output_dir: Annotated[
        Optional[Path],
        typer.Option(
            "--output-dir",
            "-o",
            help="Custom output directory (default: timestamped log directory)",
            dir_okay=True,
            file_okay=False,
        ),
    ] = None,
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

        $ compile_pdf.py compile Res202511                     # Compile using identifier

        $ compile_pdf.py compile path/to/resume.tex            # Compile using path

        $ compile_pdf.py compile Res202511 --verbose           # Verbose output

        $ compile_pdf.py compile path/to/resume.tex --passes 3 # Three compilation passes
    """

    # Infer path from identifier if needed
    if "/" not in tex_source and "." not in tex_source:
        # interpret as resume identifier
        tex_file = get_resume_file(tex_source)
    else:
        # interpret as file path
        tex_file = Path(tex_source)

    # Validate file extension
    if tex_file.suffix != ".tex":
        typer.secho(
            f"Error: File must have .tex extension: {tex_file}", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(code=1)

    # Display compilation info
    typer.secho(f"\nCompiling: {tex_file.name}", fg=typer.colors.BLUE, bold=True)
    typer.echo(f"Passes: {num_passes}")
    if output_dir:
        typer.echo(f"Output directory: {output_dir}")
    typer.echo("")

    # Compile the resume
    try:
        result = compile_resume(
            tex_file=tex_file,
            output_dir=output_dir,
            num_passes=num_passes,
            verbose=verbose,
            keep_artifacts_on_success=keep_artifacts,
            overwrite_allowed=not no_overwrite,
        )
    except Exception as e:
        typer.secho("\nCompilation failed with exception:", fg=typer.colors.RED, bold=True)
        typer.secho(f"  {str(e)}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # Display results
    if result.success:
        typer.secho("✓ Compilation succeeded", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"  PDF: {result.pdf_path}")
        typer.echo(f"  Warnings: {len(result.warnings)}")

        if verbose and result.warnings:
            typer.echo("\nWarnings:")
            for warning in result.warnings[:10]:  # Limit to first 10
                typer.echo(f"  - {warning}")
            if len(result.warnings) > 10:
                typer.echo(f"  ... and {len(result.warnings) - 10} more")
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

    # Exit with appropriate code
    sys.exit(0 if result.success else 1)


@app.command("validate")
def validate_command(
    pdf_source: Annotated[
        str,
        typer.Argument(
            help="Compiled resume PDF path OR resume identifier",
        ),
    ],
    expected_pages: Annotated[
        int,
        typer.Option(
            "--expected-pages",
            "-e",
            help="Expected number of pages (default: 2 for ARCHER resumes)",
            min=1,
            max=10,
        ),
    ] = 2,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show detailed validation output (all issues)",
        ),
    ] = False,
):
    """
    Validate a compiled resume PDF.

    Checks PDF quality including page count and other layout constraints.
    Requires the resume to be registered in the registry.

    Examples:\n

        $ compile_pdf.py validate Res202511                     # Validate using identifier

        $ compile_pdf.py validate path/to/resume.pdf            # Validate using path

        $ compile_pdf.py validate Res202511 --verbose           # Show all issues

        $ compile_pdf.py validate path/to/resume.pdf -e 1       # Expect 1 page
    """
    # Infer path from identifier if needed
    if "/" not in pdf_source and "." not in pdf_source:
        # interpret as resume identifier
        pdf_file = get_resume_file(pdf_source, "pdf")
        resume_name = pdf_source
    else:
        # interpret as file path
        pdf_file = Path(pdf_source)
        resume_name = pdf_file.stem

    # Validate file extension
    if pdf_file.suffix != ".pdf":
        typer.secho(
            f"Error: File must have .pdf extension: {pdf_file}", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(code=1)

    # Display validation info
    typer.secho(f"\nValidating: {pdf_file.name}", fg=typer.colors.BLUE, bold=True)
    typer.echo(f"Resume name: {resume_name}")
    typer.echo(f"Expected pages: {expected_pages}")
    typer.echo("")

    # Validate the resume
    result = validate_resume(
        resume_name=resume_name,
        pdf_path=pdf_file,
        expected_pages=expected_pages,
        verbose=verbose,
    )

    # Display results
    if result.is_valid:
        typer.secho("✓ Validation passed", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"  Page count: {result.page_count}")
    else:
        typer.secho("✗ Validation failed", fg=typer.colors.YELLOW, bold=True)
        typer.echo(f"  Page count: {result.page_count}")
        typer.echo(f"  Issues: {len(result.issues)}")

        if result.issues:
            typer.echo("\nValidation issues:")
            display_issues = result.issues if verbose else result.issues[:10]
            for issue in display_issues:
                typer.secho(f"  - {issue}", fg=typer.colors.YELLOW)
            if not verbose and len(result.issues) > 10:
                typer.echo(f"  ... and {len(result.issues) - 10} more (use --verbose to see all)")

    # Exit with appropriate code
    sys.exit(0 if result.is_valid else 1)


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
