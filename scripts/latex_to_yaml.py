#!/usr/bin/env python3
"""
Command-line interface for converting LaTeX resumes to structured YAML format.

Validates conversions through roundtrip testing and saves validated YAMLs to
data/resume_archive/structured/ for use by the Targeting context.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import typer
from dotenv import load_dotenv
from omegaconf import OmegaConf

from archer.contexts.templating import latex_to_yaml, yaml_to_latex
from archer.contexts.templating.process_latex_archive import process_file
from archer.utils.text_processing import get_meaningful_diff

load_dotenv()
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT"))
RESUME_ARCHIVE_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH"))
LOGS_PATH = Path(os.getenv("LOGS_PATH"))

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


def compare_yaml_structured(yaml1_path: Path, yaml2_path: Path) -> tuple[List[str], int]:
    """
    Compare two YAML files using structured comparison.

    Uses OmegaConf to load both YAMLs and compare as dictionaries,
    ignoring formatting and key order differences.

    Returns:
        Tuple of (diff_lines, num_differences)
    """
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


def convert_single_file(
    tex_file: Path,
    work_dir: Path,
    max_latex_diffs: int,
    max_yaml_diffs: int
) -> Dict:
    """
    Convert a single LaTeX file to YAML with validation.

    Returns:
        Dict with conversion results: {
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


@app.command("list")
def list_command():
    """
    List all available resumes in the archive.

    Shows which resumes have been converted to YAML (in structured/)
    and which are pending conversion.

    Example:
        $ python scripts/latex_to_yaml.py list
    """
    # Get all .tex files from archive
    tex_files = sorted(RESUME_ARCHIVE_PATH.glob("*.tex"))

    if not tex_files:
        typer.secho(
            f"No resume files found in {RESUME_ARCHIVE_PATH}",
            fg=typer.colors.YELLOW,
            err=True
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


@app.command("convert")
def convert_command(
    tex_file: Path = typer.Argument(
        ...,
        help="Path to .tex file to convert",
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
):
    """
    Convert a single LaTeX resume to YAML with validation.

    On success, saves YAML to data/resume_archive/structured/.
    On failure, saves artifacts to outs/logs/convert_TIMESTAMP/.

    Examples:
        # Convert specific file
        $ python scripts/latex_to_yaml.py convert data/resume_archive/Res202507_Anthropic.tex

        # Strict validation (0 diffs for both)
        $ python scripts/latex_to_yaml.py convert Res202507_Anthropic.tex -l 0 -y 0

        # Verbose output
        $ python scripts/latex_to_yaml.py convert Res202507_Anthropic.tex -v
    """
    # Validate file extension
    if tex_file.suffix != ".tex":
        typer.secho(
            f"Error: File must have .tex extension: {tex_file}",
            fg=typer.colors.RED,
            err=True
        )
        raise typer.Exit(code=1)

    typer.secho(f"\nConverting: {tex_file.name}", fg=typer.colors.BLUE, bold=True)
    typer.echo(f"Validation thresholds: LaTeX ≤{max_latex_diffs}, YAML ≤{max_yaml_diffs}")

    # Create log directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = LOGS_PATH / f"convert_{timestamp}"
    work_dir.mkdir(exist_ok=True, parents=True)

    typer.echo(f"Log directory: {work_dir}\n")

    # Open log file
    log_file = work_dir / "convert.log"
    with open(log_file, 'w', encoding='utf-8') as log:
        log.write(f"Conversion Log - {timestamp}\n")
        log.write("=" * 80 + "\n")
        log.write(f"File: {tex_file.name}\n")
        log.write(f"Max LaTeX diffs: {max_latex_diffs}\n")
        log.write(f"Max YAML diffs: {max_yaml_diffs}\n")
        log.write("=" * 80 + "\n\n")

        try:
            result = convert_single_file(
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
                # Save YAML to structured directory
                structured_dir = RESUME_ARCHIVE_PATH / "structured"
                structured_dir.mkdir(exist_ok=True, parents=True)
                output_yaml = structured_dir / f"{tex_file.stem}.yaml"

                parsed_yaml = work_dir / f"{tex_file.stem}_parsed.yaml"
                output_yaml.write_text(parsed_yaml.read_text())

                log.write(f"\nValidation: PASSED\n")
                log.write(f"Saved: {output_yaml}\n")

                typer.secho(f"\n✓ Success! YAML saved to: {output_yaml}", fg=typer.colors.GREEN)

                # Clean up intermediate files but keep log
                import shutil
                for item in work_dir.iterdir():
                    if item.name != "convert.log":
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)

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
):
    """
    Convert all matching resumes to YAML with validation.

    Saves validated YAMLs to data/resume_archive/structured/.
    Failed conversions keep artifacts in outs/logs/convert_TIMESTAMP/.
    Generates summary.txt and convert.log in the log directory.

    Examples:
        # Convert all resumes
        $ python scripts/latex_to_yaml.py batch

        # Convert specific pattern
        $ python scripts/latex_to_yaml.py batch --pattern "Res2025*.tex"

        # Strict validation
        $ python scripts/latex_to_yaml.py batch -l 0 -y 0

        # Quiet mode
        $ python scripts/latex_to_yaml.py batch -q
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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = LOGS_PATH / f"convert_{timestamp}"
    log_dir.mkdir(exist_ok=True, parents=True)

    if not quiet:
        typer.secho(f"\nConverting {len(tex_files)} resumes", fg=typer.colors.BLUE, bold=True)
        typer.echo(f"Validation thresholds: LaTeX ≤{max_latex_diffs}, YAML ≤{max_yaml_diffs}")
        typer.echo(f"Log directory: {log_dir}")
        typer.echo("=" * 80)

    # Open log file
    log_file = log_dir / "convert.log"
    with open(log_file, 'w', encoding='utf-8') as log:
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
                    print(f"[{i}/{len(tex_files)}] {tex_file.name}...", end=' ', flush=True)

                log.write(f"[{i}/{len(tex_files)}] {tex_file.name}\n")

                work_dir = log_dir / tex_file.stem
                result = convert_single_file(
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
                                fg=typer.colors.RED
                            )
                        log.write(f"  Validation failed - artifacts kept\n\n")

        except KeyboardInterrupt:
            typer.secho("\n\nInterrupted by user", fg=typer.colors.YELLOW, err=True)
            log.write("\n\nInterrupted by user\n")
            raise typer.Exit(code=130)

    # Generate summary
    passed = sum(1 for r in results if r['validation_passed'])
    failed = sum(1 for r in results if not r['validation_passed'])
    errors = sum(1 for r in results if r['error'])
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
        typer.echo(f"  Failed:                {failed}/{total}")
        typer.echo(f"  Total LaTeX diffs:     {total_latex_diffs:,}")
        typer.echo(f"  Total YAML diffs:      {total_yaml_diffs:,}")
        typer.echo(f"  Errors:                {errors}")

    # Save summary.txt
    summary_file = log_dir / "summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"Conversion Summary - {timestamp}\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total files:           {total}\n")
        f.write(f"Passed:                {passed}/{total} ({100*passed/total:.1f}%)\n")
        f.write(f"Failed:                {failed}/{total}\n")
        f.write(f"Total LaTeX diffs:     {total_latex_diffs:,}\n")
        f.write(f"Total YAML diffs:      {total_yaml_diffs:,}\n")
        f.write(f"Errors:                {errors}\n\n")

        for r in results:
            if r['error']:
                f.write(f"{r['file']}: ERROR - {r['error']}\n")
            else:
                latex_str = "PASS" if r['latex_roundtrip']['success'] else f"FAIL ({r['latex_roundtrip']['num_diffs']})"
                yaml_str = "PASS" if r['yaml_roundtrip']['success'] else f"FAIL ({r['yaml_roundtrip']['num_diffs']})"
                status = "PASS" if r['validation_passed'] else "FAIL"
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
