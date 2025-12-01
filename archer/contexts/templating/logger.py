"""
Templating context logger.

Provides logging interface for templating context with automatic [template] prefix.
All templating modules should import from this module, not from utils.logger directly.
"""

from pathlib import Path

from loguru import logger

from archer.utils.logger import setup_logger as _setup_logger

CONTEXT_PREFIX = "[template]"


def setup_templating_logger(log_dir: Path, phase: str = "template") -> Path:
    """
    Setup logger for templating context.

    Configures loguru with provenance tracking and templating-specific context.

    Args:
        log_dir: Directory for this templating session
        phase: Phase name for provenance ("parse" or "generate")

    Returns:
        Path to log file

    Example:
        from archer.contexts.templating.logger import setup_templating_logger, _log_info

        log_file = setup_templating_logger(log_dir, phase="parse")
        _log_info("Starting parsing...")
    """
    return _setup_logger(
        context_name="template",
        log_dir=log_dir,
        extra_provenance={"Phase": phase},
    )


# Wrapper functions with automatic [template] prefix


def _log_info(message: str) -> None:
    """Log info message with [template] prefix."""
    logger.info(f"{CONTEXT_PREFIX} {message}")


def _log_success(message: str) -> None:
    """Log success message with [template] prefix."""
    logger.success(f"{CONTEXT_PREFIX} {message}")


def _log_error(message: str) -> None:
    """Log error message with [template] prefix."""
    logger.error(f"{CONTEXT_PREFIX} {message}")


def _log_warning(message: str) -> None:
    """Log warning message with [template] prefix."""
    logger.warning(f"{CONTEXT_PREFIX} {message}")


def _log_debug(message: str) -> None:
    """Log debug message with [template] prefix."""
    logger.debug(f"{CONTEXT_PREFIX} {message}")


# High-level templating-specific logging helpers


def log_conversion_start(
    resume_name: str, input_path: Path, log_file: Path, phase_name: str
) -> None:
    """Log start of conversion with context."""
    _log_info(f"Starting to {phase_name} {resume_name}")
    _log_info(f"Log file: {log_file}")
    _log_debug(f"Source: {input_path}")


def log_conversion_result(
    resume_name: str,
    result,  # ConversionResult
    elapsed_time: float,
    phase_name: str,
) -> None:
    """
    Log conversion result with validation details.

    Args:
        resume_name: Resume identifier
        result: ConversionResult from parse_resume() or generate_resume()
        elapsed_time: Time taken
        phase_name: "parse" or "generate"
    """
    # Log validation info
    if result.error:
        _log_error("Roundtrip validation errored out")
    elif result.success:
        _log_success(
            f"Roundtrip validation passed (LaTeX diffs: {result.latex_diffs}, YAML diffs: {result.yaml_diffs})"
        )
    else:
        _log_error(
            f"Roundtrip validation failed (LaTeX diffs: {result.latex_diffs}, YAML diffs: {result.yaml_diffs})"
        )

    # Log final result
    if result.success:
        _log_success(f"{resume_name}: {phase_name} succeeded ({elapsed_time:.2f}s)")
        if result.output_path:
            _log_info(f"  Output: {result.output_path}")
    else:
        _log_error(f"Failed to {phase_name} {resume_name} ({elapsed_time:.2f}s)")
        if result.error:
            _log_error(f"  Error: {result.error}")


def log_normalization_start(resume_name: str, input_path: Path, log_file: Path) -> None:
    """Log start of normalization."""
    _log_info(f"Starting to normalize {resume_name}")
    _log_info(f"Log file: {log_file}")
    _log_debug(f"Source: {input_path}")


def log_normalization_result(resume_name: str, result, elapsed_time: float, success: bool) -> None:
    """Log normalization result."""
    if success:
        _log_success(f"{resume_name}: normalization succeeded ({elapsed_time:.2f}s)")
        if result.output_path:
            _log_info(f"  Output: {result.output_path}")
        if result.message:
            logger.opt(raw=True).debug(f'process_file message: "{result.message}"')
    else:
        _log_error(f"Failed to normalize {resume_name} ({elapsed_time:.2f}s)")
        _log_error(f'  process_file message: "{result.message}"')
