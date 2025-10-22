#!/usr/bin/env python3
"""
Statistical analysis of LaTeX resume patterns.

Analyzes keyword frequency across resume files to inform template structure:
1. Percentage of resumes containing keyword at least once
2. Percentage of total text composed of keyword

Usage:
    # Print analysis to stdout
    python analyze_resume_patterns.py

    # Save analysis to file
    python analyze_resume_patterns.py --output pattern_analysis.txt
"""

import os
from pathlib import Path
from typing import Optional
from typing_extensions import Annotated

import typer
from dotenv import load_dotenv

from archer.utils.resume_analyzer import (
    analyze_keyword_frequencies,
    enumerate_field_values,
    format_analysis_report,
    format_field_enumeration_report,
)

# Load environment variables
load_dotenv()
RESUME_ARCHIVE_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH"))
LOGS_PATH = Path(os.getenv("LOGS_PATH"))

app = typer.Typer(
    add_completion=False,
)

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

    "Brand Elements": [
        "| Physicist",
        "Machine Learning Engineer",
        "Software Engineer",
        "ML Infrastructure Engineer",
        "Research Infrastructure Engineer",
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


@app.command()
def main(
    output: Annotated[
        Optional[Path],
        typer.Option(
            "--output",
            "-o",
            help="Save report to file (prints to stdout if not specified)",
            dir_okay=False,
        )
    ] = None,
):
    """
    Analyze keyword frequency patterns across resume archive.

    Generates a statistical report showing:
    - Percentage of resumes containing each keyword
    - Total occurrences of each keyword across all resumes

    Examples:

        # Print analysis to stdout
        python analyze_resume_patterns.py

        # Save to default logs directory
        python analyze_resume_patterns.py -o resume_patterns.txt

        # Save to specific path
        python analyze_resume_patterns.py -o no_logs/patterns_2025.txt
    """
    if not RESUME_ARCHIVE_PATH.exists():
        typer.echo(f"Error: Directory {RESUME_ARCHIVE_PATH} does not exist", err=True)
        raise typer.Exit(code=1)

    try:
        # Part 1: Keyword frequency analysis
        num_resumes, total_chars, keyword_total_occurrences, keyword_resume_count = (
            analyze_keyword_frequencies(RESUME_ARCHIVE_PATH, KEYWORDS)
        )

        keyword_report = format_analysis_report(
            num_resumes,
            total_chars,
            KEYWORDS,
            keyword_total_occurrences,
            keyword_resume_count,
            RESUME_ARCHIVE_PATH
        )

        # Part 2: Field value enumeration
        # field_values = enumerate_field_values(RESUME_ARCHIVE_PATH)
        field_report = ""

        # Combine reports
        report = keyword_report + "\n\n" + field_report

        if output:
            # If output is not absolute, treat it as relative to LOGS_PATH
            if not output.is_absolute():
                output = LOGS_PATH / output

            # Ensure parent directory exists
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(report)
            typer.echo(f"✓ Analysis report saved to {output}")
        else:
            typer.echo(report)

    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
