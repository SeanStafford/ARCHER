"""
LaTeX <-> YAML Converter

Main module providing convenience functions for bidirectional conversion
between structured YAML and LaTeX resume format.

This module exports:
- Convenience functions: yaml_to_latex, latex_to_yaml
- Converter classes: YAMLToLaTeXConverter, LaTeXToYAMLConverter (re-exported)
"""

import copy
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from jinja2.exceptions import UndefinedError as JinjaUndefinedError
from omegaconf import OmegaConf

from archer.contexts.templating.exceptions import InvalidYAMLStructureError
from archer.contexts.templating.latex_generator import YAMLToLaTeXConverter
from archer.contexts.templating.latex_parser import LaTeXToYAMLConverter
from archer.contexts.templating.latex_patterns import DocumentRegex, EnvironmentPatterns
from archer.contexts.templating.process_latex_archive import process_file
from archer.utils.latex_parsing_tools import to_latex
from archer.utils.text_processing import get_meaningful_diff

# Field pairs: (LaTeX-formatted field, plaintext field)
# These pairs define which plaintext fields should be copied to LaTeX fields when missing
ENFORCED_PAIRS = [
    ("latex_raw", "plaintext"),
    ("name", "name_plaintext"),
    ("brand", "brand_plaintext"),
    ("professional_profile", "professional_profile_plaintext"),
]
ALL_ENFORCED_FIELDS = [field for pair in ENFORCED_PAIRS for field in pair]


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
            if (
                plaintext_field in original
                and latex_field not in original
                and latex_field in cleaned
            ):
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
    is compatible with the LaTeX generator. Fills missing LaTeX-formatted fields
    from plaintext equivalents, escaping special LaTeX characters in the process.

    Args:
        data: YAML data structure (dict, list, or primitive)
        return_count: If True, return (cleaned_data, count) tuple. If False, return just cleaned_data.

    Returns:
        If return_count=False: Normalized data with LaTeX fields populated
        If return_count=True: Tuple of (normalized_data, num_fields_added)
    """

    # Keep original if we need to count changes
    original_data = copy.deepcopy(data) if return_count else None

    # Perform cleaning
    if isinstance(data, dict):
        # Copy plaintext to LaTeX-formatted fields if LaTeX version is missing
        for latex_field, plaintext_field in ENFORCED_PAIRS:
            if plaintext_field in data and latex_field not in data:
                # Escape special LaTeX characters when copying from plaintext
                plaintext_value = data[plaintext_field]
                if isinstance(plaintext_value, str):
                    data[latex_field] = to_latex(plaintext_value)
                else:
                    # Non-string values (e.g., None, int) pass through unchanged
                    data[latex_field] = plaintext_value

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

    Raises:
        ValueError: If YAML contains only plaintext fields without LaTeX-formatted equivalents
    """
    yaml_data = OmegaConf.load(yaml_path)
    yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

    converter = YAMLToLaTeXConverter()

    # Validate YAML structure and generate LaTeX
    try:
        if "document" not in yaml_dict:
            raise ValueError("YAML must contain 'document' key at root level")

        latex = converter.generate_document(yaml_dict)
    except (KeyError, Exception, JinjaUndefinedError) as e:
        # Check if any enforced field appears in the error message
        is_enforced_field_error = any(f"'{field}'" in str(e) for field in ALL_ENFORCED_FIELDS)

        if is_enforced_field_error:
            # This is a plaintext → latex_raw issue - suggest clean_yaml()
            raise InvalidYAMLStructureError(
                "This YAML file appears to be missing some required fields.\n\n"
                "Try cleaning it:\n"
                "    from archer.contexts.templating.converter import clean_yaml\n"
                "    yaml_dict = clean_yaml(yaml_dict)\n"
                "    yaml_to_latex(yaml_path, output_path)\n\n"
                "Or use the CLI:\n"
                "    python scripts/convert_template.py clean <yaml_file>"
            ) from e
        else:
            # Generic structural error
            raise InvalidYAMLStructureError(
                "The YAML file is missing required structural fields or has incorrect formatting."
            ) from e

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
    if re.search(DocumentRegex.BEGIN_DOCUMENT, latex_str) and re.search(
        DocumentRegex.END_DOCUMENT, latex_str
    ):
        # Full document
        yaml_dict = converter.parse_document(latex_str)
    elif re.search(EnvironmentPatterns.BEGIN_ITEMIZE_ACADEMIC, latex_str):
        # Single work experience subsection (for testing)
        result = converter.parse_work_experience(latex_str)
        yaml_dict = {"subsection": result}
    else:
        raise ValueError(
            "LaTeX must be either a full document or a single itemizeAcademic subsection"
        )

    if output_path:
        conf = OmegaConf.create(yaml_dict)
        OmegaConf.save(conf, output_path)

        # Strip trailing blank lines for consistency
        content = output_path.read_text()
        output_path.write_text(content.rstrip() + "\n")

    return yaml_dict


