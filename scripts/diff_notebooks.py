#!/usr/bin/env python
"""
Diff two Jupyter notebooks, comparing only cell contents.

Ignores outputs, metadata, and whitespace-only cells.
Uses difflib for proper alignment (handles inserted/deleted cells).

Usage:
    python scripts/diff_notebooks.py notebook1.ipynb notebook2.ipynb
    python scripts/diff_notebooks.py notebook1.ipynb notebook2.ipynb --min 5 --max 10
"""

import argparse
import difflib
import json
from pathlib import Path

# ANSI color codes
RED = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"


def red(text: str) -> str:
    return f"{RED}{text}{RESET}"


def green(text: str) -> str:
    return f"{GREEN}{text}{RESET}"


def colorize_diff_line(line: str) -> str:
    """Colorize a diff line based on its prefix."""
    if line.startswith("+"):
        return green(line)
    elif line.startswith("-"):
        return red(line)
    return line


def extract_cells(notebook_path: Path) -> list[tuple[str, str]]:
    """Extract (cell_type, source) tuples from notebook, skipping whitespace-only cells."""
    with open(notebook_path) as f:
        nb = json.load(f)

    cells = []
    for cell in nb["cells"]:
        try:
            cell_type, source = cell["cell_type"], cell["source"]
        except KeyError as e:
            raise ValueError(f"Malformed notebook {notebook_path}: missing key {e}") from e

        # Jupyter stores source as either a string or list of lines
        if isinstance(source, list):
            source = "".join(source)

        # Skip whitespace-only cells
        if not source.strip():
            continue

        cells.append((cell_type, source))

    return cells


def main():
    parser = argparse.ArgumentParser(description="Diff two Jupyter notebooks")
    parser.add_argument("notebook1", type=Path, help="First notebook")
    parser.add_argument("notebook2", type=Path, help="Second notebook")
    parser.add_argument(
        "--min", type=int, default=1, help="Minimum cell number (1-indexed, inclusive)"
    )
    parser.add_argument(
        "--max", type=int, default=None, help="Maximum cell number (1-indexed, inclusive)"
    )
    parser.add_argument(
        "--no-color", action="store_true", help="Disable colored output"
    )
    args = parser.parse_args()

    # Disable colors if requested
    if args.no_color:
        global RED, GREEN, RESET
        RED = GREEN = RESET = ""

    path1, path2 = args.notebook1, args.notebook2

    cells1 = extract_cells(path1)
    cells2 = extract_cells(path2)

    # Apply cell range filter (convert to 0-indexed)
    min_idx = args.min - 1
    max_idx = args.max if args.max is None else args.max
    cells1 = cells1[min_idx:max_idx]
    cells2 = cells2[min_idx:max_idx]

    # Separate types and sources; include type in source for matching but track separately
    types1 = [t for t, s in cells1]
    types2 = [t for t, s in cells2]
    sources1 = [s for t, s in cells1]
    sources2 = [s for t, s in cells2]

    # For difflib matching, include type so different cell types don't match
    strings1 = [f"[{t}]\n{s}" for t, s in cells1]
    strings2 = [f"[{t}]\n{s}" for t, s in cells2]

    # SequenceMatcher finds the longest common subsequence between two lists.
    # This allows it to align matching cells even when cells are inserted/deleted.
    # First arg (None) means no "junk" filtering function.
    matcher = difflib.SequenceMatcher(None, strings1, strings2)

    # get_opcodes() returns tuples describing how to transform list1 into list2.
    # Each tuple: (tag, i1, i2, j1, j2) where:
    #   - tag: 'equal', 'replace', 'delete', or 'insert'
    #   - i1:i2 is the slice in strings1
    #   - j1:j2 is the slice in strings2
    has_diff = False
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        has_diff = True

        # Cell numbers adjusted for --min offset (display as 1-indexed)
        offset = args.min

        # 'replace': cells at i1:i2 in file1 were replaced by cells at j1:j2 in file2
        # Show line-by-line diff within each replaced cell pair
        if tag == "replace":
            for idx1, idx2 in zip(range(i1, i2), range(j1, j2)):
                cell_num = idx1 + offset
                type1, type2 = types1[idx1], types2[idx2]
                # splitlines then re-add \n to ensure consistent line endings
                lines1 = [line + "\n" for line in sources1[idx1].splitlines()]
                lines2 = [line + "\n" for line in sources2[idx2].splitlines()]
                diff = list(difflib.unified_diff(
                    lines1,
                    lines2,
                    fromfile=f"Cell {cell_num} [{type1}] in {path1.name}",
                    tofile=f"Cell {cell_num} [{type2}] in {path2.name}",
                    n=3,  # lines of context around each change
                ))
                # First two lines are headers (--- and +++), need newlines added
                if diff:
                    print(red(diff[0].rstrip()))  # --- header
                    print(green(diff[1].rstrip()))  # +++ header
                    # Colorize remaining diff lines
                    for line in diff[2:]:
                        print(colorize_diff_line(line), end="")
                print()

            # Handle unmatched cells if ranges differ in length
            for idx in range(i1 + min(i2 - i1, j2 - j1), i2):
                print(red(f"--- Cell {idx + offset} [{types1[idx]}] in {path1.name} (deleted)"))
                print(red(sources1[idx]))
                print()
            for idx in range(j1 + min(i2 - i1, j2 - j1), j2):
                print(green(f"+++ Cell {idx + offset} [{types2[idx]}] in {path2.name} (inserted)"))
                print(green(sources2[idx]))
                print()

        # 'delete': cells at i1:i2 in file1 don't exist in file2
        elif tag == "delete":
            for idx in range(i1, i2):
                print(red(f"--- Cell {idx + offset} [{types1[idx]}] in {path1.name} (deleted)"))
                print(red(sources1[idx]))
                print()

        # 'insert': cells at j1:j2 in file2 don't exist in file1
        elif tag == "insert":
            for idx in range(j1, j2):
                print(green(f"+++ Cell {idx + offset} [{types2[idx]}] in {path2.name} (inserted)"))
                print(green(sources2[idx]))
                print()

    if not has_diff:
        print("No differences in cell contents.")


if __name__ == "__main__":
    main()
