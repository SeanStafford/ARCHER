"""
YAML Normalization and Canonicalization

Provides Step 2 of the minimal resume pipeline: normalization of YAML data
to canonical form ready for LaTeX generation.

Step 2: Normalizer (this module)
- Input: ANY partial YAML (from builder, historical, or manual)
- Output: Complete, canonical YAML ready for LaTeX generation
- Operations:
  1. Create plaintext ↔ latex_raw pairs (whichever is missing)
  2. Add missing defaults (colors, setlengths, deflens, hlcolor, etc.)
  3. Infer type-specific metadata (spacing_after, subtitle)
  4. Add structural completeness (textblock_literal, decorations)
  5. Sort keys alphabetically for consistent ordering

This module makes ANY partial YAML complete and canonical, enabling:
- Minimal builder output → Full YAML
- Historical resumes → Normalized YAML
- Manual YAMLs → Complete YAML
"""

from typing import Any, Dict

from archer.contexts.templating.defaults import SECTION_SPACING, get_default_metadata
from archer.utils.latex_parsing_tools import to_latex, to_plaintext


def _sort_dict_keys(data: Any) -> Any:
    """Recursively sort dictionary keys alphabetically for consistent ordering."""
    if isinstance(data, dict):
        return {k: _sort_dict_keys(v) for k, v in sorted(data.items())}
    elif isinstance(data, list):
        return [_sort_dict_keys(item) for item in data]
    return data


# Field pairs: (LaTeX-formatted field, plaintext field)
# These pairs define which plaintext fields should be copied to LaTeX fields when missing
ENFORCED_PAIRS = [
    ("latex_raw", "plaintext"),
    ("name", "name_plaintext"),
    ("brand", "brand_plaintext"),
    ("professional_profile", "professional_profile_plaintext"),
]
ALL_ENFORCED_FIELDS = [field for pair in ENFORCED_PAIRS for field in pair]


def _add_document_defaults(data: Dict[str, Any]) -> None:
    """
    Add missing default values to document metadata in-place.

    Uses get_default_metadata() to get complete default structure,
    then adds only missing fields to preserve existing values.

    Args:
        data: Full YAML structure with document.metadata
    """
    if "document" not in data or "metadata" not in data["document"]:
        return

    metadata = data["document"]["metadata"]
    defaults = get_default_metadata()

    # Add each default field if missing
    for key, default_value in defaults.items():
        if key not in metadata:
            # For nested dicts, copy to avoid shared references
            if isinstance(default_value, dict):
                metadata[key] = default_value.copy()
            else:
                metadata[key] = default_value


def _add_structural_completeness(data: Dict[str, Any]) -> None:
    """
    Add missing structural fields to pages in-place.

    Args:
        data: Full YAML structure with document.pages
    """
    for page in data["document"]["pages"]:
        # Add textblock_literal if missing
        if "textblock_literal" not in page["regions"]:
            page["regions"]["textblock_literal"] = None

        # Add decorations if missing
        if "decorations" not in page["regions"]:
            page["regions"]["decorations"] = None


def _add_metadata_completeness(data: Any) -> None:
    """
    Add missing type-specific metadata fields in-place.

    Adds:
    - spacing_after based on component type
    - subtitle (empty string) for work_experience if missing

    Args:
        data: YAML data structure (dict, list, or primitive)
    """
    if isinstance(data, dict):
        # Check if this is a typed component
        if "type" in data and "metadata" in data:
            # components types are specified in template/types/
            component_type = data["type"]

            # Add spacing_after if missing
            if "spacing_after" not in data["metadata"]:
                data["metadata"]["spacing_after"] = SECTION_SPACING.get(component_type, "")

            # Add subtitle for work_experience if missing
            if component_type == "work_experience" and "subtitle" not in data["metadata"]:
                data["metadata"]["subtitle"] = ""

        # Recursively process nested structures
        for value in data.values():
            _add_metadata_completeness(value)

    elif isinstance(data, list):
        for item in data:
            _add_metadata_completeness(item)


def clean_yaml(data: Any, top_level: bool = True) -> Any:
    """
    Minimal normalization for comparison and field pair enforcement.

    Operations performed:
    1. Bidirectional field conversion (plaintext ↔ latex_raw)
    2. Create *_plaintext fields from LaTeX equivalents
    3. Sort keys alphabetically for canonical ordering

    Does NOT add defaults, type inference, or structural completeness.
    Use normalize_yaml() for full normalization needed for LaTeX generation.

    Args:
        data: YAML data structure (dict, list, or primitive)
        top_level: If True, apply final key sorting (only at root call)

    Returns:
        Cleaned data with field pairs normalized and keys sorted
    """
    if isinstance(data, dict):
        # Handle bidirectional field conversion
        for latex_field, plaintext_field in ENFORCED_PAIRS:
            # Direction 1: plaintext → latex_raw (escaping)
            if plaintext_field in data and latex_field not in data:
                plaintext_value = data[plaintext_field]
                if isinstance(plaintext_value, str):
                    data[latex_field] = to_latex(plaintext_value)
                else:
                    # Non-string values (e.g., None, int) pass through unchanged
                    data[latex_field] = plaintext_value

            # Direction 2: latex_raw → plaintext (unescaping)
            elif latex_field in data and plaintext_field not in data:
                latex_value = data[latex_field]
                if isinstance(latex_value, str):
                    data[plaintext_field] = to_plaintext(latex_value)
                else:
                    # Non-string values (e.g., None, int) pass through unchanged
                    data[plaintext_field] = latex_value

        # Recursively clean nested structures
        for key, value in data.items():
            data[key] = clean_yaml(value, top_level=False)

    elif isinstance(data, list):
        data = [clean_yaml(item, top_level=False) for item in data]

    # Sort keys at top level only (once at the end)
    if top_level:
        data = _sort_dict_keys(data)

    # Primitives (str, int, bool, None) pass through unchanged
    return data


def count_new_fields(original: Any, cleaned: Any, field_pairs: list) -> int:
    """
    Recursively count how many fields were added during cleaning.

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


def normalize_yaml(data: Any) -> Any:
    """
    Full normalization for LaTeX generation.

    Applies comprehensive normalization rules to ensure YAML structure is complete
    and ready for LaTeX compilation. This is Step 2 of the minimal resume pipeline.

    Operations performed:
    1. Add missing defaults (colors, setlengths, deflens, hlcolor, etc.)
    2. Add structural completeness (textblock_literal, decorations)
    3. Add type-specific metadata (spacing_after, subtitle)
    4. Clean YAML via clean_yaml():
       a. Bidirectional field conversion (plaintext ↔ latex_raw)
       b. Sort keys alphabetically for canonical ordering

    Opinionated - no parameters. Always produces complete YAML ready for compilation.

    Args:
        data: ARCHER YAML document structure with "document" key

    Returns:
        Normalized data ready for LaTeX generation
    """
    _add_document_defaults(data)
    _add_structural_completeness(data)
    _add_metadata_completeness(data)
    return clean_yaml(data)
