#!/usr/bin/env python3
"""
Format raw job markdown into canonical format with interactive metadata prompts.

Usage:
    python scripts/format_job.py /tmp/archer/raw_job.md
    python scripts/format_job.py /tmp/archer/raw_job.md -o data/jobs/MLEng_Disney_12345.md
    python scripts/format_job.py /tmp/archer/raw_job.md --llm-optional
    python scripts/format_job.py /tmp/archer/raw_job.md --skip-llm
"""

import os
import sys
import termios
import time
from pathlib import Path

import typer
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

JOBS_PATH = Path(os.getenv("JOBS_PATH", "data/jobs"))

# Timing constants
SMALL_DELAY = 0.15  # seconds after each field
DONE_DELAY = 0.5  # seconds after "Done" before clearing

# Track lines for ANSI cleanup
_lines_printed = 0

# =============================================================================
# TERMINAL HELPERS
# =============================================================================


def flush_input():
    """Discard any pending keyboard input."""
    try:
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except termios.error:
        pass  # Not a terminal


def print_tracked(text: str = ""):
    """Print and track line count for later cleanup."""
    global _lines_printed
    print(text)
    _lines_printed += text.count("\n") + 1


def clear_previous_lines(count: int):
    """Move up and clear the specified number of lines."""
    for _ in range(count):
        print("\033[A\033[K", end="")


def print_header(title: str):
    """Print a section header with underline."""
    print_tracked(f"\n {title}")
    print_tracked(" " + "─" * len(title))


def prompt_for_field(field: str, default: str = "") -> str:
    """
    Prompt user for a metadata field value with line overwrite.

    - Shows [default] if provided
    - Enter accepts default
    - Typing overrides default
    - Ctrl+C aborts cleanly
    """
    global _lines_printed
    prompt = f"> {field}" + (f" [{default}]" if default else "") + ": "
    try:
        flush_input()
        value = input(prompt).strip()
        final_value = value if value else default

        # Overwrite prompt line with confirmed value
        display = f"{field}: {final_value}" if final_value else f"{field}: (skipped)"
        time.sleep(SMALL_DELAY)
        print(f"\033[A\r{display}\033[K")
        _lines_printed += 1

        return final_value
    except KeyboardInterrupt:
        print("\n\n✗ Operation aborted by user\n")
        raise typer.Exit(code=1)


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================


def print_extraction_results(extracted: dict[str, str], required: list[str], optional: list[str]):
    """Print what was found during heuristic extraction."""
    for field in required + optional:
        if field in extracted:
            typer.echo(f'  ✓ Found {field}: "{extracted[field]}"')
        else:
            typer.echo(f"  ✗ No {field} found")


def print_final_summary(metadata: dict[str, str], all_fields: list[str]):
    """Print the final metadata summary with aligned fields."""
    max_len = max(len(f) for f in all_fields)

    print("\n Metadata")
    print(" " + "─" * 8)
    for field in all_fields:
        value = metadata.get(field, "")
        padding = " " * (max_len - len(field))
        display = value if value else "(empty)"
        print(f"{padding}{field}:  {display}")
    print()


# =============================================================================
# MARKDOWN GENERATION
# =============================================================================


def build_canonical_markdown(metadata: dict[str, str], body_text: str) -> str:
    """
    Build canonical job markdown with metadata header.

    Format:
        ## Metadata

        ### Company
        <value>

        ### Role
        <value>

        ...

        ## <body content>
    """
    from archer.contexts.intake.extraction_patterns import ALL_FIELDS

    lines = ["## Metadata", ""]

    for field in ALL_FIELDS:
        value = metadata.get(field)
        if value:
            lines.append(f"### {field}")
            lines.append(value)
            lines.append("")

    # Add body content (strip any existing metadata section)
    body = _strip_existing_metadata(body_text)
    if body.strip():
        lines.append(body.strip())
        lines.append("")

    return "\n".join(lines)


def _strip_existing_metadata(text: str) -> str:
    """Remove existing ## Metadata section from text."""
    lines = text.split("\n")
    result = []
    in_metadata = False

    for line in lines:
        if line.strip().lower() == "## metadata":
            in_metadata = True
            continue
        if in_metadata and line.startswith("## "):
            in_metadata = False
        if not in_metadata:
            result.append(line)

    return "\n".join(result)


# =============================================================================
# CLI APPLICATION
# =============================================================================

app = typer.Typer(help="Format raw job markdown with interactive metadata prompts.")


