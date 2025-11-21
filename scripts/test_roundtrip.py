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
from datetime import datetime
from pathlib import Path
from typing import Dict

import typer
from dotenv import load_dotenv

from archer.contexts.templating import latex_to_yaml, yaml_to_latex
from archer.contexts.templating.process_latex_archive import process_file
from archer.utils.text_processing import get_meaningful_diff
from archer.utils.timestamp import now

load_dotenv()
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT"))
LOGS_PATH = Path(os.getenv("LOGS_PATH"))
RESUME_ARCHIVE_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH"))

# Default validation thresholds
DEFAULT_MAX_LATEX_DIFFS = 6
DEFAULT_MAX_YAML_DIFFS = 0

app = typer.Typer(
    add_completion=False,
    help="Test LaTeX ↔ YAML roundtrip conversion with validation",
    invoke_without_command=True,
)


@app.callback()
def main(ctx: typer.Context):
    """Show help by default when no command is provided."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def normalize_latex_file(input_path: Path, output_path: Path) -> tuple[bool, str]:
    """Normalize a LaTeX file (remove all comments, standardize format)."""
    success, message = process_file(
        input_path,
        output_path,
        comment_types=set(),
        normalize=True,
        dry_run=False
    )
    return success, message


def compare_yaml_structured(yaml1_path: Path, yaml2_path: Path) -> tuple[list[str], int]:
    """
    Compare two YAML files using structured comparison.

    Uses OmegaConf to load both YAMLs and compare as dictionaries,
    ignoring formatting and key order differences.

    Returns:
        Tuple of (diff_lines, num_differences)
    """
    from omegaconf import OmegaConf

    yaml1 = OmegaConf.load(yaml1_path)
    yaml2 = OmegaConf.load(yaml2_path)

    dict1 = OmegaConf.to_container(yaml1)
    dict2 = OmegaConf.to_container(yaml2)

    if dict1 == dict2:
        return [], 0

    diff_lines = [
        "YAML structures differ",
        f"File 1: {yaml1_path.name}",
        f"File 2: {yaml2_path.name}",
        "Run diff on the files for details"
    ]

    return diff_lines, 1


def test_single_file(
    tex_file: Path,
    work_dir: Path,
    max_latex_diffs: int,
    max_yaml_diffs: int
) -> Dict:
    """
    Test roundtrip conversion on a single LaTeX file.

    Returns:
        Dict with test results: {
            'file': filename,
            'latex_roundtrip': {'success': bool, 'num_diffs': int},
            'yaml_roundtrip': {'success': bool, 'num_diffs': int},
            'validation_passed': bool,
            'error': str or None,
            'time_ms': float
        }
    """
    start_time = datetime.now()
    result = {
        'file': tex_file.name,
        'latex_roundtrip': {'success': False, 'num_diffs': None},
        'yaml_roundtrip': {'success': False, 'num_diffs': None},
        'validation_passed': False,
        'error': None,
        'time_ms': 0.0
    }

    try:
        file_stem = tex_file.stem
        work_dir.mkdir(exist_ok=True, parents=True)

        # Step 1: Normalize input
        normalized_input = work_dir / f"{file_stem}_normalized.tex"
        if not normalize_latex_file(tex_file, normalized_input)[0]:
            result['error'] = "Failed to normalize input"
            return result

        # Step 2: Parse LaTeX → YAML
        parsed_yaml = work_dir / f"{file_stem}_parsed.yaml"
        try:
            latex_to_yaml(normalized_input, parsed_yaml)
        except Exception as e:
            result['error'] = f"Parse error: {str(e)}"
            return result

        # Step 3: Generate YAML → LaTeX
        generated_tex = work_dir / f"{file_stem}_generated.tex"
        try:
            yaml_to_latex(parsed_yaml, generated_tex)
        except Exception as e:
            result['error'] = f"Generation error: {str(e)}"
            return result

        # Step 4: Normalize generated output
        normalized_output = work_dir / f"{file_stem}_generated_normalized.tex"
        if not normalize_latex_file(generated_tex, normalized_output)[0]:
            result['error'] = "Failed to normalize output"
            return result

        # Step 5: LaTeX Roundtrip Comparison
        latex_diff_lines, latex_num_diffs = get_meaningful_diff(
            normalized_input,
            normalized_output
        )

        if latex_num_diffs > 0:
            latex_diff_file = work_dir / "latex_roundtrip.diff"
            latex_diff_file.write_text('\n'.join(latex_diff_lines), encoding='utf-8')

        result['latex_roundtrip'] = {
            'success': (latex_num_diffs <= max_latex_diffs),
            'num_diffs': latex_num_diffs
        }

        # Step 6: Re-parse generated LaTeX for YAML roundtrip
        reparsed_yaml = work_dir / f"{file_stem}_reparsed.yaml"
        try:
            latex_to_yaml(normalized_output, reparsed_yaml)
        except Exception as e:
            result['error'] = f"Re-parse error: {str(e)}"
            return result

        # Step 7: YAML Roundtrip Comparison
        yaml_diff_lines, yaml_num_diffs = compare_yaml_structured(
            parsed_yaml,
            reparsed_yaml
        )

        if yaml_num_diffs > 0:
            yaml_diff_file = work_dir / "yaml_roundtrip.diff"
            yaml_diff_file.write_text('\n'.join(yaml_diff_lines), encoding='utf-8')

        result['yaml_roundtrip'] = {
            'success': (yaml_num_diffs <= max_yaml_diffs),
            'num_diffs': yaml_num_diffs
        }

        # Determine if validation passed
        result['validation_passed'] = (
            result['latex_roundtrip']['success'] and
            result['yaml_roundtrip']['success']
        )

    except Exception as e:
        result['error'] = f"Unexpected error: {str(e)}"

    finally:
        end_time = datetime.now()
        result['time_ms'] = (end_time - start_time).total_seconds() * 1000

    return result


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

        $ python scripts/test_roundtrip.py test path/to/resume.tex           # Test with default thresholds (LaTeX: 6, YAML: 0)

        $ python scripts/test_roundtrip.py test path/to/resume.tex -l 0 -y 0 # Strict validation (0 diffs for both)

        $ python scripts/test_roundtrip.py test path/to/resume.tex -v        # Verbose output
    """
    # Validate file extension
    if tex_file.suffix != ".tex":
        typer.secho(
            f"Error: File must have .tex extension: {tex_file}",
            fg=typer.colors.RED,
            err=True
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
    with open(log_file, 'w', encoding='utf-8') as log:
        log.write(f"Roundtrip Test - {timestamp}\n")
        log.write("=" * 80 + "\n")
        log.write(f"File: {tex_file.name}\n")
        log.write(f"Max LaTeX diffs: {max_latex_diffs}\n")
        log.write(f"Max YAML diffs: {max_yaml_diffs}\n")
        log.write("=" * 80 + "\n\n")

        try:
            result = test_single_file(
                tex_file,
                work_dir,
                max_latex_diffs,
                max_yaml_diffs
            )

            # Log results
            if result['error']:
                log.write(f"ERROR: {result['error']}\n")
                typer.secho(f"✗ Error: {result['error']}", fg=typer.colors.RED)
                typer.echo(f"Artifacts saved to: {work_dir}")
                raise typer.Exit(code=1)

            latex_status = "✓" if result['latex_roundtrip']['success'] else "✗"
            yaml_status = "✓" if result['yaml_roundtrip']['success'] else "✗"
            latex_diffs = result['latex_roundtrip']['num_diffs']
            yaml_diffs = result['yaml_roundtrip']['num_diffs']

            log.write(f"LaTeX roundtrip: {'PASS' if result['latex_roundtrip']['success'] else 'FAIL'} ({latex_diffs} diffs)\n")
            log.write(f"YAML roundtrip:  {'PASS' if result['yaml_roundtrip']['success'] else 'FAIL'} ({yaml_diffs} diffs)\n")
            log.write(f"Time: {result['time_ms']:.0f}ms\n")

            typer.echo(f"LaTeX roundtrip: {latex_status} ({latex_diffs} diffs)")
            typer.echo(f"YAML roundtrip:  {yaml_status} ({yaml_diffs} diffs)")
            typer.echo(f"Time: {result['time_ms']:.0f}ms")

            if result['validation_passed']:
                log.write(f"\nValidation: PASSED\n")

                typer.secho(f"\n✓ Success!", fg=typer.colors.GREEN)

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
                log.write(f"\nValidation: FAILED\n")
                log.write(f"Artifacts kept in: {work_dir}\n")

                typer.secho(
                    f"\n✗ Validation failed. Artifacts saved to: {work_dir}",
                    fg=typer.colors.RED
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

        $ python scripts/test_roundtrip.py batch                         # Test all resumes

        $ python scripts/test_roundtrip.py batch --pattern "Res2025*.tex" # Test specific pattern

        $ python scripts/test_roundtrip.py batch -l 0 -y 0               # Strict validation

        $ python scripts/test_roundtrip.py batch -q                      # Quiet mode
    """
    # Find matching files
    tex_files = sorted(RESUME_ARCHIVE_PATH.glob(pattern))

    if not tex_files:
        typer.secho(
            f"No files found matching {pattern} in {RESUME_ARCHIVE_PATH}",
            fg=typer.colors.RED,
            err=True
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
    with open(log_file, 'w', encoding='utf-8') as log:
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
                    print(f"[{i}/{len(tex_files)}] {tex_file.name}...", end=' ', flush=True)

                log.write(f"[{i}/{len(tex_files)}] {tex_file.name}\n")

                # Each file gets its own subdirectory
                work_dir = log_dir / tex_file.stem
                result = test_single_file(
                    tex_file,
                    work_dir,
                    max_latex_diffs,
                    max_yaml_diffs
                )
                results.append(result)

                if result['error']:
                    if not quiet:
                        typer.secho(f"✗ ERROR: {result['error']}", fg=typer.colors.RED)
                    log.write(f"  ERROR: {result['error']}\n\n")
                else:
                    latex_status = "PASS" if result['latex_roundtrip']['success'] else "FAIL"
                    yaml_status = "PASS" if result['yaml_roundtrip']['success'] else "FAIL"

                    log.write(f"  LaTeX: {latex_status} ({result['latex_roundtrip']['num_diffs']} diffs)\n")
                    log.write(f"  YAML: {yaml_status} ({result['yaml_roundtrip']['num_diffs']} diffs)\n")
                    log.write(f"  Time: {result['time_ms']:.0f}ms\n")

                    if result['validation_passed']:
                        # Check if perfect roundtrip (0 diffs in both)
                        perfect_roundtrip = (
                            result['latex_roundtrip']['num_diffs'] == 0 and
                            result['yaml_roundtrip']['num_diffs'] == 0
                        )

                        if not quiet:
                            typer.secho(f"✓ ({result['time_ms']:.0f}ms)", fg=typer.colors.GREEN)

                        log.write(f"  Validation: PASSED\n")

                        # Clean up work directory only on perfect roundtrip (unless --keep-all)
                        if perfect_roundtrip and not keep_all:
                            shutil.rmtree(work_dir)
                            log.write(f"  Perfect roundtrip - artifacts cleaned\n\n")
                        elif keep_all:
                            log.write(f"  Artifacts kept (--keep-all flag)\n\n")
                        else:
                            log.write(f"  Artifacts kept (has diffs within threshold)\n\n")
                    else:
                        if not quiet:
                            typer.secho(
                                f"✗ LaTeX:{result['latex_roundtrip']['num_diffs']} "
                                f"YAML:{result['yaml_roundtrip']['num_diffs']}",
                                fg=typer.colors.RED
                            )
                        log.write(f"  Validation: FAILED - artifacts kept\n\n")

        except KeyboardInterrupt:
            typer.secho("\n\nInterrupted by user", fg=typer.colors.YELLOW, err=True)
            log.write("\n\nInterrupted by user\n")
            raise typer.Exit(code=130)

    # Generate summary
    passed = sum(1 for r in results if r['validation_passed'])
    failed = sum(1 for r in results if not r['validation_passed'])
    errors = sum(1 for r in results if r['error'])
    perfect = sum(
        1 for r in results
        if r['validation_passed'] and
        r['latex_roundtrip']['num_diffs'] == 0 and
        r['yaml_roundtrip']['num_diffs'] == 0
    )
    total = len(results)

    total_latex_diffs = sum(
        r['latex_roundtrip']['num_diffs']
        for r in results
        if r['latex_roundtrip']['num_diffs'] is not None
    )
    total_yaml_diffs = sum(
        r['yaml_roundtrip']['num_diffs']
        for r in results
        if r['yaml_roundtrip']['num_diffs'] is not None
    )

    if not quiet:
        typer.echo("=" * 80)
        typer.echo(f"\nSummary:")
        typer.echo(f"  Total files:           {total}")
        typer.echo(f"  Passed:                {passed}/{total} ({100*passed/total:.1f}%)")
        typer.echo(f"  Perfect (0 diffs):     {perfect}/{total} ({100*perfect/total:.1f}%)")
        typer.echo(f"  Failed:                {failed}/{total}")
        typer.echo(f"  Total LaTeX diffs:     {total_latex_diffs:,}")
        typer.echo(f"  Total YAML diffs:      {total_yaml_diffs:,}")
        typer.echo(f"  Errors:                {errors}")

    # Save summary.txt
    summary_file = log_dir / "summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"Roundtrip Test Summary - {timestamp}\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total files:           {total}\n")
        f.write(f"Passed:                {passed}/{total} ({100*passed/total:.1f}%)\n")
        f.write(f"Perfect (0 diffs):     {perfect}/{total} ({100*perfect/total:.1f}%)\n")
        f.write(f"Failed:                {failed}/{total}\n")
        f.write(f"Total LaTeX diffs:     {total_latex_diffs:,}\n")
        f.write(f"Total YAML diffs:      {total_yaml_diffs:,}\n")
        f.write(f"Errors:                {errors}\n\n")

        # Find longest filename for alignment
        max_filename_len = max(len(r['file']) for r in results)

        for r in results:
            # Calculate padding with dots
            padding = '.' * (max_filename_len - len(r['file']))

            if r['error']:
                f.write(f"{r['file']}{padding}: ERROR - {r['error']}\n")
            else:
                # Always show diff counts, even when passing
                latex_str = f"PASS ({r['latex_roundtrip']['num_diffs']})" if r['latex_roundtrip']['success'] else f"FAIL ({r['latex_roundtrip']['num_diffs']})"
                yaml_str = f"PASS ({r['yaml_roundtrip']['num_diffs']})" if r['yaml_roundtrip']['success'] else f"FAIL ({r['yaml_roundtrip']['num_diffs']})"
                status = "PASS" if r['validation_passed'] else "FAIL"
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
