"""
LaTeX <-> YAML Converter

Main module providing convenience functions for bidirectional conversion
between structured YAML and LaTeX resume format.

This module exports:
- Convenience functions: yaml_to_latex, latex_to_yaml
- Converter classes: YAMLToLaTeXConverter, LaTeXToYAMLConverter (re-exported)
"""

import re
from pathlib import Path
from typing import Any, Dict

from omegaconf import OmegaConf

from archer.contexts.templating.latex_patterns import DocumentRegex, EnvironmentPatterns
from archer.contexts.templating.latex_generator import YAMLToLaTeXConverter
from archer.contexts.templating.latex_parser import LaTeXToYAMLConverter


# Field pairs: (LaTeX-formatted field, plaintext field)
# These pairs define which plaintext fields should be copied to LaTeX fields when missing
ENFORCED_PAIRS = [
    ('latex_raw', 'plaintext'),
    ('name', 'name_plaintext'),
    ('brand', 'brand_plaintext'),
    ('professional_profile', 'professional_profile_plaintext'),
]


def count_new_fields(original: Any, cleaned: Any, field_pairs: list) -> int:
    """
    Count how many fields were added during cleaning.

    Args:
        original: Original data structure before cleaning
        cleaned: Cleaned data structure after normalization
        field_pairs: List of (latex_field, plaintext_field) tuples

    Returns:
        Number of new fields added
    """
    count = 0
    if isinstance(original, dict) and isinstance(cleaned, dict):
        for latex_field, plaintext_field in field_pairs:
            if plaintext_field in original and latex_field not in original and latex_field in cleaned:
                count += 1
        for key in original:
            if key in cleaned:
                count += count_new_fields(original[key], cleaned[key], field_pairs)
    elif isinstance(original, list) and isinstance(cleaned, list):
        for orig_item, clean_item in zip(original, cleaned):
            count += count_new_fields(orig_item, clean_item, field_pairs)
    return count


def clean_yaml(data: Any, return_count: bool = False) -> Any | tuple[Any, int]:
    """
    Normalize YAML resume data for LaTeX generation.

    Applies normalization rules defined in ENFORCED_PAIRS to ensure YAML structure
    is compatible with the LaTeX generator. Currently fills missing LaTeX-formatted
    fields from plaintext equivalents.

    Args:
        data: YAML data structure (dict, list, or primitive)
        return_count: If True, return (cleaned_data, count) tuple. If False, return just cleaned_data.

    Returns:
        If return_count=False: Normalized data with LaTeX fields populated
        If return_count=True: Tuple of (normalized_data, num_fields_added)
    """
    import copy

    # Keep original if we need to count changes
    original_data = copy.deepcopy(data) if return_count else None

    # Perform cleaning
    if isinstance(data, dict):
        # Copy plaintext to LaTeX-formatted fields if LaTeX version is missing
        for latex_field, plaintext_field in ENFORCED_PAIRS:
            if plaintext_field in data and latex_field not in data:
                data[latex_field] = data[plaintext_field]

        # Recursively clean nested structures
        for key, value in data.items():
            data[key] = clean_yaml(value, return_count=False)  # Don't count recursively

    elif isinstance(data, list):
        # Clean each item in list
        data = [clean_yaml(item, return_count=False) for item in data]

    # Return with count if requested
    if return_count:
        count = count_new_fields(original_data, data, ENFORCED_PAIRS)
        return data, count

    # Primitives (str, int, bool, None) pass through unchanged
    return data


def yaml_to_latex(yaml_path: Path, output_path: Path = None) -> str:
    """
    Convert YAML resume structure to LaTeX.

    Args:
        yaml_path: Path to YAML file
        output_path: Optional path to write LaTeX output

    Returns:
        Generated LaTeX string
    """
    yaml_data = OmegaConf.load(yaml_path)
    yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

    converter = YAMLToLaTeXConverter()

    # Handle different YAML structures
    if "document" in yaml_dict:
        # Full document
        latex = converter.generate_document(yaml_dict)
    elif "subsection" in yaml_dict:
        # Single subsection (for testing)
        latex = converter.convert_work_experience(yaml_dict["subsection"])
    else:
        raise ValueError("YAML must contain either 'document' or 'subsection' key")

    if output_path:
        output_path.write_text(latex, encoding="utf-8")

    return latex


def latex_to_yaml(latex_path: Path, output_path: Path = None) -> Dict[str, Any]:
    """
    Convert LaTeX resume to YAML structure.

    Args:
        latex_path: Path to LaTeX file
        output_path: Optional path to write YAML output

    Returns:
        Parsed YAML structure as dict
    """
    latex_str = latex_path.read_text(encoding="utf-8")

    converter = LaTeXToYAMLConverter()

    # Try to parse as full document first
    if re.search(DocumentRegex.BEGIN_DOCUMENT, latex_str) and re.search(DocumentRegex.END_DOCUMENT, latex_str):
        # Full document
        yaml_dict = converter.parse_document(latex_str)
    elif re.search(EnvironmentPatterns.BEGIN_ITEMIZE_ACADEMIC, latex_str):
        # Single work experience subsection (for testing)
        result = converter.parse_work_experience(latex_str)
        yaml_dict = {"subsection": result}
    else:
        raise ValueError("LaTeX must be either a full document or a single itemizeAcademic subsection")

    if output_path:
        conf = OmegaConf.create(yaml_dict)
        OmegaConf.save(conf, output_path)

        # Strip trailing blank lines for consistency
        content = output_path.read_text()
        output_path.write_text(content.rstrip() + '\n')

    return yaml_dict