@app.command()
def main(
    input_file: Path = typer.Argument(..., help="Raw markdown file to format"),
    output: Path | None = typer.Option(
        None, "-o", "--output", help="Output file path (default: data/jobs/<stem>.md)"
    ),
    llm_optional: bool = typer.Option(
        False, "--llm-optional", help="Offer LLM extraction for missing optional fields"
    ),
    llm_model: str = typer.Option(
        "gpt-4o-mini", "--llm-model", help="LLM model for extraction fallback"
    ),
    llm_provider: str = typer.Option(
        "openai", "--llm-provider", help="LLM provider (openai or anthropic)"
    ),
    skip_llm: bool = typer.Option(False, "--skip-llm", help="Never prompt for LLM extraction"),
):
    """Format raw markdown into canonical job format with metadata."""
    global _lines_printed

    if not input_file.exists():
        typer.echo(f"Error: File not found: {input_file}", err=True)
        raise typer.Exit(1)

    text = input_file.read_text()

    # Import here to avoid circular imports
    from archer.contexts.intake.extraction_patterns import (
        ALL_FIELDS,
        LLM_VIABLE_FIELDS,
        OPTIONAL_FIELDS,
        OPTIONAL_FIELDS_LLM_VIABLE,
        REQUIRED_FIELDS,
    )
    from archer.contexts.intake.metadata_extractor import extract_metadata_heuristic

    # Phase 1: Heuristic extraction
    typer.echo("\n=== Job Metadata Extraction ===")
    typer.echo("Attempting to extract metadata from raw markdown...\n")

    extracted = extract_metadata_heuristic(text, filename=input_file.name)
    print_extraction_results(extracted, REQUIRED_FIELDS, OPTIONAL_FIELDS)

    typer.echo("\nEnter accepts [default], type to override, Ctrl+C aborts.")

    # Phase 2: Interactive prompting
    _lines_printed = 0

    print_header("Required Fields")
    metadata = {}
    for field in REQUIRED_FIELDS:
        value = prompt_for_field(field, extracted.get(field, ""))
        if value:
            metadata[field] = value

    print_header("Optional Fields")
    for field in OPTIONAL_FIELDS:
        value = prompt_for_field(field, extracted.get(field, ""))
        if value:
            metadata[field] = value

    # Phase 3: LLM fallback (if needed) - only for validated viable fields
    missing_required = [f for f in REQUIRED_FIELDS if f not in metadata]
    missing_optional_viable = (
        [f for f in OPTIONAL_FIELDS_LLM_VIABLE if f not in metadata] if llm_optional else []
    )
    fields_for_llm = [
        f for f in (missing_required + missing_optional_viable) if f in LLM_VIABLE_FIELDS
    ]

    if fields_for_llm and not skip_llm:
        print()  # Blank line before LLM prompt
        _lines_printed += 1

        field_type = "required" if missing_required else "optional"
        typer.echo(f"Missing {field_type} fields: {', '.join(fields_for_llm)}")
        _lines_printed += 1

        if typer.confirm("Use LLM to attempt extraction?", default=False):
            _lines_printed += 1  # The confirm line

            typer.echo("\nQuerying LLM...")
            _lines_printed += 2

            from archer.contexts.intake.metadata_llm import extract_metadata_with_llm

            llm_results = extract_metadata_with_llm(
                fields_for_llm, text, model=llm_model, provider=llm_provider
            )

            for field, value in llm_results.items():
                if value:
                    typer.echo(f'  ✓ LLM extracted {field}: "{value}"')
                else:
                    typer.echo(f"  ✗ LLM could not extract {field}")
                _lines_printed += 1

            if any(llm_results.values()):
                if typer.confirm("\nAccept LLM suggestions?", default=True):
                    for field, value in llm_results.items():
                        if value:
                            metadata[field] = value
                _lines_printed += 2  # blank + confirm line
        else:
            _lines_printed += 1  # The "No" response line

    # Show done, pause, clear, show final summary
    print("\n✓ Done")
    _lines_printed += 2
    time.sleep(DONE_DELAY)
    clear_previous_lines(_lines_printed)

    print_final_summary(metadata, ALL_FIELDS)

    # Phase 4: Write output
    output_path = output or (JOBS_PATH / f"{input_file.stem}.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_text = build_canonical_markdown(metadata, text)
    output_path.write_text(output_text)

    typer.secho(f"✓ Saved: {output_path}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
