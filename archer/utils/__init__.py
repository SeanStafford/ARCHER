"""
Shared utilities for ARCHER.

Common functionality used across contexts:
- Text processing
- LaTeX helpers
- File operations
- Configuration management
"""

from archer.utils.timestamp import now, now_exact, today

__all__ = ["now", "now_exact", "today"]
