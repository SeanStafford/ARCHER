#!/usr/bin/env python3
"""
Apply Configuration Presets to Resume YAML

Applies named configuration presets (spacing, colors, etc.) to resume YAML files.
Presets are composable and can override each other.

Examples:
    # List all available presets
    python scripts/apply_presets.py options

    # List presets in a specific category
    python scripts/apply_presets.py options colors

    # Apply Anthropic colors to existing resume
    python scripts/apply_presets.py apply Res202601_MLEng_Company colors_warm

    # Apply multiple presets (colors + spacing)
    python scripts/apply_presets.py apply Res202601_MLEng_Company spacing_deluxe colors_cool

    # Specify custom output path
    python scripts/apply_presets.py apply Res202601_MLEng_Company colors_warm -o resume_anthropic.yaml
"""

import copy
import difflib
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import typer
from dotenv import load_dotenv
from omegaconf import OmegaConf
from typing_extensions import Annotated

from archer.contexts.templating import apply_presets
from archer.utils.resume_registry import get_resume_file

load_dotenv()
RESUME_PRESETS_PATH = Path(os.getenv("RESUME_PRESETS_PATH"))


def print_diff(original: Dict[str, Any], modified: Dict[str, Any]) -> None:
    """Print unified diff between original and modified YAML."""
    orig_yaml = OmegaConf.to_yaml(original)
    mod_yaml = OmegaConf.to_yaml(modified)
    diff = difflib.unified_diff(
        orig_yaml.splitlines(keepends=True),
        mod_yaml.splitlines(keepends=True),
        fromfile="original",
        tofile="modified",
        lineterm="",
    )
    typer.echo("\nDiff:")
    for line in diff:
        typer.echo(line, nl=False)


app = typer.Typer(
    help="Apply configuration presets to resume YAML files",
    add_completion=False,
)


@app.command("options")
def options_command(
    category: Annotated[
        Optional[str],
        typer.Argument(help="Category to filter (e.g., 'colors', 'spacing')"),
    ] = None,
):
    """
    List available preset options.

    Examples:\n
        $ apply_presets.py options            # All categories and presets

        $ apply_presets.py options colors     # Only color presets
    """
    nested = OmegaConf.to_container(OmegaConf.load(RESUME_PRESETS_PATH), resolve=True)

    if category:
        if category not in nested:
            typer.secho(
                f"Unknown category '{category}'. Available: {', '.join(nested.keys())}",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)
        for name in nested[category]:
            typer.echo(f"{category}_{name}")
    else:
        for cat, presets in nested.items():
            typer.secho(cat, bold=True)
            for name in presets:
                typer.echo(f"  {name}")


@app.command("print")
def print_command(
    preset_name: Annotated[
        str,
        typer.Argument(help="Preset name (e.g., 'colors_warm', 'spacing_tight')"),
    ],
):
    """
    Print the contents of a specific preset.

    Examples:\n
        $ apply_presets.py print colors_warm

        $ apply_presets.py print spacing_tight
    """
    from archer.contexts.templating.config_resolver import load_resume_presets

    presets = load_resume_presets()

    if preset_name not in presets:
        typer.secho(f"Unknown preset '{preset_name}'", fg=typer.colors.RED, err=True)
        typer.echo(f"\nAvailable presets: {', '.join(sorted(presets.keys()))}")
        raise typer.Exit(code=1)

    typer.secho(preset_name, bold=True)
    typer.echo(OmegaConf.to_yaml(OmegaConf.create(presets[preset_name])).rstrip())


@app.command("apply")
def apply_command(
    resume_identifier: Annotated[
        str,
        typer.Argument(help="Resume identifier (e.g., Res202601_Sci_Chief_AIRes_JHAPL)"),
    ],
    presets: Annotated[
        list[str],
        typer.Argument(help="Preset names to apply (e.g., spacing_tight colors_warm)"),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output path (defaults to overwriting input file)",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show diff of changes",
        ),
    ] = False,
):
    """
    Apply configuration presets to a resume YAML file.

    Presets are applied in order, with later presets overriding earlier ones.
    This allows composable combinations like base spacing + override deflens.

    Examples:\n
        # Apply Anthropic colors
        $ apply_presets.py apply Res202601_MLEng_Company colors_warm

        # Apply multiple presets (colors + spacing)
        $ apply_presets.py apply Res202601_MLEng_Company spacing_deluxe colors_cool
    """

    # Detect if a file path was given instead of a resume identifier
    if "/" in resume_identifier or resume_identifier.endswith(".yaml"):
        typer.secho(
            f"Error: Expected a resume identifier, not a file path: '{resume_identifier}'",
            fg=typer.colors.RED,
            err=True,
        )
        typer.echo("  Example: apply_presets.py apply Res202601_MLEng_Company colors_warm")
        raise typer.Exit(code=1)

    # Resolve identifier to YAML path
    try:
        yaml_path = get_resume_file(resume_identifier, file_type="yaml")
    except FileNotFoundError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # Load YAML
    typer.echo(f"Loading: {yaml_path}")
    yaml_data = OmegaConf.to_container(OmegaConf.load(yaml_path), resolve=True)
    original_data = copy.deepcopy(yaml_data) if verbose else None

    # Apply presets
    typer.echo(f"Applying presets: {', '.join(presets)}")
    try:
        modified_data = apply_presets(yaml_data, presets)
    except ValueError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # Show diff if verbose
    if verbose:
        print_diff(original_data, modified_data)

    # Determine output path
    output_path = output if output else yaml_path

    # Save modified YAML
    conf = OmegaConf.create(modified_data)
    OmegaConf.save(conf, output_path)

    # Strip trailing blank lines for consistency
    content = output_path.read_text()
    output_path.write_text(content.rstrip() + "\n")

    typer.secho("✓ Presets applied successfully", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  Output: {output_path}")

    # Show what was modified
    typer.echo("\nApplied presets:")
    for preset_name in presets:
        typer.echo(f"  • {preset_name}")


if __name__ == "__main__":
    # Default to 'apply' command if no known subcommand specified
    # This allows: python apply_presets.py resume.yaml colors_warm
    # instead of:  python apply_presets.py apply resume.yaml colors_warm
    known_commands = {"apply", "options", "print"}
    if len(sys.argv) > 1 and sys.argv[1] not in known_commands and not sys.argv[1].startswith("-"):
        sys.argv.insert(1, "apply")
    app()