def compare_yaml_structured(yaml1_path: Path, yaml2_path: Path) -> tuple[list[str], int]:
    """
    Compare two YAML files using structured comparison.

    Uses OmegaConf to load both YAMLs and compare as dictionaries,
    ignoring formatting and key order differences.

    Args:
        yaml1_path: Path to first YAML file
        yaml2_path: Path to second YAML file

    Returns:
        Tuple of (diff_lines, num_differences)
    """
    yaml1 = OmegaConf.load(yaml1_path)
    yaml2 = OmegaConf.load(yaml2_path)

    dict1 = OmegaConf.to_container(yaml1)
    dict2 = OmegaConf.to_container(yaml2)

    if dict1 == dict2:
        return [], 0

    diff_lines = [
        "YAML structures differ",
        f"File 1: {yaml1_path.name}",
        f"File 2: {yaml2_path.name}",
        "Run diff on the files for details",
    ]

    return diff_lines, 1


def validate_roundtrip_conversion(
    tex_file: Path, work_dir: Path, max_latex_diffs: int, max_yaml_diffs: int
) -> Dict:
    """
    Validate LaTeX ↔ YAML roundtrip conversion fidelity.

    Performs dual roundtrip testing:
    - LaTeX roundtrip: LaTeX → YAML → LaTeX (tests parser + generator)
    - YAML roundtrip: Compare parsed YAML vs re-parsed YAML (tests stability)

    Args:
        tex_file: Path to LaTeX file to test
        work_dir: Directory for intermediate files
        max_latex_diffs: Maximum allowed LaTeX differences
        max_yaml_diffs: Maximum allowed YAML differences

    Returns:
        Dict with validation results: {
            'file': filename,
            'latex_roundtrip': {'success': bool, 'num_diffs': int},
            'yaml_roundtrip': {'success': bool, 'num_diffs': int},
            'validation_passed': bool,
            'error': str or None,
            'time_ms': float
        }
    """

    start_time = datetime.now()
    result = {
        "file": tex_file.name,
        "latex_roundtrip": {"success": False, "num_diffs": None},
        "yaml_roundtrip": {"success": False, "num_diffs": None},
        "validation_passed": False,
        "error": None,
        "time_ms": 0.0,
    }

    try:
        file_stem = tex_file.stem
        work_dir.mkdir(exist_ok=True, parents=True)

        # Step 1: Normalize input
        normalized_input = work_dir / f"{file_stem}_normalized.tex"
        success, _ = process_file(
            tex_file, normalized_input, comment_types=set(), normalize=True, dry_run=False
        )
        if not success:
            result["error"] = "Failed to normalize input"
            return result

        # Step 2: Parse LaTeX → YAML
        parsed_yaml = work_dir / f"{file_stem}_parsed.yaml"
        try:
            latex_to_yaml(normalized_input, parsed_yaml)
        except Exception as e:
            result["error"] = f"Parse error: {str(e)}"
            return result

        # Step 3: Generate YAML → LaTeX
        generated_tex = work_dir / f"{file_stem}_generated.tex"
        try:
            yaml_to_latex(parsed_yaml, generated_tex)
        except Exception as e:
            result["error"] = f"Generation error: {str(e)}"
            return result

        # Step 4: Normalize generated output
        normalized_output = work_dir / f"{file_stem}_generated_normalized.tex"
        success, _ = process_file(
            generated_tex, normalized_output, comment_types=set(), normalize=True, dry_run=False
        )
        if not success:
            result["error"] = "Failed to normalize output"
            return result

        # Step 5: LaTeX Roundtrip Comparison
        latex_diff_lines, latex_num_diffs = get_meaningful_diff(normalized_input, normalized_output)

        if latex_num_diffs > 0:
            latex_diff_file = work_dir / "latex_roundtrip.diff"
            latex_diff_file.write_text("\n".join(latex_diff_lines), encoding="utf-8")

        result["latex_roundtrip"] = {
            "success": (latex_num_diffs <= max_latex_diffs),
            "num_diffs": latex_num_diffs,
        }

        # Step 6: Re-parse generated LaTeX for YAML roundtrip
        reparsed_yaml = work_dir / f"{file_stem}_reparsed.yaml"
        try:
            latex_to_yaml(normalized_output, reparsed_yaml)
        except Exception as e:
            result["error"] = f"Re-parse error: {str(e)}"
            return result

        # Step 7: YAML Roundtrip Comparison
        yaml_diff_lines, yaml_num_diffs = compare_yaml_structured(parsed_yaml, reparsed_yaml)

        if yaml_num_diffs > 0:
            yaml_diff_file = work_dir / "yaml_roundtrip.diff"
            yaml_diff_file.write_text("\n".join(yaml_diff_lines), encoding="utf-8")

        result["yaml_roundtrip"] = {
            "success": (yaml_num_diffs <= max_yaml_diffs),
            "num_diffs": yaml_num_diffs,
        }

        # Determine if validation passed
        result["validation_passed"] = (
            result["latex_roundtrip"]["success"] and result["yaml_roundtrip"]["success"]
        )

    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"

    finally:
        end_time = datetime.now()
        result["time_ms"] = (end_time - start_time).total_seconds() * 1000

    return result
