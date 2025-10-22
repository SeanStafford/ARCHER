#!/usr/bin/env python3

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
    tex_files = list(RAW_ARCHIVE_PATH.glob("*.tex"))
    success_count = 0
    error_count = 0
    for tex_file in tex_files:

        output_file = RESUME_ARCHIVE_PATH / tex_file.name

        # process_file handles reading, cleaning, and writing
        success, message = process_file(
            tex_file,
            output_file,
            ["all"],
            remove_suggest_blocks=True,
            dry_run=False,
        )

        if success:
            success_count += 1
            print(f"✓ {message}")
        else:
            error_count += 1
            print(f"✗ {message}", file=sys.stderr)

    print(f"Summary: {success_count} succeeded, {error_count} failed")

if __name__ == "__main__":
    main()
