#!/usr/bin/env python3
"""
Statistical analysis of LaTeX resume patterns.

Analyzes keyword frequency across resume files to inform template structure:
1. Percentage of resumes containing keyword at least once
2. Percentage of total text composed of keyword
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from archer.utils.resume_analyzer import analyze_keyword_frequencies, format_analysis_report

# Load environment variables
load_dotenv()
RESUME_ARCHIVE_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH"))

# Keyword categories to analyze
KEYWORDS = {
    "Section Titles (Left Column Page 1)": [
        "AI & Machine Learning",
        "AI \\& Machine Learning",
        "Software Tools",
        "ML Infrastructure Tools",
        "Machine Learning & AI",
        "SE Toolbox",
        "Core Skills",
        "Other ML Capabilities",
    ],

    "Personality Section Titles": [
        "Marketable Monikers",
        "Proficiency Pseudonyms",
        "Alias Array",
        "Alliterative Aliases",
    ],

    "Bottom Bar Elements": [
        "\\bottombar",
        "\\leftgrad",
        "Two Truths and a Lie",
    ],

    "Name Formatting": [
        "\\textbf{Sean Stafford}",
        "\\renewcommand{\\myname}{Sean Stafford}",
    ],

    "Project Section Titles": [
        "LLM Research Portfolio",
        "Other Projects I'm Proud Of",
        "Projects I'm Proud Of",
    ],

    "Special Sections": [
        "HPC Highlights",
        "Passions",
        "\\phantomsection",
    ],

    "Subsection Formatting": [
        "\\item[\\faRobot]",
        "\\item[]",
        "\\itemLL",
        "\\item[--]",
    ],

    "Professional Profile Formatting": [
        "\\centering \\textbf{",
        "\\centering {",
    ],

    "Environment Usage": [
        "itemizeAcademic",
        "itemizeAProject",
        "itemizeKeyProject",
        "itemizeProjMain",
        "itemizeProjSecond",
        "itemizeSecond",
        "itemizeLL",
    ],
}


def main():
    """Run keyword frequency analysis on resume archive."""
    if not RESUME_ARCHIVE_PATH.exists():
        print(f"Error: Directory {RESUME_ARCHIVE_PATH} does not exist")
        return 1

    try:
        num_resumes, total_chars, keyword_total_occurrences, keyword_resume_count = (
            analyze_keyword_frequencies(RESUME_ARCHIVE_PATH, KEYWORDS)
        )

        report = format_analysis_report(
            num_resumes,
            total_chars,
            KEYWORDS,
            keyword_total_occurrences,
            keyword_resume_count,
            RESUME_ARCHIVE_PATH
        )

        print(report)
        return 0

    except ValueError as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
