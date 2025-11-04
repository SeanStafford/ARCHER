#!/usr/bin/env python3
"""
Batch process all resume files from raw/ to parent directory.

Cleans and normalizes all .tex files in data/resume_archive/raw/, writing
processed versions to data/resume_archive/.

Processing includes:
- Removing inline annotations (% ----), commented-out code (% \command)
- Removing \suggest{...} blocks
- Normalizing formatting (blank lines, Education header, trailing whitespace)

Usage:
    python scripts/process_all_resumes.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from archer.contexts.templating.process_latex_archive import process_file
from archer.utils.clean_latex import CommentType

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
    preamble_comment_types = { CommentType.ALL }
    body_comment_types = { CommentType.ALL }

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
    print(f"Processing {len(tex_files)} resume files...")
    print(f"Source: {RAW_ARCHIVE_PATH}")
    print(f"Destination: {RESUME_ARCHIVE_PATH}")
    print(f"Preamble comment types: {', '.join(preamble_comment_types)}")
    print(f"Body comment types: {', '.join(body_comment_types)}")
    print(f"Remove suggest blocks: True")
    print(f"Normalize formatting: True\n")

    success_count = 0
    error_count = 0
    for tex_file in tex_files:

        output_file = RESUME_ARCHIVE_PATH / tex_file.name

        # process_file() handles reading, cleaning, normalizing, and writing
        success, message = process_file(
            tex_file,
            output_file,
            body_comment_types,
            remove_suggest_blocks=remove_suggest_blocks,
            normalize=True,
            dry_run=dry_run,
            preamble_comment_types=preamble_comment_types,
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
