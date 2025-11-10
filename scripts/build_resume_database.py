#!/usr/bin/env python3
"""
Build persistent SQLite database from resume archive.

Extracts all items (skills, bullets) from resume YAMLs and stores in a
queryable database for use by the targeting context.

Usage:
    python scripts/build_resume_database.py
"""

import os
from pathlib import Path

import typer
from dotenv import load_dotenv

from archer.contexts.templating import ResumeDocumentArchive, ResumeDatabase

# Load environment
load_dotenv()
RESUME_ARCHIVE_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH"))

# Database output path
DB_DIR = RESUME_ARCHIVE_PATH / "database"
DB_PATH = DB_DIR / "resumes.db"

app = typer.Typer(add_completion=False)


@app.command()
def main(
    output: Path = typer.Option(
        DB_PATH,
        "--output",
        "-o",
        help="Output database path"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed statistics"
    ),
):
    """Build database from resume archive."""
    typer.echo(f"Loading resume archive from: {RESUME_ARCHIVE_PATH}")
    archive_manager = ResumeDocumentArchive(RESUME_ARCHIVE_PATH)
    documents = archive_manager.load(mode="available", format_mode="plaintext")
    typer.echo(f"  Loaded {len(documents)} resumes\n")

    typer.echo(f"Building database at: {output}")
    db = ResumeDatabase.from_documents(documents, output)
    typer.echo("  Database created\n")

    # Query statistics
    total_items = db.query("SELECT COUNT(*) as count FROM items")[0]["count"]
    total_skills = len(db.get_all_skills())
    total_bullets = len(db.get_all_bullets())

    typer.echo("Database Statistics:")
    typer.echo(f"  Total items: {total_items}")
    typer.echo(f"  Skills: {total_skills}")
    typer.echo(f"  Bullets: {total_bullets}")

    if verbose:
        # Show sample queries
        typer.echo("\nSample queries:")

        typer.echo("\n  Work experience bullets:")
        work_bullets = db.get_items_by_section_type("work_history")
        typer.echo(f"    Found {len(work_bullets)} bullets")
        if work_bullets:
            sample = work_bullets[0]
            typer.echo(f"    Sample: {sample['item_text'][:80]}...")
            typer.echo(f"      Company: {sample['company']}")
            typer.echo(f"      Type: {sample['subsection_type']}")

        typer.echo("\n  Skills:")
        skills = db.get_all_skills()
        typer.echo(f"    Found {len(skills)} skills")
        if skills:
            typer.echo(f"    First 5: {[s['item_text'] for s in skills[:5]]}")

    typer.echo("\n✓ Database ready for use by targeting context")


if __name__ == "__main__":
    app()
