#!/usr/bin/env python3
"""
Command-line interface for testing LaTeX ↔ YAML roundtrip conversion.

Validates conversions through dual roundtrip testing:
- LaTeX roundtrip: LaTeX → YAML → LaTeX (tests parser + generator)
- YAML roundtrip: Compare parsed YAML vs re-parsed YAML (tests stability)

Usage:
    python scripts/test_roundtrip.py test <resume.tex>
    python scripts/test_roundtrip.py batch [--pattern "Res2025*.tex"]
"""

import os
import shutil
from pathlib import Path

import typer
from dotenv import load_dotenv

from archer.contexts.templating import validate_roundtrip_conversion
from archer.utils.timestamp import now

load_dotenv()
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT"))
LOGS_PATH = Path(os.getenv("LOGS_PATH"))
RESUME_ARCHIVE_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH"))

# Default validation thresholds
DEFAULT_MAX_LATEX_DIFFS = 6
DEFAULT_MAX_YAML_DIFFS = 0

app = typer.Typer(
    help="Test LaTeX ↔ YAML roundtrip conversion with validation",
    invoke_without_command=True,
)


@app.callback()
def main(ctx: typer.Context):
    """Show help by default when no command is provided."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command("test")
def test_command(
    tex_file: Path = typer.Argument(
        ...,
        help="Path to .tex file to test",
        exists=True,
        file_okay=True,
        dir_okay=False,
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
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed progress",
    ),
    keep_all: bool = typer.Option(
        False,
        "--keep-all",
        "-k",
        help="Keep all intermediate files even on perfect roundtrip (for inspection)",
    ),
):
    """
    Test roundtrip conversion on a single resume.

    Saves intermediate files to outs/logs/test_TIMESTAMP/ for inspection.
    On success, cleans up intermediate files and keeps only the log.

    Examples:\n

        $ test_roundtrip.py test path/to/resume.tex            # Test with default thresholds (LaTeX: 6, YAML: 0)

        $ test_roundtrip.py test path/to/resume.tex -l 0 -y 0  # Strict validation (0 diffs for both)

        $ test_roundtrip.py test path/to/resume.tex -v         # Verbose output
    """
    # Validate file extension
    if tex_file.suffix != ".tex":
        typer.secho(
            f"Error: File must have .tex extension: {tex_file}", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(code=1)

    # Create log directory (files go directly here, not in subdirectory)
    timestamp = now()
    work_dir = LOGS_PATH / f"test_{timestamp}"
    work_dir.mkdir(exist_ok=True, parents=True)

    typer.secho(f"\nTesting: {tex_file.name}", fg=typer.colors.BLUE, bold=True)
    typer.echo(f"Validation thresholds: LaTeX ≤{max_latex_diffs}, YAML ≤{max_yaml_diffs}")
    typer.echo(f"Log directory: {work_dir}\n")

    # Open log file
    log_file = work_dir / "test.log"
    with open(log_file, "w", encoding="utf-8") as log:
        log.write(f"Roundtrip Test - {timestamp}\n")
        log.write("=" * 80 + "\n")
        log.write(f"File: {tex_file.name}\n")
        log.write(f"Max LaTeX diffs: {max_latex_diffs}\n")
        log.write(f"Max YAML diffs: {max_yaml_diffs}\n")
        log.write("=" * 80 + "\n\n")

        try:
            result = validate_roundtrip_conversion(
                tex_file, work_dir, max_latex_diffs, max_yaml_diffs
            )

            # Log results
            if result["error"]:
                log.write(f"ERROR: {result['error']}\n")
                typer.secho(f"✗ Error: {result['error']}", fg=typer.colors.RED)
                typer.echo(f"Artifacts saved to: {work_dir}")
                raise typer.Exit(code=1)

            latex_status = "✓" if result["latex_roundtrip"]["success"] else "✗"
            yaml_status = "✓" if result["yaml_roundtrip"]["success"] else "✗"
            latex_diffs = result["latex_roundtrip"]["num_diffs"]
            yaml_diffs = result["yaml_roundtrip"]["num_diffs"]

            log.write(
                f"LaTeX roundtrip: {'PASS' if result['latex_roundtrip']['success'] else 'FAIL'} ({latex_diffs} diffs)\n"
            )
            log.write(
                f"YAML roundtrip:  {'PASS' if result['yaml_roundtrip']['success'] else 'FAIL'} ({yaml_diffs} diffs)\n"
            )
            log.write(f"Time: {result['time_ms']:.0f}ms\n")

            typer.echo(f"LaTeX roundtrip: {latex_status} ({latex_diffs} diffs)")
            typer.echo(f"YAML roundtrip:  {yaml_status} ({yaml_diffs} diffs)")
            typer.echo(f"Time: {result['time_ms']:.0f}ms")

            if result["validation_passed"]:
                log.write("\nValidation: PASSED\n")

                typer.secho("\n✓ Success!", fg=typer.colors.GREEN)

                # Clean up intermediate files but keep log (unless --keep-all)
                if not keep_all:
                    for item in work_dir.iterdir():
                        if item.name != "test.log":
                            if item.is_file():
                                item.unlink()
                            elif item.is_dir():
                                shutil.rmtree(item)
                    typer.echo(f"Log saved to: {log_file}")
                else:
                    typer.echo(f"All artifacts kept in: {work_dir}")
                    typer.echo(f"Log saved to: {log_file}")

            else:
                log.write("\nValidation: FAILED\n")
                log.write(f"Artifacts kept in: {work_dir}\n")

                typer.secho(
                    f"\n✗ Validation failed. Artifacts saved to: {work_dir}", fg=typer.colors.RED
                )
                typer.echo(f"Log saved to: {log_file}")
                raise typer.Exit(code=1)

        except KeyboardInterrupt:
            log.write("\n\nInterrupted by user\n")
            typer.secho("\n\nInterrupted by user", fg=typer.colors.YELLOW, err=True)
            raise typer.Exit(code=130)


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
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed progress",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress non-error output",
    ),
    keep_all: bool = typer.Option(
        False,
        "--keep-all",
        "-k",
        help="Keep all intermediate files even on perfect roundtrip (for inspection)",
    ),
):
    """
    Test roundtrip conversion on all matching resumes.

    Saves artifacts for failed conversions in outs/logs/test_TIMESTAMP/ResumeName/.
    Generates summary.txt and test.log in the log directory.

    Examples:\n

        $ test_roundtrip.py batch                           # Test all resumes

        $ test_roundtrip.py batch --pattern "Res2025*.tex"  # Test specific pattern

        $ test_roundtrip.py batch -l 0 -y 0                 # Strict validation

        $ test_roundtrip.py batch -q                        # Quiet mode
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
    log_dir = LOGS_PATH / f"test_{timestamp}"
    log_dir.mkdir(exist_ok=True, parents=True)

    if not quiet:
        typer.secho(f"\nTesting {len(tex_files)} resumes", fg=typer.colors.BLUE, bold=True)
        typer.echo(f"Validation thresholds: LaTeX ≤{max_latex_diffs}, YAML ≤{max_yaml_diffs}")
        typer.echo(f"Log directory: {log_dir}")
        typer.echo("=" * 80)

    # Open log file
    log_file = log_dir / "test.log"
    with open(log_file, "w", encoding="utf-8") as log:
        log.write(f"Roundtrip Test - {timestamp}\n")
        log.write("=" * 80 + "\n")
        log.write(f"Pattern: {pattern}\n")
        log.write(f"Files: {len(tex_files)}\n")
        log.write(f"Max LaTeX diffs: {max_latex_diffs}\n")
        log.write(f"Max YAML diffs: {max_yaml_diffs}\n")
        log.write("=" * 80 + "\n\n")

        results = []

        try:
            for i, tex_file in enumerate(tex_files, 1):
                if not quiet:
                    print(f"[{i}/{len(tex_files)}] {tex_file.name}...", end=" ", flush=True)

                log.write(f"[{i}/{len(tex_files)}] {tex_file.name}\n")

                # Each file gets its own subdirectory
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
                        # Check if perfect roundtrip (0 diffs in both)
                        perfect_roundtrip = (
                            result["latex_roundtrip"]["num_diffs"] == 0
                            and result["yaml_roundtrip"]["num_diffs"] == 0
                        )

                        if not quiet:
                            typer.secho(f"✓ ({result['time_ms']:.0f}ms)", fg=typer.colors.GREEN)

                        log.write("  Validation: PASSED\n")

                        # Clean up work directory only on perfect roundtrip (unless --keep-all)
                        if perfect_roundtrip and not keep_all:
                            shutil.rmtree(work_dir)
                            log.write("  Perfect roundtrip - artifacts cleaned\n\n")
                        elif keep_all:
                            log.write("  Artifacts kept (--keep-all flag)\n\n")
                        else:
                            log.write("  Artifacts kept (has diffs within threshold)\n\n")
                    else:
                        if not quiet:
                            typer.secho(
                                f"✗ LaTeX:{result['latex_roundtrip']['num_diffs']} "
                                f"YAML:{result['yaml_roundtrip']['num_diffs']}",
                                fg=typer.colors.RED,
                            )
                        log.write("  Validation: FAILED - artifacts kept\n\n")

        except KeyboardInterrupt:
            typer.secho("\n\nInterrupted by user", fg=typer.colors.YELLOW, err=True)
            log.write("\n\nInterrupted by user\n")
            raise typer.Exit(code=130)

    # Generate summary
    passed = sum(1 for r in results if r["validation_passed"])
    failed = sum(1 for r in results if not r["validation_passed"])
    errors = sum(1 for r in results if r["error"])
    perfect = sum(
        1
        for r in results
        if r["validation_passed"]
        and r["latex_roundtrip"]["num_diffs"] == 0
        and r["yaml_roundtrip"]["num_diffs"] == 0
    )
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
        typer.echo(f"  Perfect (0 diffs):     {perfect}/{total} ({100 * perfect / total:.1f}%)")
        typer.echo(f"  Failed:                {failed}/{total}")
        typer.echo(f"  Total LaTeX diffs:     {total_latex_diffs:,}")
        typer.echo(f"  Total YAML diffs:      {total_yaml_diffs:,}")
        typer.echo(f"  Errors:                {errors}")

    # Save summary.txt
    summary_file = log_dir / "summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(f"Roundtrip Test Summary - {timestamp}\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total files:           {total}\n")
        f.write(f"Passed:                {passed}/{total} ({100 * passed / total:.1f}%)\n")
        f.write(f"Perfect (0 diffs):     {perfect}/{total} ({100 * perfect / total:.1f}%)\n")
        f.write(f"Failed:                {failed}/{total}\n")
        f.write(f"Total LaTeX diffs:     {total_latex_diffs:,}\n")
        f.write(f"Total YAML diffs:      {total_yaml_diffs:,}\n")
        f.write(f"Errors:                {errors}\n\n")

        # Find longest filename for alignment
        max_filename_len = max(len(r["file"]) for r in results)

        for r in results:
            # Calculate padding with dots
            padding = "." * (max_filename_len - len(r["file"]))

            if r["error"]:
                f.write(f"{r['file']}{padding}: ERROR - {r['error']}\n")
            else:
                # Always show diff counts, even when passing
                latex_str = (
                    f"PASS ({r['latex_roundtrip']['num_diffs']})"
                    if r["latex_roundtrip"]["success"]
                    else f"FAIL ({r['latex_roundtrip']['num_diffs']})"
                )
                yaml_str = (
                    f"PASS ({r['yaml_roundtrip']['num_diffs']})"
                    if r["yaml_roundtrip"]["success"]
                    else f"FAIL ({r['yaml_roundtrip']['num_diffs']})"
                )
                status = "PASS" if r["validation_passed"] else "FAIL"
                f.write(f"{r['file']}{padding}: {status} - LaTeX={latex_str} YAML={yaml_str}\n")

    if not quiet:
        typer.echo(f"\nLogs saved to: {log_dir}")
        typer.echo(f"Summary: {summary_file}")
        typer.echo(f"Detailed log: {log_file}")

    # Exit with appropriate code
    if failed > 0 or errors > 0:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
