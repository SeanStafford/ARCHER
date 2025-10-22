#!/usr/bin/env python3
"""
Batch clean all resume files from raw/ to parent directory.

Removes inline annotations (% ----), commented-out code (% \command), and
\suggest{...} blocks from all .tex files in data/resume_archive/raw/, writing
cleaned versions to data/resume_archive/.

Usage:
    python scripts/clean_all_resumes.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from archer.utils.latex_cleaner import process_file, CommentType

# Load environment variables
load_dotenv()
RAW_ARCHIVE_PATH = Path(os.getenv("RAW_ARCHIVE_PATH"))
RESUME_ARCHIVE_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH"))


def main():
    """
    Clean all resume files from raw directory to output directory.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """

    # File processing settings
    # Define which comment types to remove (see CommentType class for more info)
    comment_types = {
        CommentType.INLINE_ANNOTATIONS,  # Removes % ---- style comments
        CommentType.COMMENTED_CODE,      # Removes % \setlength{...} style lines
    }
    # Note: This preserves descriptive comments, decorative separators, and inline dates
    remove_suggest_blocks=True # Also remove \suggest{...} blocks
    dry_run=False  # Actually write files (not just preview changes)

    # Get all raw tex files
    # glob() returns generator, sorted() converts to list in consistent order
    tex_files = sorted(RAW_ARCHIVE_PATH.glob("*.tex"))

    # Exit early if no files found
    if not tex_files:
        print(f"No .tex files found in {RAW_ARCHIVE_PATH}")
        return 1

    # Print configuration summary
    print(f"Cleaning {len(tex_files)} resume files...")
    print(f"Source: {RAW_ARCHIVE_PATH}")
    print(f"Destination: {RESUME_ARCHIVE_PATH}")
    print(f"Comment types: {', '.join(comment_types)}")
    print(f"Remove suggest blocks: True\n")

    success_count = 0
    error_count = 0
    for tex_file in tex_files:

        output_file = RESUME_ARCHIVE_PATH / tex_file.name

        # process_file() handles reading, cleaning, and writing
        success, message = process_file(
            tex_file,
            output_file,
            comment_types,
            remove_suggest_blocks=remove_suggest_blocks,
            dry_run=dry_run,
        )

        if success:
            success_count += 1
            print(f"✓ {message}")
        else:
            error_count += 1
            print(f"✗ {message}", file=sys.stderr)

    # Print outcome summary
    print(f"\n{'='*60}")
    print(f"Summary: {success_count} succeeded, {error_count} failed")
    print(f"{'='*60}")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
