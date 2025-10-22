import re
from pathlib import Path
from typing import List, Set


class CommentType:
    """Enum-like class for comment types"""

    DECORATIVE = "decorative"
    SECTION_HEADERS = "section_headers"
    DESCRIPTIVE = "descriptive"
    COMMENTED_CODE = "commented_code"
    INLINE_ANNOTATIONS = "inline_annotations"
    INLINE_DATES = "inline_dates"
    ALL = "all"
    NONE = "none"

    @classmethod
    def get_all_types(cls) -> Set[str]:
        """Return all comment types except ALL and NONE"""
        return {
            cls.DECORATIVE,
            cls.SECTION_HEADERS,
            cls.DESCRIPTIVE,
            cls.COMMENTED_CODE,
            cls.INLINE_ANNOTATIONS,
            cls.INLINE_DATES,
        }
