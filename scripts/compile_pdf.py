#!/usr/bin/env python3
"""
PDF Compilation CLI

Compiles LaTeX resume files to PDF using the rendering context.

Commands:
    compile - Compile a single LaTeX file to PDF
    batch   - Compile multiple resumes (not yet implemented)

Examples:\n

    compile_pdf.py compile data/resume_archive/Res202506.tex  # Compile single resume

    compile_pdf.py compile Res202506.tex --verbose            # Verbose output
"""

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from typing_extensions import Annotated

from archer.contexts.rendering import compile_resume

load_dotenv()
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT"))
RESUME_ARCHIVE_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH"))

app = typer.Typer(
    help="Compile LaTeX resumes to PDF with registry tracking",
    add_completion=False,
    invoke_without_command=True,
)


@app.callback()
def main(ctx: typer.Context):
    """Show help by default when no command is provided."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command()
def compile(
    tex_file: Annotated[
        Path,
        typer.Argument(
            help="LaTeX resume file to compile (.tex extension)",
            exists=True,
            dir_okay=False,
            resolve_path=True,
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
            help="Number of pdflatex passes (default: 2 for cross-references)",
            min=1,
            max=5,
        ),
    ] = 2,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show detailed compilation output (pdflatex stdout/stderr)",
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
):
    """
    Compile a LaTeX resume to PDF.

    Requires the resume to be registered in the registry. Uses the rendering
    context's compile_resume() function with full tracking and logging.

    Examples:\n

        $ compile_pdf.py compile path/to/resume.tex            # Compile single resume

        $ compile_pdf.py compile path/to/resume.tex --verbose  # Verbose output

        $ compile_pdf.py compile path/to/resume.tex --passes 3 # Three compilation passes
    """
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
        typer.secho("✗ Compilation failed", fg=typer.colors.RED, bold=True)
        typer.echo(f"  Errors: {len(result.errors)}")

        if result.errors:
            typer.echo("\nErrors:")
            for error in result.errors[:10]:  # Limit to first 10
                typer.secho(f"  - {error}", fg=typer.colors.RED)
            if len(result.errors) > 10:
                typer.echo(f"  ... and {len(result.errors) - 10} more")

    # Exit with appropriate code
    sys.exit(0 if result.success else 1)


@app.command()
def batch(
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
