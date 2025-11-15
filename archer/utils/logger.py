"""
Generic logger setup utilities for Tier 1 (detailed) logging.

Provides reusable loguru configuration with provenance tracking.
Context-specific wrappers should be defined in contexts/{context}/logger.py.
"""

import os
import sys
from pathlib import Path

from loguru import logger
from dotenv import load_dotenv

load_dotenv()


def setup_logger(
    context_name: str,
    log_dir: Path,
    extra_provenance: dict = None
) -> Path:
    """
    Configure loguru for a context with provenance tracking.

    Sets up dual output (file + console) and logs execution provenance
    (script, command, working directory, Python version, etc.).

    Args:
        context_name: Context identifier (e.g., "render", "template", "target")
        log_dir: Directory for this logging session
        extra_provenance: Additional key-value pairs for provenance header

    Returns:
        Path to log file

    Example:
        from archer.utils.logger import setup_logger

        log_file = setup_logger(
            context_name="render",
            log_dir=Path("outs/logs/render_20251114_123456"),
            extra_provenance={"LaTeX compiler": "pdflatex"}
        )
    """
    log_dir.mkdir(exist_ok=True, parents=True)
    log_file = log_dir / f"{context_name}.log"

    # Remove default logger
    logger.remove()

    # Add file handler - captures everything (DEBUG level)
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <7} | {message}",
        level="DEBUG"
    )

    # Add console handler - only INFO and above
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <7} | {message}",
        level="INFO",
        colorize=True
    )

    # Log provenance header
    log_provenance(extra_provenance)

    return log_file


def log_provenance(extra_context: dict = None) -> None:
    """
    Log execution provenance to current logger.

    Logs standard context (script, command, working directory, Python version)
    plus any additional context provided.

    Args:
        extra_context: Additional key-value pairs to log

    Example:
        from loguru import logger
        from archer.utils.logger import log_provenance

        logger.add("session.log")
        log_provenance(extra_context={"LaTeX compiler": "pdflatex"})
    """
    logger.info("=" * 80)
    logger.info(f"Script: {sys.argv[0]}")
    logger.info(f"Command: {' '.join(sys.argv)}")
    logger.info(f"Working directory: {Path.cwd()}")
    logger.info(f"Python: {sys.version.split()[0]}")

    if extra_context:
        for key, value in extra_context.items():
            logger.info(f"{key}: {value}")

    logger.info("=" * 80)
