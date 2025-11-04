#!/usr/bin/env python3
"""
LaTeX Resume Processing CLI

Command-line interface for processing LaTeX resume files with cleaning and
optional normalization. Cleaning removes comments and suggestion blocks.
Normalization standardizes formatting to match generated output conventions.

When --normalize is specified, all cleaning options are automatically enabled
(removes all comments and suggest blocks) regardless of other flags.

Usage:
    # Clean a single file
    python process_resume.py input.tex output.tex --comment-types all
    python process_resume.py input.tex --comment-types descriptive,commented_code

    # Clean and normalize (auto-enables full cleaning)
    python process_resume.py input.tex --normalize

    # Clean entire directory in-place
    python process_resume.py --directory Archive/Resumes_cleaned/ --comment-types all

    # Dry run (preview changes)
    python process_resume.py input.tex --dry-run --comment-types all
"""

import typer
from pathlib import Path
from typing import Optional, List
from typing_extensions import Annotated

from archer.contexts.templating.process_latex_archive import process_file, process_directory
from archer.utils.clean_latex import CommentType


app = typer.Typer(
    help="Process LaTeX resume files with cleaning and optional normalization",
    add_completion=False,
)


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
    for t in comment_types_str.split(','):
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
def main(
    input_file: Annotated[
        Optional[Path],
        typer.Argument(
            help="Input .tex file (omit for directory mode)",
            exists=True,
            dir_okay=False,
            resolve_path=True,
        )
    ] = None,
    output_file: Annotated[
        Optional[Path],
        typer.Argument(
            help="Output .tex file (defaults to overwriting input)",
            dir_okay=False,
            resolve_path=True,
        )
    ] = None,
    directory: Annotated[
        Optional[Path],
        typer.Option(
            "--directory",
            "-d",
            help="Process all .tex files in this directory (in-place)",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        )
    ] = None,
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
        )
    ] = "none",
    remove_suggest_blocks: Annotated[
        bool,
        typer.Option(
            "--remove-suggest-blocks",
            "-s",
            help="Remove \\suggest{...} blocks from the LaTeX files"
        )
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-n",
            help="Preview changes without writing files"
        )
    ] = False,
    normalize: Annotated[
        bool,
        typer.Option(
            "--normalize",
            help="Apply formatting normalization (blank lines, Education header, etc.)"
        )
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show detailed output"
        )
    ] = False,
):
    """
    Process LaTeX resume files with cleaning and optional normalization.

    Note: When --normalize is used, all cleaning options are automatically enabled
    (removes all comments and suggest blocks). Any provided cleaning flags will be
    ignored with a warning.

    Examples:

        # Clean a single file, removing all comment types
        python process_resume.py input.tex --comment-types all

        # Normalize (automatically enables full cleaning)
        python process_resume.py input.tex --normalize

        # Clean with specific comment types
        python process_resume.py input.tex output.tex -c descriptive,commented_code

        # Clean all files in a directory with normalization
        python process_resume.py -d Archive/Resumes_cleaned/ --normalize

        # Preview changes without modifying files
        python process_resume.py input.tex --dry-run -c all
    """
    # Validate arguments
    if directory and input_file:
        typer.echo("Error: Cannot specify both --directory and input_file", err=True)
        raise typer.Exit(code=1)

    if not directory and not input_file:
        typer.echo("Error: Must specify either input_file or --directory", err=True)
        raise typer.Exit(code=1)

    comment_types_set = parse_comment_types(comment_types)
    try:
        validate_comment_types(comment_types_set)
    except typer.BadParameter as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    # Normalize flag overrides cleaning options
    if normalize:
        # Check if user provided cleaning options
        user_provided_cleaning_options = (
            comment_types != "none" or remove_suggest_blocks
        )

        if user_provided_cleaning_options:
            typer.echo(
                "\nWarning: --normalize flag automatically enables full cleaning "
                "(all comments + suggest blocks). Provided cleaning options will be ignored.",
                err=True
            )
            typer.echo()

        # Override with full cleaning
        comment_types_set = {CommentType.ALL}
        remove_suggest_blocks = True

    if verbose or dry_run:
        typer.echo("Configuration:")
        typer.echo(f"  Comment types: {', '.join(sorted(comment_types_set)) if comment_types_set else 'none'}")
        typer.echo(f"  Remove suggest blocks: {remove_suggest_blocks}")
        typer.echo(f"  Normalize formatting: {normalize}")
        typer.echo(f"  Dry run: {dry_run}")
        typer.echo()

    # Process files and collect results
    results = []

    if directory:
        if verbose:
            typer.echo(f"Processing directory: {directory}")
            typer.echo()

        results = process_directory(
            directory,
            comment_types_set,
            remove_suggest_blocks,
            normalize,
            dry_run
        )

    else:
        if output_file is None:
            output_file = input_file
            if verbose:
                typer.echo(f"Output file not specified, will overwrite: {input_file}")

        if verbose:
            typer.echo(f"Processing file: {input_file}")
            if output_file != input_file:
                typer.echo(f"Output file: {output_file}")
            typer.echo()

        success, message = process_file(
            input_file,
            output_file,
            comment_types_set,
            remove_suggest_blocks,
            normalize,
            dry_run
        )
        results = [(success, message)]

    # Print results and summary
    success_count = 0
    error_count = 0

    for success, message in results:
        if success:
            success_count += 1
            typer.echo(f"✓ {message}")
        else:
            error_count += 1
            typer.echo(f"✗ {message}", err=True)

    if len(results) > 1:
        typer.echo()
        typer.echo(f"Summary: {success_count} succeeded, {error_count} failed")

    if error_count > 0:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
