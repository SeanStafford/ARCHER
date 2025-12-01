#!/usr/bin/env python3
"""
Command-line interface for LaTeX <-> YAML resume conversion.

Subcommands:
- parse: Convert LaTeX to YAML with roundtrip validation (for historical/test resumes)
- generate: Convert YAML to LaTeX (for experimental/test resumes)
- clean: Normalize YAML structure for LaTeX generation
- list: List available resumes in the archive
- batch: Batch convert with validation
"""

import os
from pathlib import Path

import typer
from dotenv import load_dotenv
from omegaconf import OmegaConf

from archer.contexts.templating import (
    clean_yaml,
    generate_resume,
    parse_resume,
    validate_roundtrip_conversion,
)
from archer.utils.timestamp import now

load_dotenv()
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT"))
RESUME_ARCHIVE_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH"))
LOGS_PATH = Path(os.getenv("LOGS_PATH"))


def display_path(path: Path) -> str:
    """Return path relative to PROJECT_ROOT for cleaner display."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


# Validation thresholds
DEFAULT_MAX_LATEX_DIFFS = 6
DEFAULT_MAX_YAML_DIFFS = 0

app = typer.Typer(
    add_completion=False,
    help="Convert LaTeX resumes to structured YAML format with validation",
    invoke_without_command=True,
)


@app.callback()
def main(ctx: typer.Context):
    """Show help by default when no command is provided."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command("list")
def list_command():
    """
    List all available resumes in the archive.

    Shows which resumes have been converted to YAML (in structured/)
    and which are pending conversion.

    Example:\n

        $ convert_template.py list
    """
    # Get all .tex files from archive
    tex_files = sorted(RESUME_ARCHIVE_PATH.glob("*.tex"))

    if not tex_files:
        typer.secho(
            f"No resume files found in {RESUME_ARCHIVE_PATH}", fg=typer.colors.YELLOW, err=True
        )
        raise typer.Exit(code=1)

    # Check structured directory for existing YAMLs
    structured_dir = RESUME_ARCHIVE_PATH / "structured"
    structured_dir.mkdir(exist_ok=True, parents=True)
    existing_yamls = {f.stem for f in structured_dir.glob("*.yaml")}

    typer.secho(f"\nResumes in archive ({len(tex_files)}):", fg=typer.colors.BLUE, bold=True)

    converted_count = 0
    for tex_file in tex_files:
        if tex_file.stem in existing_yamls:
            typer.secho(f"  ✓ {tex_file.name}", fg=typer.colors.GREEN)
            converted_count += 1
        else:
            typer.echo(f"  • {tex_file.name}")

    typer.echo(f"\nConverted: {converted_count}/{len(tex_files)}")
    typer.echo(f"Pending: {len(tex_files) - converted_count}/{len(tex_files)}")


