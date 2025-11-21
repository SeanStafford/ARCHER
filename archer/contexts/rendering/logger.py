"""
Rendering context logger.

Provides logging interface for rendering context with automatic [render] prefix.
All rendering modules should import from this module, not from utils.logger directly.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from archer.utils.logger import setup_logger as _setup_logger

load_dotenv()

CONTEXT_PREFIX = "[render]"


def setup_rendering_logger(log_dir: Path) -> Path:
    """
    Setup logger for rendering context.

    Configures loguru with provenance tracking and rendering-specific context.

    Args:
        log_dir: Directory for this rendering session

    Returns:
        Path to log file

    Example:
        from archer.contexts.rendering.logger import setup_rendering_logger, info

        log_file = setup_rendering_logger(log_dir)
        info("Starting compilation...")
    """
    return _setup_logger(
        context_name="render",
        log_dir=log_dir,
        extra_provenance={"LaTeX compiler": os.getenv("LATEX_COMPILER")},
    )


# Wrapper functions with automatic [render] prefix


def _log_info(message: str) -> None:
    """Log info message with [render] prefix."""
    logger.info(f"{CONTEXT_PREFIX} {message}")


def _log_success(message: str) -> None:
    """Log success message with [render] prefix."""
    logger.success(f"{CONTEXT_PREFIX} {message}")


def _log_error(message: str) -> None:
    """Log error message with [render] prefix."""
    logger.error(f"{CONTEXT_PREFIX} {message}")


def _log_warning(message: str) -> None:
    """Log warning message with [render] prefix."""
    logger.warning(f"{CONTEXT_PREFIX} {message}")


def _log_debug(message: str) -> None:
    """Log debug message with [render] prefix."""
    logger.debug(f"{CONTEXT_PREFIX} {message}")


# High-level rendering-specific logging helpers


def log_compilation_start(
    resume_name: str, tex_file: Path, num_passes: int, working_dir: Path
) -> None:
    """Log start of compilation with context."""
    _log_info(f"Starting compilation: {resume_name}")
    _log_info(f"Compiling in {working_dir}")
    _log_debug(f"  Source: {tex_file}")
    _log_debug(f"  Passes: {num_passes}")


def log_compilation_result(
    resume_name: str,
    result,  # CompilationResult
    elapsed_time: float,
    verbose: bool = False,
) -> None:
    """
    Log compilation result with diagnostics.

    Args:
        resume_name: Resume identifier
        result: CompilationResult from compile_latex()
        elapsed_time: Time taken to compile
        verbose: Show detailed warnings/errors (default: False)
    """
    if result.success:
        _log_success("Compilation succeeded.")
        _log_success(f"{resume_name}: {len(result.warnings)} warnings ({elapsed_time:.2f}s)")
        if result.pdf_path:
            _log_debug(f"  PDF: {result.pdf_path}")
    else:
        _log_error("Compilation failed.")
        _log_error(f"{resume_name}: {len(result.errors)} errors ({elapsed_time:.2f}s)")
        error_limit = 10 if verbose else 5
        for i, err in enumerate(result.errors[:error_limit], 1):
            _log_error(f"  Error {i}: {err}")
        if len(result.errors) > error_limit:
            _log_error(f"  ... and {len(result.errors) - error_limit} more errors")

    # Log warnings at debug level (can be verbose)
    if result.warnings:
        _log_warning(f"{len(result.warnings)} warnings detected")
        warning_limit = 10 if verbose else 3
        for i, warn in enumerate(result.warnings[:warning_limit], 1):
            _log_debug(f"  Warning {i}: {warn}")
        if len(result.warnings) > warning_limit:
            _log_debug(f"  ... and {len(result.warnings) - warning_limit} more warnings")

    # Log full pdflatex output in verbose mode (or always on failure)
    # Use opt(raw=True) to bypass format template and preserve original formatting
    # This prevents loguru from adding timestamp/level to every line of multi-line output
    if verbose or not result.success:
        if result.stdout:
            logger.opt(raw=True).debug(
                f"\n{'=' * 80}\nPDFLATEX STDOUT:\n{'=' * 80}\n{result.stdout}\n"
            )
        if result.stderr:
            logger.opt(raw=True).debug(
                f"\n{'=' * 80}\nPDFLATEX STDERR:\n{'=' * 80}\n{result.stderr}\n"
            )
