"""
LaTeX Compilation Module

Handles compilation of .tex files to PDF using pdflatex.
"""

import os
import re
import shutil
import subprocess
import time
import warnings as warnings_module
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

from archer.contexts.rendering.logger import (
    _log_debug,
    _log_info,
    log_compilation_result,
    log_compilation_start,
    setup_rendering_logger,
)
from archer.utils.pdf_processing import page_count
from archer.utils.resume_registry import resume_is_registered, update_resume_status
from archer.utils.timestamp import now, today

load_dotenv()

LATEX_COMPILER = os.getenv("LATEX_COMPILER")
LOGS_PATH = Path(os.getenv("LOGS_PATH"))
RESULTS_PATH = Path(os.getenv("RESULTS_PATH"))
FIGS_PATH = Path(os.getenv("FIGS_PATH"))
KEEP_LATEX_ARTIFACTS = os.getenv("KEEP_LATEX_ARTIFACTS").lower() == "true"

# LaTeX intermediate files created during compilation
LATEX_ARTIFACTS = [".aux", ".log", ".out", ".toc"]


@dataclass
class CompilationResult:
    """
    Result of LaTeX compilation.

    Attributes:
        success: Whether compilation succeeded
        pdf_path: Path to generated PDF (None if failed)
        stdout: Standard output from pdflatex
        stderr: Standard error from pdflatex
        errors: List of parsed LaTeX errors
        warnings: List of parsed LaTeX warnings
        page_count: Number of pages in generated PDF (None if not available)
    """

    success: bool
    pdf_path: Optional[Path] = None
    stdout: str = ""
    stderr: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    page_count: Optional[int] = None


