#!/usr/bin/env python3
"""
LaTeX Normalization CLI

Normalizes LaTeX resume files by cleaning comments and standardizing formatting.

Commands:
    normalize - Process a single LaTeX file
    batch     - Process multiple files (directory or pipeline mode)

Examples:
    # Single file
    normalize_latex.py normalize input.tex output.tex
    normalize_latex.py normalize --in-place input.tex
    normalize_latex.py normalize --dry-run input.tex output.tex

    # Batch processing
    normalize_latex.py batch  # Pipeline mode (raw/ → archive/)
    normalize_latex.py batch --in-place /path/to/resumes/
    normalize_latex.py batch /input/dir/ /output/dir/
"""

import os
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from typing_extensions import Annotated

from archer.contexts.templating.normalizer import process_file
from archer.utils.clean_latex import CommentType

load_dotenv()
RAW_ARCHIVE_PATH = Path(os.getenv("RAW_ARCHIVE_PATH"))
RESUME_ARCHIVE_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH"))

app = typer.Typer(
    help="Normalize LaTeX resume files (cleaning and formatting)",
    add_completion=False,
    invoke_without_command=True,
)


@app.callback()
def main(ctx: typer.Context):
    """Show help by default when no command is provided."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def parse_comment_types(comment_types_str: str) -> set:
    """
    Parse comma-separated comment types string into a set.

    Args:
        comment_types_str: Comma-separated string like "descriptive,commented_code,all"

    Returns:
        Set of comment type strings
    """
    if not comment_types_str:
        return set()

    types = set()
    for t in comment_types_str.split(","):
        t = t.strip().lower()
        if t:
            types.add(t)

    return types


def validate_comment_types(comment_types: set) -> None:
    """
    Validate that all comment types are recognized.

    Args:
        comment_types: Set of comment type strings

    Raises:
        typer.BadParameter: If any comment type is not recognized
    """
    valid_types = CommentType.get_all_types() | {CommentType.ALL, CommentType.NONE}

    invalid_types = comment_types - valid_types
    if invalid_types:
        raise typer.BadParameter(
            f"Invalid comment types: {', '.join(invalid_types)}. "
            f"Valid types are: {', '.join(sorted(valid_types))}"
        )


@app.command()
def normalize(
    input_file: Annotated[
        Path,
        typer.Argument(
            help="Input .tex file",
            exists=True,
            dir_okay=False,
            resolve_path=True,
        ),
    ],
    output_file: Annotated[
        Optional[Path],
        typer.Argument(
            help="Output .tex file (required unless --in-place)",
            dir_okay=False,
            resolve_path=True,
        ),
    ] = None,
    in_place: Annotated[
        bool, typer.Option("--in-place", "-i", help="Modify input file in-place")
    ] = False,
    comment_types: Annotated[
        str,
        typer.Option(
            "--comment-types",
            "-c",
            help=(
                "Comma-separated list of comment types to remove. "
                "Options: decorative, section_headers, descriptive, commented_code, "
                "inline_annotations, inline_dates, all, none"
            ),
        ),
    ] = "none",
    remove_suggest_blocks: Annotated[
        bool,
        typer.Option(
            "--remove-suggest-blocks",
            "-s",
            help="Remove \\suggest{...} blocks from the LaTeX files",
        ),
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-d", help="Preview changes without writing files")
    ] = False,
    skip_normalization: Annotated[
        bool,
        typer.Option(
            "--no-normalize",
            help="Skip formatting normalization (only clean comments/suggest blocks)",
        ),
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed output")] = False,
):
    """
    Normalize a single LaTeX resume file.

    By default, applies full normalization (cleaning + formatting). Use --no-normalize
    to skip formatting normalization and only apply specified cleaning options.

    Examples:\n

        normalize_latex.py normalize input.tex output.tex                   # Full normalization

        normalize_latex.py normalize --in-place input.tex                   # In-place normalization

        normalize_latex.py normalize --no-normalize input.tex output.tex    # Only clean, no normalization

        normalize_latex.py normalize --dry-run input.tex output.tex         # Preview changes
    """
    # Validate arguments
    if not (in_place or dry_run) and output_file is None:
        typer.echo("Error: Must specify output_file or use --in-place", err=True)
        raise typer.Exit(code=1)

    if not in_place and output_file == input_file:
        typer.echo(
            "Error: Input and output files are the same. Use --in-place to confirm in-place modification.",
            err=True,
        )
        raise typer.Exit(code=1)

    if in_place:
        output_file = input_file

    # Parse and validate comment types
    comment_types_set = parse_comment_types(comment_types)
    try:
        validate_comment_types(comment_types_set)
    except typer.BadParameter as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    # Determine if we should normalize (default: yes, unless --no-normalize)
    apply_normalization = not skip_normalization

    # When normalizing, automatically enable full cleaning
    if apply_normalization:
        # Check if user provided cleaning options
        user_provided_cleaning_options = comment_types != "none" or remove_suggest_blocks

        if user_provided_cleaning_options:
            typer.echo(
                "\nWarning: Normalization automatically enables full cleaning "
                "(all comments + suggest blocks). Provided cleaning options will be ignored.",
                err=True,
            )
            typer.echo()

        # Override with full cleaning
        comment_types_set = {CommentType.ALL}
        remove_suggest_blocks = True

    if verbose or dry_run:
        typer.echo("Configuration:")
        typer.echo(
            f"  Comment types: {', '.join(sorted(comment_types_set)) if comment_types_set else 'none'}"
        )
        typer.echo(f"  Remove suggest blocks: {remove_suggest_blocks}")
        typer.echo(f"  Normalize formatting: {apply_normalization}")
        typer.echo(f"  Dry run: {dry_run}")
        typer.echo()

    if verbose:
        typer.echo(f"Processing file: {input_file}")
        if output_file != input_file:
            typer.echo(f"Output file: {output_file}")
        typer.echo()

    # Process file
    success, message = process_file(
        input_file,
        output_file,
        comment_types_set,
        remove_suggest_blocks,
        apply_normalization,
        dry_run,
    )

    if success:
        typer.echo(f"✓ {message}\n")
    else:
        typer.echo(f"✗ {message}\n", err=True)
        raise typer.Exit(code=1)


@app.command()
def batch(
    input_dir: Annotated[
        Optional[Path],
        typer.Argument(
            help="Input directory (omit for pipeline mode: raw/ → archive/)",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = None,
    output_dir: Annotated[
        Optional[Path],
        typer.Argument(
            help="Output directory (required unless --in-place or pipeline mode)",
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = None,
    in_place: Annotated[
        bool, typer.Option("--in-place", "-i", help="Modify files in input directory in-place")
    ] = False,
    comment_types: Annotated[
        str,
        typer.Option(
            "--comment-types",
            "-c",
            help=(
                "Comma-separated list of comment types to remove. "
                "Options: decorative, section_headers, descriptive, commented_code, "
                "inline_annotations, inline_dates, all, none"
            ),
        ),
    ] = "all",
    remove_suggest_blocks: Annotated[
        bool,
        typer.Option(
            "--remove-suggest-blocks",
            "-s",
            help="Remove \\suggest{...} blocks from the LaTeX files",
        ),
    ] = True,
    skip_normalization: Annotated[
        bool,
        typer.Option(
            "--no-normalize",
            help="Skip formatting normalization (only clean comments/suggest blocks)",
        ),
    ] = False,
    suffix: Annotated[
        Optional[str],
        typer.Option(
            "--suffix",
            help="Suffix to append to output filenames (e.g., 'Res123.tex' → 'Res123_suffix.tex')",
        ),
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed output")] = False,
):
    """
    Batch normalize LaTeX resume files.

    Pipeline mode (no arguments): Processes raw/ → archive/ with full normalization.
    Directory mode: Process all .tex files in specified directory/directories.

    Examples:

        normalize_latex.py batch                                  # Pipeline mode (raw/ → archive/)

        normalize_latex.py batch --in-place my_dir/               # In-place batch normalization (overwrites originals)

        normalize_latex.py batch --in-place --suffix test my_dir/ # Create normalized copies in same directory (originals unchanged)

        normalize_latex.py batch in_dir/ out_dir/                 # Custom input/output directories

        normalize_latex.py batch --suffix test in_dir/ out_dir/   # Add suffix to output files (Res123.tex → Res123_test.tex)

    """
    # Determine mode and validate arguments
    pipeline_mode = input_dir is None and output_dir is None

    if pipeline_mode:
        # Pipeline mode: use hardcoded archive paths
        input_dir = RAW_ARCHIVE_PATH
        output_dir = RESUME_ARCHIVE_PATH
        typer.echo(f"Pipeline mode: {input_dir} → {output_dir}")
    elif input_dir and not output_dir and not in_place:
        typer.echo(
            "Error: Must specify output_dir or use --in-place when providing input_dir", err=True
        )
        raise typer.Exit(code=1)
    elif in_place:
        output_dir = input_dir

    # Parse and validate comment types
    comment_types_set = parse_comment_types(comment_types)
    try:
        validate_comment_types(comment_types_set)
    except typer.BadParameter as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    # Determine if we should normalize (default: yes, unless --no-normalize)
    apply_normalization = not skip_normalization

    # When normalizing, automatically enable full cleaning
    if apply_normalization:
        comment_types_set = {CommentType.ALL}
        remove_suggest_blocks = True

    # Get all .tex files
    tex_files = sorted(input_dir.glob("*.tex"))

    if not tex_files:
        typer.echo(f"No .tex files found in {input_dir}", err=True)
        raise typer.Exit(code=1)

    # Print configuration summary
    typer.echo(f"\nProcessing {len(tex_files)} resume files...")
    typer.echo(f"Source: {input_dir}")
    typer.echo(f"Destination: {output_dir}")
    if suffix:
        typer.echo(f"Output suffix: _{suffix}")
    if verbose:
        typer.echo(
            f"Comment types: {', '.join(sorted(comment_types_set)) if comment_types_set else 'none'}"
        )
        typer.echo(f"Remove suggest blocks: {remove_suggest_blocks}")
        typer.echo(f"Normalize formatting: {apply_normalization}")
    typer.echo()

    # Process all files
    success_count = 0
    error_count = 0

    for tex_file in tex_files:
        # Construct output filename with optional suffix
        if suffix:
            # Insert suffix before extension: Res123.tex → Res123_suffix.tex
            stem = tex_file.stem
            output_filename = f"{stem}_{suffix}.tex"
        else:
            output_filename = tex_file.name

        output_file = output_dir / output_filename

        success, message = process_file(
            tex_file,
            output_file,
            comment_types_set,
            remove_suggest_blocks=remove_suggest_blocks,
            normalize=apply_normalization,
            dry_run=False,  # No dry-run for batch
            preamble_comment_types=comment_types_set,
        )

        if success:
            success_count += 1
            if verbose:
                typer.echo(f"✓ {message}")
        else:
            error_count += 1
            typer.echo(f"✗ {message}", err=True)

    # Print summary
    if verbose:
        typer.echo()
        typer.echo("=" * 60)
        typer.echo(f"Summary: {success_count} succeeded, {error_count} failed")
        typer.echo("=" * 60)
    else:
        typer.echo(f"Summary: {success_count} succeeded, {error_count} failed")

    if error_count > 0:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
