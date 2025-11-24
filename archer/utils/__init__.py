"""
Shared utilities for ARCHER.

Common functionality used across contexts:
- Text processing
- LaTeX helpers
- File operations
- Configuration management
"""

from archer.utils.resume_registry import get_resume_file
from archer.utils.timestamp import now, now_exact, today

__all__ = ["get_resume_file", "now", "now_exact", "today"]