def _parse_latex_log(log_content: str) -> tuple[List[str], List[str]]:
    """
    Parse LaTeX log file for errors and warnings.

    Args:
        log_content: Content of the .log file

    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []

    # LaTeX error pattern: "! Error message"
    error_pattern = re.compile(r"^! (.+)$", re.MULTILINE)
    for match in error_pattern.finditer(log_content):
        errors.append(match.group(1).strip())

    # Additional error patterns that don't start with "!"
    additional_error_patterns = [
        r"Undefined control sequence",
        r"File ended while scanning use of",
        r"Emergency stop",
    ]
    for pattern in additional_error_patterns:
        if re.search(pattern, log_content):
            # Extract the specific error line
            match = re.search(rf"({pattern}.*?)$", log_content, re.MULTILINE)
            if match and match.group(1) not in errors:
                errors.append(match.group(1))

    # Common warning patterns
    warning_patterns = [
        r"LaTeX Warning: (.+)",
        r"Package \w+ Warning: (.+)",
        r"Overfull \\hbox \((.+)\)",
        r"Underfull \\hbox \((.+)\)",
    ]

    for pattern in warning_patterns:
        compiled = re.compile(pattern, re.MULTILINE)
        for match in compiled.finditer(log_content):
            warnings.append(match.group(1).strip())

    return errors, warnings


def _remove_artifacts(tex_path: Path) -> None:
    """
    Remove intermediate LaTeX files.

    Args:
        tex_path: Path to the .tex file
    """
    base_path = tex_path.parent / tex_path.stem

    for ext in LATEX_ARTIFACTS:
        artifact_path = base_path.with_suffix(ext)
        if artifact_path.exists():
            artifact_path.unlink()


def compile_latex(
    tex_file: Path,
    compile_dir: Optional[Path] = None,
    num_passes: int = 2,
    keep_artifacts: bool = KEEP_LATEX_ARTIFACTS,
    fig_dir: Optional[Path] = FIGS_PATH,
) -> CompilationResult:
    """
    Compile a LaTeX file to PDF using pdflatex.

    Pure compilation function - assumes paths are resolved and directories exist.

    Args:
        tex_file: Path to the .tex file to compile
        compile_dir: Path to output directory (must exist)
        num_passes: Number of pdflatex passes (default: 2 for cross-references)
        keep_artifacts: Keep intermediate files (default: from KEEP_LATEX_ARTIFACTS env)

    Returns:
        CompilationResult with success status and diagnostic information
    """

    assert tex_file.exists(), f"TeX file not found: {tex_file}"
    original_tex_file = tex_file

    if compile_dir is None:
        # Warn about in-place compilation
        warnings_module.warn(
            f"No compile_dir specified. Will compile in-place at: {tex_file.parent}\n"
            "This will create artifacts (.aux, .log, .out, .toc, .pdf) in the source directory.",
            UserWarning,
        )

        response = input("Proceed with in-place compilation? [Y/n]: ").strip().lower()
        if response and response not in ["y", "yes", "yeppers"]:
            return CompilationResult(success=False, errors=["Compilation cancelled by user"])

        compile_dir = tex_file.parent.resolve()
    else:
        # Copy tex file to output directory for compilation
        # pdflatex runs in compile_dir so mystyle/ can be found via TEXINPUTS
        tex_file = compile_dir / tex_file.name
        shutil.copy2(original_tex_file, tex_file)

    # Create symlink to figures directory so LaTeX can find them via \graphicspath
    # Resume .tex files use \graphicspath{{./}{Figs/}} which looks for Figs/ in cwd
    figs_symlink = compile_dir / "Figs"
    if fig_dir is not None:
        if not fig_dir.exists():
            return CompilationResult(
                success=False, errors=[f"Figures directory not found: {fig_dir}"]
            )
        if not figs_symlink.exists():
            figs_symlink.symlink_to(fig_dir)

    # Clean any existing output files to ensure unambiguous success detection
    # Missing log file → compilation failed; existing PDF → compilation succeeded
    stem = tex_file.stem
    for ext in [".pdf"] + LATEX_ARTIFACTS:
        old_file = compile_dir / f"{stem}{ext}"
        if old_file.exists():
            old_file.unlink()

    all_stdout = []
    all_stderr = []
    success = True

    # Multiple passes needed for cross-references, TOC, and page numbers
    # First pass generates .aux, second pass resolves references
    for _ in range(num_passes):
        cmd = [
            LATEX_COMPILER,
            "-interaction=nonstopmode",
            "-file-line-error",
            tex_file.name,
        ]

        result = subprocess.run(
            cmd,
            cwd=compile_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",  # Replace invalid UTF-8 bytes instead of crashing
        )

        all_stdout.append(result.stdout)
        all_stderr.append(result.stderr)

        # Stop on fatal errors (returncode != 0 means pdflatex crashed)
        # Log file parsing below will distinguish errors from warnings
        if result.returncode != 0:
            success = False
            break

    combined_stdout = "\n".join(all_stdout)
    combined_stderr = "\n".join(all_stderr)

    # Parse log file for detailed errors and warnings
    log_file = compile_dir / f"{tex_file.stem}.log"
    errors = []
    warnings = []

    if log_file.exists():
        # pdflatex writes log files in latin-1 encoding (font metadata contains non-UTF-8)
        log_content = log_file.read_text(encoding="latin-1")
        errors, warnings = _parse_latex_log(log_content)

    # Check if PDF was generated
    pdf_path = compile_dir / f"{tex_file.stem}.pdf"
    if not pdf_path.exists():
        success = False
        if not errors:
            errors.append("PDF file was not generated")
    elif len(errors) == 0:
        # PDF exists and no LaTeX errors found - consider it a success
        # even if pdflatex returned non-zero (which can happen for warnings)
        success = True

    # Cleanup artifacts (.aux, .log, .out, .toc)
    if not keep_artifacts:
        _remove_artifacts(tex_file)

    # Remove copied tex file (keep compile_dir clean, source remains untouched)
    if original_tex_file != tex_file and tex_file.exists():
        tex_file.unlink()

    # Remove Figs symlink (keep compile_dir clean)
    figs_symlink = compile_dir / "Figs"
    if figs_symlink.exists() and figs_symlink.is_symlink():
        figs_symlink.unlink()

    # Get page count from generated PDF
    pdf_page_count = page_count(pdf_path) if pdf_path.exists() else None

    return CompilationResult(
        success=success,
        pdf_path=pdf_path if pdf_path.exists() else None,
        stdout=combined_stdout,
        stderr=combined_stderr,
        errors=errors,
        warnings=warnings,
        page_count=pdf_page_count,
    )


def compile_resume(
    tex_file: Path,
    output_dir: Optional[Path] = None,
    num_passes: int = 2,
    verbose: bool = False,
    keep_artifacts_on_success: bool = False,
) -> CompilationResult:
    """
    Compile a resume LaTeX file with registry tracking and organized output management.

    Orchestration function that wraps compile_latex() with ARCHER-specific
    resume tracking via the registry system. Logs status changes to the
    pipeline event log (Tier 2 logging).

    On success:
        - Moves PDF to outs/results/YYYY-MM-DD/
        - Creates symlink in log directory pointing to PDF
        - Saves minimal render.log (or detailed if verbose=True)
        - Deletes artifacts (unless keep_artifacts_on_success=True)

    On failure:
        - Keeps all artifacts in log directory for debugging
        - Saves detailed render.log with full stdout/stderr

    Args:
        tex_file: Path to the resume .tex file to compile
        output_dir: Directory for output files (default: None, uses timestamped log directory)
        num_passes: Number of pdflatex passes (default: 2 for cross-references)
        verbose: Show detailed warnings/errors in logs (default: False)
        keep_artifacts_on_success: Keep LaTeX artifacts (.aux, .log, etc.) on success (default: False)

    Returns:
        CompilationResult with success status and diagnostic information
    """

    tex_file = Path(tex_file).resolve()
    # Early validation before any registry updates
    if not tex_file.exists():
        return CompilationResult(success=False, errors=[f"TeX file not found: {tex_file}"])

    # Extract resume name for registry lookup (registry uses file stem)
    resume_name = tex_file.stem
    # Verify resume is registered in the tracking system
    if not resume_is_registered(resume_name):
        return CompilationResult(success=False, errors=[f"Resume not registered: {resume_name}"])

    # Create timestamped log directory for this compilation
    timestamp = now()
    log_dir = LOGS_PATH / f"render_{timestamp}"
    log_dir.mkdir(parents=True, exist_ok=True)

    if output_dir is None:
        output_dir = log_dir
    else:
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

    # Setup loguru logger with provenance
    setup_rendering_logger(log_dir)

    # Log start of compilation (Tier 1)
    log_compilation_start(resume_name, tex_file, num_passes, log_dir)

    # Log start of compilation to pipeline events by setting status to 'compiling' (Tier 2)
    update_resume_status(updates={resume_name: "compiling"}, source="rendering")

    start_time = time.time()

    # Actually compile the LaTeX file
    result = compile_latex(
        tex_file=tex_file,
        compile_dir=output_dir,
        num_passes=num_passes,
        keep_artifacts=True,  # Always keep initially, we'll clean up based on success
    )

    compilation_time_s = time.time() - start_time

    # Log compilation result (Tier 1)
    log_compilation_result(
        resume_name=resume_name, result=result, elapsed_time=compilation_time_s, verbose=verbose
    )

    # Handle success vs failure
    if result.success:
        # Move PDF to dated results directory
        results_dir = RESULTS_PATH / today()
        results_dir.mkdir(parents=True, exist_ok=True)

        final_pdf = results_dir / f"{resume_name}.pdf"
        shutil.move(result.pdf_path, final_pdf)
        _log_info(f"PDF saved to: {final_pdf}")

        # Create symlink in log directory pointing to final PDF
        pdf_symlink = log_dir / f"{resume_name}.pdf"
        pdf_symlink.symlink_to(final_pdf)

        # Clean up artifacts on success (unless keep_artifacts_on_success=True)
        if not keep_artifacts_on_success:
            for ext in LATEX_ARTIFACTS:
                artifact = output_dir / f"{resume_name}{ext}"
                if artifact.exists():
                    artifact.unlink()
            _log_debug("Cleaned up LaTeX artifacts.")
        else:
            _log_debug("Keeping LaTeX artifacts (keep_artifacts_on_success=True).")

        # Update result with new PDF path
        result.pdf_path = final_pdf

        # Log success to pipeline events (Tier 2)
        update_resume_status(
            updates={resume_name: "compiling_completed"},
            source="rendering",
            compilation_time_s=round(compilation_time_s, 2),
            warning_count=len(result.warnings),
            num_passes=num_passes,
            pdf_path=str(final_pdf),
            page_count=result.page_count,
        )
    else:  # Compilation failed
        # Keep artifacts for debugging on failure
        _log_debug("Keeping artifacts: compilation failed")

        # Log failure to pipeline events (Tier 2)
        update_resume_status(
            updates={resume_name: "compiling_failed"},
            source="rendering",
            compilation_time_s=round(compilation_time_s, 2),
            error_count=len(result.errors),
            errors=result.errors[:5] if result.errors else [],
        )

    return result
