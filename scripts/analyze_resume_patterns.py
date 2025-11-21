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
    analyze_section_patterns,
    enumerate_field_values,
    enumerate_section_values,
    format_analysis_report,
    format_field_enumeration_report,
    format_section_enumeration_report,
    format_section_pattern_report,
)

# Load environment variables
load_dotenv()
RESUME_ARCHIVE_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH"))
LOGS_PATH = Path(os.getenv("LOGS_PATH"))

app = typer.Typer(
    add_completion=False,
)

SECTION_CATEGORIES = {
    "Left Column (Professional)": [
        "Core Skills",
        "AI \& Machine Learning|Machine Learning \& AI",
        "[^ ]Machine Learning[^ ]",
        "Hardware",
        "Languages|Programming Languages",
        "Software Tools",
        ".*Tool.*",
        "HPC Tools",
        "Infrastructure",
        "Data",
    ],

    "Personality": [
        "Marketable Monikers",
        "Proficiency Pseudonyms",
        "Alias Array",
        "Alliterative Aliases",
        "Certifiable Pseudonyms",
        "Two Truths and a Lie|2 Truths and a Lie",
        "Passions",
    ],

    "Project Section Titles": [
        "Projects I'm Proud Of",
        "Timeline of.*",
        ".*Project.*",
        "Highlighted.*Projects",
        ".*Selected.*",
        ".*Portfolio.*",
        "LLM Research Portfolio",
        "LLM Projects",
        "Other Projects",
    ],
}


FIELD_CATEGORIES = {
    "Professional Profile": [
        "6+ years",
        "6 years",
        "since 2017",
        "since 2019",
    ],

    "Core Skills": [
        "Machine Learning",
        "Physics"
    ],

    "brand": [
        "Physicist",
        "Computational Physicist",
        "HPC Physicist",
        "Machine Learning Engineer",
        "ML Engineer",
        "AI|Artificial Intelligence",
        "ML|Machine Learning",
        "Data",
        "Software",
        "Quantum",
        "System",
        "Test",
        "Infrastructure",
        "Scientist",
        "Engineer",
        "Researcher",
        "Specialist"
    ]
}

# Keyword categories to analyze
KEYWORDS = {


    "Environment Usage": [
        "itemizeAcademic",
        "itemizeAProject",
        "itemizeKeyProject",
        "itemizeProjMain",
        "itemizeProjSecond",
        "itemizeSecond",
        "itemizeLL",
    ],

    "Professional Profile Themes": [
        "scientific rigor",
        "rigor",
        "scalable",
        "scaling",
        "prototype to production",
        "infrastructure",
        "distributed",
        "high-performance",
        "fast",
        "rapid",
    ],

    "Technical Domains": [
        "LLM",
        "Large Language Model",
        "HPC",
        "High Performance",
        "distributed computing",
        "distributed systems",
        "quantum",
        "ML infrastructure",
        "data pipeline",
    ],

    "Job Family Indicators": [
        "AI Engineer",
        "ML Engineer",
        "Machine Learning Engineer",
        "Data Scientist",
        "Infrastructure Engineer",
        "Researcher",
        "Research Scientist",
        "Software Engineer",
    ],

    "Physicist Identity Variations": [
        "| Physicist",
        "| Computational Physicist",
        "| HPC Physicist",
        "Physicist with",
        "Physicist building",
        "Physicist who",
    ],

    "Company Targeting Patterns": [
        "BoozGreen",
        "NorthropGrumanBlue",
        "AnthropicGeistOrange",
        "ClaudeOrange",
        "JHAPLblue",
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
        ),
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
        field_values = enumerate_field_values(RESUME_ARCHIVE_PATH)
        field_report = format_field_enumeration_report(
            field_values,
            num_resumes,
            RESUME_ARCHIVE_PATH
        )

        # Part 3: Section enumeration
        section_counts = enumerate_section_values(RESUME_ARCHIVE_PATH)
        section_report = format_section_enumeration_report(
            section_counts,
            num_resumes,
            RESUME_ARCHIVE_PATH
        )

        # Part 4: Section pattern matching
        (
            section_pattern_num_resumes,
            section_pattern_occurrences,
            section_pattern_counts,
        ) = analyze_section_patterns(RESUME_ARCHIVE_PATH, SECTION_CATEGORIES, is_regex=True)

        section_pattern_report = format_section_pattern_report(
            section_pattern_num_resumes,
            SECTION_CATEGORIES,
            section_pattern_occurrences,
            section_pattern_counts,
            RESUME_ARCHIVE_PATH,
        )

        # Combine reports
        report = (
            keyword_report
            + "\n\n"
            + field_report
            + "\n\n"
            + section_report
            + "\n\n"
            + section_pattern_report
        )

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
