#!/usr/bin/env python3
"""
Validate job file parsing before notebook creation.

Usage:
    python scripts/validate_job.py FactoryInspector_MomCorp_5
    python scripts/validate_job.py FactoryInspector_MomCorp_5 --tree
"""

import os
from pathlib import Path

import typer
from dotenv import load_dotenv

from archer.contexts.intake.job_data_structure import JobListing

load_dotenv()

app = typer.Typer(help="Validate job file parsing.")


@app.command()
def main(
    job_identifier: str = typer.Argument(
        ..., help="Job identifier (e.g., MLEng_Sen_AcmeCorp_12345)"
    ),
    tree: bool = typer.Option(False, "--tree", help="Use markdown tree parsing"),
):
    """Validate job parsing and display extracted structure."""
    job_identifier = job_identifier.removesuffix(".md")

    try:
        job = JobListing.from_identifier(job_identifier, use_markdown_tree=tree)
    except ValueError:
        typer.echo(f"ERROR: Job not found: {job_identifier}", err=True)
        raise typer.Exit(1)

    project_root = Path(os.getenv("PROJECT_ROOT"))
    jobs_path = Path(os.getenv("JOBS_PATH"))
    job_file = jobs_path / f"{job_identifier}.md"
    relative_path = job_file.relative_to(project_root)

    typer.echo(f"Loading {job_identifier}")
    typer.echo(f"Path: {relative_path}")
    if tree:
        typer.echo("(Using MarkdownTree parser)")

    # Metadata
    typer.echo("\n=== Metadata ===")
    typer.echo(f"  job_identifier: {job.job_identifier}")
    typer.echo(f"  title: {job.title}")
    for key, value in job.metadata.items():
        typer.echo(f"  {key}: {value}")

    # Sections
    typer.echo(f"\n=== Sections ({len(job.sections)}) ===")
    for name, content in job.sections.items():
        lines = content.count("\n") + 1
        chars = len(content)
        typer.echo(f"  {name}: {lines} lines, {chars} chars")

    # Section categorization
    all_sections = list(job.sections.keys())
    boilerplate = list(job._boilerplate_sections)
    req_names = job.required_qualifications_sections or []
    pref_names = job.preferred_qualifications_sections or []
    other = [
        s
        for s in all_sections
        if s not in boilerplate and s not in req_names and s not in pref_names
    ]

    typer.echo("\n=== Qualification Sections ===")

    req_lines = sum(job.sections.get(s, "").count("\n") + 1 for s in req_names)
    pref_lines = sum(job.sections.get(s, "").count("\n") + 1 for s in pref_names)

    req_display = f"{req_names} ({req_lines} lines)" if req_names else "(none detected)"
    pref_display = f"{pref_names} ({pref_lines} lines)" if pref_names else "(none detected)"
    typer.echo(f"  Required: {req_display}")
    typer.echo(f"  Preferred: {pref_display}")

    typer.echo("\n=== Section Categorization ===")
    typer.echo(f"Boilerplate sections ({len(boilerplate)}):")
    typer.echo(f"  {', '.join(boilerplate)}" if boilerplate else "  None")

    typer.echo(f"\nOther scorable sections ({len(other)}):")
    typer.echo(f"  {', '.join(other)}" if other else "  None")

    # Warnings
    warnings = []
    if not req_names:
        warnings.append("No required qualifications section detected")
    if not pref_names:
        warnings.append("No preferred qualifications section detected")
    if len(job.sections) < 3:
        warnings.append(f"Only {len(job.sections)} sections parsed (expected more)")

    if warnings:
        typer.echo("\n=== Warnings ===")
        for w in warnings:
            typer.echo(f"  ! {w}")

    typer.secho("\n✓ Parsing successful", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
