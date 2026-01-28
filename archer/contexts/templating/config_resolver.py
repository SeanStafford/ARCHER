"""
Config Preset Resolution for Resume Generation

Applies named configuration presets to resume YAML metadata. Presets are composable
and can override each other, allowing flexible combination of spacing, colors, etc.

Examples:
    # Apply multiple presets (later overrides earlier)
    >>> apply_presets(yaml_data, ["spacing_tight", "colors_warm"])

    # Mix base preset with override
    >>> apply_presets(yaml_data, ["spacing_deluxe", "spacing_bigbottom", "colors_cool"])
"""

import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from omegaconf import OmegaConf

load_dotenv()
RESUME_PRESETS_PATH = Path(os.getenv("RESUME_PRESETS_PATH"))


def load_resume_presets(config_path: Path = None) -> Dict[str, Any]:
    """
    Load resume_presets.yaml config file and flatten to single-level dict.

    Collapses nested structure: spacing.tight -> spacing_tight

    Args:
        config_path: Optional path to config file (defaults to RESUME_PRESETS_PATH env variable)

    Returns:
        Flattened dict mapping preset names to configs
        Example: {"spacing_tight": {...}, "colors_warm": {...}}
    """
    if config_path is None:
        config_path = RESUME_PRESETS_PATH

    nested = OmegaConf.to_container(OmegaConf.load(config_path), resolve=True)

    # Flatten: category.name -> category_name
    flattened = {}
    for category, presets in nested.items():
        for name, config in presets.items():
            flattened[f"{category}_{name}"] = config

    return flattened


def apply_presets(
    yaml_data: Dict[str, Any],
    preset_names: List[str],
    config_path: Path = None,
) -> Dict[str, Any]:
    """
    Apply named configuration presets to resume YAML metadata.

    Presets are applied in order, with later presets overriding earlier ones.
    Each preset's keys must match the metadata structure exactly.

    Args:
        yaml_data: Resume YAML data (must have document.metadata)
        preset_names: List of preset names to apply (e.g., ["spacing_tight", "colors_warm"])
        config_path: Optional path to resume_presets.yaml (defaults to RESUME_PRESETS_PATH)

    Returns:
        Modified YAML data with presets applied

    Raises:
        ValueError: If YAML missing document.metadata or preset not found

    Examples:
        >>> # Apply tight spacing and Anthropic colors
        >>> yaml_data = apply_presets(yaml_data, ["spacing_tight", "colors_warm"])

        >>> # Mix base preset with override
        >>> yaml_data = apply_presets(yaml_data, ["spacing_deluxe", "spacing_bigbottom"])
    """
    # Validate YAML structure
    if "document" not in yaml_data:
        raise ValueError("YAML must contain 'document' key at root level")
    if "metadata" not in yaml_data["document"]:
        raise ValueError("YAML must contain 'document.metadata' key")

    # Load presets config
    presets_dict = load_resume_presets(config_path)

    # Apply each preset in order
    metadata = yaml_data["document"]["metadata"]

    for preset_name in preset_names:
        if preset_name not in presets_dict:
            available = list(presets_dict.keys())
            raise ValueError(f"Preset '{preset_name}' not found. Available presets: {available}")

        preset_config = presets_dict[preset_name]

        # Merge preset into metadata (OmegaConf-style update)
        # Later presets override earlier ones
        metadata.update(preset_config)

    return yaml_data