@app.command("clean")
def clean_command(
    yaml_file: Path = typer.Argument(
        ...,
        help="Path to .yaml file to clean",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path (if not specified, modifies in-place)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be done without modifying files",
    ),
):
    """
    Normalize YAML resume data for LaTeX generation.

    Applies normalization rules to ensure YAML structure is compatible with
    the LaTeX generator. Currently fills missing LaTeX-formatted fields from
    plaintext equivalents.

    Examples:\n

        $ convert_template.py clean test.yaml                        # Clean in-place

        $ convert_template.py clean test.yaml -o test_cleaned.yaml   # Save to new file

        $ convert_template.py clean test.yaml --dry-run              # Preview changes
    """
    # Validate file extension
    if yaml_file.suffix != ".yaml":
        typer.secho(
            f"Error: File must have .yaml extension: {yaml_file}", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(code=1)

    # Determine output path
    output_path = output if output else yaml_file

    typer.secho(f"\nCleaning: {yaml_file.name}", fg=typer.colors.BLUE, bold=True)
    if output:
        typer.echo(f"Output: {output_path}")
    else:
        typer.echo("Mode: In-place modification")

    if dry_run:
        typer.echo("DRY RUN (no files will be modified)\n")

    try:
        # Load YAML
        yaml_data = OmegaConf.load(yaml_file)
        yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

        # Clean YAML and count changes
        cleaned_dict, changes = clean_yaml(yaml_dict, return_count=True)

        typer.echo(f"Fields normalized: {changes}")

        if not dry_run:
            # Save cleaned YAML
            conf = OmegaConf.create(cleaned_dict)
            OmegaConf.save(conf, output_path)

            # Strip trailing blank lines for consistency
            content = output_path.read_text()
            output_path.write_text(content.rstrip() + "\n")

            typer.secho(f"\n✓ Success! Cleaned YAML saved to: {output_path}", fg=typer.colors.GREEN)
        else:
            typer.echo("\nDry run complete. Run without --dry-run to apply changes.")

    except Exception as e:
        typer.secho(f"\n✗ Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


def print_roundtrip_validation_results(result, max_latex_diffs, max_yaml_diffs):
    """Helper to print roundtrip validation results."""

    latex_status = (
        "?" if result.latex_diffs is None else "✓" if result.latex_diffs <= max_latex_diffs else "✗"
    )
    latex_info = (
        "diff info unavailable" if result.latex_diffs is None else f"{result.latex_diffs} diffs"
    )
    yaml_status = (
        "?" if result.yaml_diffs is None else "✓" if result.yaml_diffs <= max_yaml_diffs else "✗"
    )
    yaml_info = (
        "diff info unavailable" if result.yaml_diffs is None else f"{result.yaml_diffs} diffs"
    )

    typer.echo(f"  LaTeX roundtrip: {latex_status} ({latex_info})")
    typer.echo(f"  YAML  roundtrip: {yaml_status} ({yaml_info})")


@app.command("generate")
def generate_command(
    resume_identifier: str = typer.Argument(
        ...,
        help="Resume identifier (must be registered)",
    ),
    max_latex_diffs: int = typer.Option(
        DEFAULT_MAX_LATEX_DIFFS,
        "--max-latex-diffs",
        "-l",
        help="Maximum LaTeX differences allowed for validation",
        min=0,
    ),
    max_yaml_diffs: int = typer.Option(
        DEFAULT_MAX_YAML_DIFFS,
        "--max-yaml-diffs",
        "-y",
        help="Maximum YAML differences allowed for validation",
        min=0,
    ),
    no_overwrite: bool = typer.Option(
        False,
        "--no-overwrite",
        help="Prevent overwriting existing output files",
    ),
):
    """
    Generate LaTeX from a structured YAML resume with validation.

    Converts YAML to LaTeX for experimental or test resumes with registry tracking.
    Validates via YAML → LaTeX → YAML roundtrip testing.

    The resume must be registered and have the correct status:\n
    - experimental: must be 'drafting_completed'\n
    - generated: must be 'targeting_completed'\n
    - test: any status allowed\n
    - historical: not allowed (wrong direction)

    Logs are saved to outs/logs/generate_TIMESTAMP/.

    Examples:\n

        $ convert_template.py generate _test_Res202511_Fry

        $ convert_template.py generate _test_Res202511_Fry --no-overwrite
    """
    typer.secho(f"\nGenerating LaTeX: {resume_identifier}\n", fg=typer.colors.BLUE, bold=True)

    try:
        result = generate_resume(
            resume_identifier,
            max_latex_diffs=max_latex_diffs,
            max_yaml_diffs=max_yaml_diffs,
            allow_overwrite=not no_overwrite,
        )
    except ValueError as e:
        typer.secho(f"Error: {e}\n", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    if result.success:
        typer.secho("\n✓ LaTeX generation succeeded", fg=typer.colors.GREEN)
        typer.echo(f"  Time: {result.time_s:.2f}s")
        typer.echo(f"  tex file: {display_path(result.output_path)}")

    else:
        typer.secho("\n✗ LaTeX generation failed", fg=typer.colors.RED, err=True)
        # typer.secho(f"  Error: {result.error}", err=True)
        if result.log_dir:
            typer.echo(f"  Artifacts saved to: {display_path(result.log_dir)}")

    # Display validation info
    print_roundtrip_validation_results(result, max_latex_diffs, max_yaml_diffs)

    if result.log_dir:
        typer.echo(f"  Log: {display_path(result.log_dir / 'template.log')}")
    typer.echo("")

    # Exit with appropriate code
    raise typer.Exit(code=0 if result.success else 1)


@app.command("parse")
def parse_command(
    resume_identifier: str = typer.Argument(
        ...,
        help="Resume identifier (must be registered)",
    ),
    max_latex_diffs: int = typer.Option(
        DEFAULT_MAX_LATEX_DIFFS,
        "--max-latex-diffs",
        "-l",
        help="Maximum LaTeX differences allowed for validation",
        min=0,
    ),
    max_yaml_diffs: int = typer.Option(
        DEFAULT_MAX_YAML_DIFFS,
        "--max-yaml-diffs",
        "-y",
        help="Maximum YAML differences allowed for validation",
        min=0,
    ),
    no_overwrite: bool = typer.Option(
        False,
        "--no-overwrite",
        help="Prevent overwriting existing output files",
    ),
):
    """
    Parse a LaTeX resume to YAML with roundtrip validation.

    Validates the conversion via LaTeX → YAML → LaTeX roundtrip testing.
    On success, saves YAML to data/resume_archive/structured/.
    On failure, saves artifacts to outs/logs/parse_TIMESTAMP/.

    The resume must be registered and have the correct status:\n
    - historical: must be 'normalized' or 'parsing_failed'\n
    - test: any status allowed\n
    - experimental/generated: not allowed (wrong direction)

    Examples:\n

        $ convert_template.py parse Res202506_MLEng_Company

        $ convert_template.py parse _test_Res202511_Fry -l 0 -y 0  # Strict validation

        $ convert_template.py parse Res202506 --no-overwrite
    """

    typer.secho(f"\nParsing YAML from LaTeX: {resume_identifier}", fg=typer.colors.BLUE, bold=True)
    typer.echo("")

    try:
        result = parse_resume(
            resume_identifier,
            max_latex_diffs=max_latex_diffs,
            max_yaml_diffs=max_yaml_diffs,
            allow_overwrite=not no_overwrite,
        )
    except ValueError as e:
        typer.secho(f"Error: {e}\n", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    if result.success:
        typer.secho("\n✓ YAML parsing succeeded", fg=typer.colors.GREEN)
        typer.echo(f"  Time: {result.time_s:.2f}s")
        typer.echo(f"  YAML: {display_path(result.output_path)}")
    else:
        typer.secho("\n✗ YAML parsing failed", fg=typer.colors.RED, err=True)
        if result.log_dir:
            typer.echo(f"  Artifacts saved to: {display_path(result.log_dir)}")

    # Display validation info
    print_roundtrip_validation_results(result, max_latex_diffs, max_yaml_diffs)

    if result.log_dir:
        typer.echo(f"  Log: {display_path(result.log_dir / 'template.log')}")
    typer.echo("")

    # Exit with appropriate code
    raise typer.Exit(code=0 if result.success else 1)


@app.command("batch")
def batch_command(
    pattern: str = typer.Option(
        "*.tex",
        "--pattern",
        "-p",
        help="File pattern to match",
    ),
    max_latex_diffs: int = typer.Option(
        DEFAULT_MAX_LATEX_DIFFS,
        "--max-latex-diffs",
        "-l",
        help="Maximum LaTeX differences allowed for validation",
        min=0,
    ),
    max_yaml_diffs: int = typer.Option(
        DEFAULT_MAX_YAML_DIFFS,
        "--max-yaml-diffs",
        "-y",
        help="Maximum YAML differences allowed for validation",
        min=0,
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress non-error output",
    ),
):
    """
    Convert all matching resumes to YAML with validation.

    Saves validated YAMLs to data/resume_archive/structured/.
    Failed conversions keep artifacts in outs/logs/convert_TIMESTAMP/.
    Generates summary.txt and convert.log in the log directory.

    Examples:\n

        $ convert_template.py batch                           # Convert all resumes

        $ convert_template.py batch --pattern "Res2025*.tex"  # Convert specific pattern

        $ convert_template.py batch -l 0 -y 0                 # Strict validation

        $ convert_template.py batch -q                        # Quiet mode
    """
    # Find matching files
    tex_files = sorted(RESUME_ARCHIVE_PATH.glob(pattern))

    if not tex_files:
        typer.secho(
            f"No files found matching {pattern} in {RESUME_ARCHIVE_PATH}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    # Create log directory
    timestamp = now()
    log_dir = LOGS_PATH / f"convert_{timestamp}"
    log_dir.mkdir(exist_ok=True, parents=True)

    if not quiet:
        typer.secho(f"\nConverting {len(tex_files)} resumes", fg=typer.colors.BLUE, bold=True)
        typer.echo(f"Validation thresholds: LaTeX ≤{max_latex_diffs}, YAML ≤{max_yaml_diffs}")
        typer.echo(f"Log directory: {log_dir}")
        typer.echo("=" * 80)

    # Open log file
    log_file = log_dir / "convert.log"
    with open(log_file, "w", encoding="utf-8") as log:
        log.write(f"Conversion Log - {timestamp}\n")
        log.write("=" * 80 + "\n")
        log.write(f"Pattern: {pattern}\n")
        log.write(f"Files: {len(tex_files)}\n")
        log.write(f"Max LaTeX diffs: {max_latex_diffs}\n")
        log.write(f"Max YAML diffs: {max_yaml_diffs}\n")
        log.write("=" * 80 + "\n\n")

        results = []
        structured_dir = RESUME_ARCHIVE_PATH / "structured"
        structured_dir.mkdir(exist_ok=True, parents=True)

        try:
            for i, tex_file in enumerate(tex_files, 1):
                if not quiet:
                    print(f"[{i}/{len(tex_files)}] {tex_file.name}...", end=" ", flush=True)

                log.write(f"[{i}/{len(tex_files)}] {tex_file.name}\n")

                work_dir = log_dir / tex_file.stem
                result = validate_roundtrip_conversion(
                    tex_file, work_dir, max_latex_diffs, max_yaml_diffs
                )
                results.append(result)

                if result["error"]:
                    if not quiet:
                        typer.secho(f"✗ ERROR: {result['error']}", fg=typer.colors.RED)
                    log.write(f"  ERROR: {result['error']}\n\n")
                else:
                    latex_status = "PASS" if result["latex_roundtrip"]["success"] else "FAIL"
                    yaml_status = "PASS" if result["yaml_roundtrip"]["success"] else "FAIL"

                    log.write(
                        f"  LaTeX: {latex_status} ({result['latex_roundtrip']['num_diffs']} diffs)\n"
                    )
                    log.write(
                        f"  YAML: {yaml_status} ({result['yaml_roundtrip']['num_diffs']} diffs)\n"
                    )
                    log.write(f"  Time: {result['time_ms']:.0f}ms\n")

                    if result["validation_passed"]:
                        # Save YAML to structured
                        output_yaml = structured_dir / f"{tex_file.stem}.yaml"
                        parsed_yaml = work_dir / f"{tex_file.stem}_parsed.yaml"
                        output_yaml.write_text(parsed_yaml.read_text())

                        if not quiet:
                            typer.secho(f"✓ ({result['time_ms']:.0f}ms)", fg=typer.colors.GREEN)

                        log.write(f"  Saved: {output_yaml}\n\n")

                        # Clean up work directory
                        import shutil

                        shutil.rmtree(work_dir)
                    else:
                        if not quiet:
                            typer.secho(
                                f"✗ LaTeX:{result['latex_roundtrip']['num_diffs']} "
                                f"YAML:{result['yaml_roundtrip']['num_diffs']}",
                                fg=typer.colors.RED,
                            )
                        log.write("  Validation failed - artifacts kept\n\n")

        except KeyboardInterrupt:
            typer.secho("\n\nInterrupted by user", fg=typer.colors.YELLOW, err=True)
            log.write("\n\nInterrupted by user\n")
            raise typer.Exit(code=130)

    # Generate summary
    passed = sum(1 for r in results if r["validation_passed"])
    failed = sum(1 for r in results if not r["validation_passed"])
    errors = sum(1 for r in results if r["error"])
    total = len(results)

    total_latex_diffs = sum(
        r["latex_roundtrip"]["num_diffs"]
        for r in results
        if r["latex_roundtrip"]["num_diffs"] is not None
    )
    total_yaml_diffs = sum(
        r["yaml_roundtrip"]["num_diffs"]
        for r in results
        if r["yaml_roundtrip"]["num_diffs"] is not None
    )

    if not quiet:
        typer.echo("=" * 80)
        typer.echo("\nSummary:")
        typer.echo(f"  Total files:           {total}")
        typer.echo(f"  Passed:                {passed}/{total} ({100 * passed / total:.1f}%)")
        typer.echo(f"  Failed:                {failed}/{total}")
        typer.echo(f"  Total LaTeX diffs:     {total_latex_diffs:,}")
        typer.echo(f"  Total YAML diffs:      {total_yaml_diffs:,}")
        typer.echo(f"  Errors:                {errors}")

    # Save summary.txt
    summary_file = log_dir / "summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(f"Conversion Summary - {timestamp}\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total files:           {total}\n")
        f.write(f"Passed:                {passed}/{total} ({100 * passed / total:.1f}%)\n")
        f.write(f"Failed:                {failed}/{total}\n")
        f.write(f"Total LaTeX diffs:     {total_latex_diffs:,}\n")
        f.write(f"Total YAML diffs:      {total_yaml_diffs:,}\n")
        f.write(f"Errors:                {errors}\n\n")

        for r in results:
            if r["error"]:
                f.write(f"{r['file']}: ERROR - {r['error']}\n")
            else:
                latex_str = (
                    "PASS"
                    if r["latex_roundtrip"]["success"]
                    else f"FAIL ({r['latex_roundtrip']['num_diffs']})"
                )
                yaml_str = (
                    "PASS"
                    if r["yaml_roundtrip"]["success"]
                    else f"FAIL ({r['yaml_roundtrip']['num_diffs']})"
                )
                status = "PASS" if r["validation_passed"] else "FAIL"
                f.write(f"{r['file']}: {status} - LaTeX={latex_str} YAML={yaml_str}\n")

    if not quiet:
        typer.echo(f"\nLogs saved to: {log_dir}")
        typer.echo(f"Summary: {summary_file}")
        typer.echo(f"Detailed log: {log_file}")

    # Exit with appropriate code
    if failed > 0 or errors > 0:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
