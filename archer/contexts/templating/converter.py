"""
LaTeX <-> YAML Converter

Main module providing convenience functions for bidirectional conversion
between structured YAML and LaTeX resume format.

This module exports:
- Convenience functions: yaml_to_latex, latex_to_yaml
- Orchestration functions: parse_resume, generate_resume (with registry tracking)
- Converter classes: YAMLToLaTeXConverter, LaTeXToYAMLConverter (re-exported)
"""

import copy
import os
import re
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from dotenv import load_dotenv
from jinja2.exceptions import UndefinedError as JinjaUndefinedError
from omegaconf import OmegaConf

from archer.contexts.templating.exceptions import InvalidYAMLStructureError
from archer.contexts.templating.latex_generator import YAMLToLaTeXConverter
from archer.contexts.templating.latex_parser import LaTeXToYAMLConverter
from archer.contexts.templating.latex_patterns import DocumentRegex, EnvironmentPatterns
from archer.contexts.templating.logger import (
    _log_debug,
    log_conversion_result,
    log_conversion_start,
    setup_templating_logger,
)
from archer.contexts.templating.normalizer import process_file
from archer.utils.latex_parsing_tools import to_latex
from archer.utils.resume_registry import (
    get_resume_file,
    get_resume_status,
    resume_is_registered,
    update_resume_status,
)
from archer.utils.text_processing import get_meaningful_diff
from archer.utils.timestamp import now

load_dotenv()
LOGS_PATH = Path(os.getenv("LOGS_PATH", "outs/logs"))

# Field pairs: (LaTeX-formatted field, plaintext field)
# These pairs define which plaintext fields should be copied to LaTeX fields when missing
ENFORCED_PAIRS = [
    ("latex_raw", "plaintext"),
    ("name", "name_plaintext"),
    ("brand", "brand_plaintext"),
    ("professional_profile", "professional_profile_plaintext"),
]
ALL_ENFORCED_FIELDS = [field for pair in ENFORCED_PAIRS for field in pair]


# Result dataclasses for orchestration functions


@dataclass
class ConversionResult:
    """Result from parse_resume() or generate_resume() orchestration function."""

    success: bool
    input_path: Optional[Path] = None
    output_path: Optional[Path] = None
    error: Optional[str] = None
    time_s: float = 0.0
    log_dir: Optional[Path] = None
    # Validation results
    yaml_diffs: Optional[int] = None
    latex_diffs: Optional[int] = None


@dataclass
class ConversionConfig:
    """Direction-specific configuration for conversion orchestration."""

    phase_name: str
    status_in_progress: str
    status_success: str
    status_failure: str
    output_extension: str
    intermediate_suffix: str
    convert_fn: Callable[[Path, Path], None]


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
    input_file: Path, work_dir: Path, max_latex_diffs: int, max_yaml_diffs: int
) -> Dict:
    """
    Validate roundtrip conversion fidelity (routing function).

    Automatically detects input type and routes to appropriate validation:
    - .tex files: LaTeX → YAML → LaTeX (for parsing validation)
    - .yaml files: YAML → LaTeX → YAML (for generation validation)

    Args:
        input_file: Path to input file (.tex or .yaml)
        work_dir: Directory for intermediate files
        max_latex_diffs: Maximum allowed LaTeX differences
        max_yaml_diffs: Maximum allowed YAML differences

    Returns:
        Dict with validation results (same structure for both directions)
    """
    suffix = input_file.suffix.lower()

    if suffix == ".tex":
        return _validate_roundtrip_from_tex(input_file, work_dir, max_latex_diffs, max_yaml_diffs)
    elif suffix == ".yaml":
        return _validate_roundtrip_from_yaml(input_file, work_dir, max_latex_diffs, max_yaml_diffs)
    else:
        return {
            "file": input_file.name,
            "latex_roundtrip": {"success": False, "num_diffs": None},
            "yaml_roundtrip": {"success": False, "num_diffs": None},
            "validation_passed": False,
            "error": f"Unsupported file type: {suffix}. Must be .tex or .yaml",
            "time_ms": 0.0,
        }


def _validate_roundtrip_from_tex(
    tex_file: Path, work_dir: Path, max_latex_diffs: int, max_yaml_diffs: int
) -> Dict:
    """
    Validate LaTeX → YAML → LaTeX roundtrip conversion.

    For parsing validation: ensures LaTeX survives the roundtrip.
    Historical resumes are the source of truth.

    Steps:
    1. Normalize input LaTeX
    2. Parse LaTeX → YAML
    3. Generate YAML → LaTeX
    4. Normalize generated LaTeX
    5. Compare LaTeX (input vs generated)
    6. Re-parse generated LaTeX → YAML
    7. Compare YAML (parsed vs re-parsed)
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


def _validate_roundtrip_from_yaml(
    yaml_file: Path, work_dir: Path, max_latex_diffs: int, max_yaml_diffs: int
) -> Dict:
    """
    Validate YAML → LaTeX → YAML roundtrip conversion.

    For generation validation: ensures YAML survives the roundtrip.
    Structured YAML data is the source of truth.

    Steps:
    1. Generate YAML → LaTeX
    2. Normalize generated LaTeX
    3. Parse LaTeX → YAML
    4. Compare YAML (original vs re-parsed)
    5. Re-generate re-parsed YAML → LaTeX
    6. Normalize re-generated LaTeX
    7. Compare LaTeX (generated vs re-generated)
    """
    start_time = datetime.now()
    result = {
        "file": yaml_file.name,
        "yaml_roundtrip": {"success": False, "num_diffs": None},
        "latex_roundtrip": {"success": False, "num_diffs": None},
        "validation_passed": False,
        "error": None,
        "time_ms": 0.0,
    }

    try:
        file_stem = yaml_file.stem
        work_dir.mkdir(exist_ok=True, parents=True)

        # Step 1: Generate YAML → LaTeX
        generated_tex = work_dir / f"{file_stem}_generated.tex"
        try:
            yaml_to_latex(yaml_file, generated_tex)
        except Exception as e:
            result["error"] = f"Generation error: {str(e)}"
            return result

        # Step 2: Normalize generated LaTeX
        normalized_tex = work_dir / f"{file_stem}_generated_normalized.tex"
        success, _ = process_file(
            generated_tex, normalized_tex, comment_types=set(), normalize=True, dry_run=False
        )
        if not success:
            result["error"] = "Failed to normalize generated LaTeX"
            return result

        # Step 3: Parse LaTeX → YAML
        reparsed_yaml = work_dir / f"{file_stem}_reparsed.yaml"
        try:
            latex_to_yaml(normalized_tex, reparsed_yaml)
        except Exception as e:
            result["error"] = f"Parse error: {str(e)}"
            return result

        # Step 4: YAML Roundtrip Comparison (original vs re-parsed)
        yaml_diff_lines, yaml_num_diffs = compare_yaml_structured(yaml_file, reparsed_yaml)

        if yaml_num_diffs > 0:
            yaml_diff_file = work_dir / "yaml_roundtrip.diff"
            yaml_diff_file.write_text("\n".join(yaml_diff_lines), encoding="utf-8")

        result["yaml_roundtrip"] = {
            "success": (yaml_num_diffs <= max_yaml_diffs),
            "num_diffs": yaml_num_diffs,
        }

        # Step 5: Re-generate re-parsed YAML → LaTeX
        regenerated_tex = work_dir / f"{file_stem}_regenerated.tex"
        try:
            yaml_to_latex(reparsed_yaml, regenerated_tex)
        except Exception as e:
            result["error"] = f"Re-generation error: {str(e)}"
            return result

        # Step 6: Normalize re-generated LaTeX
        normalized_regenerated = work_dir / f"{file_stem}_regenerated_normalized.tex"
        success, _ = process_file(
            regenerated_tex,
            normalized_regenerated,
            comment_types=set(),
            normalize=True,
            dry_run=False,
        )
        if not success:
            result["error"] = "Failed to normalize re-generated LaTeX"
            return result

        # Step 7: LaTeX Roundtrip Comparison (generated vs re-generated)
        latex_diff_lines, latex_num_diffs = get_meaningful_diff(
            normalized_tex, normalized_regenerated
        )

        if latex_num_diffs > 0:
            latex_diff_file = work_dir / "latex_roundtrip.diff"
            latex_diff_file.write_text("\n".join(latex_diff_lines), encoding="utf-8")

        result["latex_roundtrip"] = {
            "success": (latex_num_diffs <= max_latex_diffs),
            "num_diffs": latex_num_diffs,
        }

        # Determine if validation passed
        result["validation_passed"] = (
            result["yaml_roundtrip"]["success"] and result["latex_roundtrip"]["success"]
        )

    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"

    finally:
        end_time = datetime.now()
        result["time_ms"] = (end_time - start_time).total_seconds() * 1000

    return result


# Type-aware validation functions


def _validate_parse_allowed(resume_name: str) -> None:
    """
    Check if parsing is allowed for this resume. Raises ValueError if not.

    Parsing (LaTeX → YAML) is allowed for:
    - historical: must be 'normalized' or 'parsing_failed'
    - test: any status

    Raises:
        ValueError: If resume not registered or invalid type/status for parsing
    """
    if not resume_is_registered(resume_name):
        raise ValueError(f"Resume not registered: {resume_name}")

    info = get_resume_status(resume_name)
    resume_type = info.get("resume_type")
    status = info.get("status")

    if resume_type == "historical":
        if status not in ("normalized", "parsing_failed"):
            raise ValueError(
                f"Historical resume must be 'normalized' or 'parsing_failed', got '{status}'"
            )

    elif resume_type == "test":
        pass  # Test resumes always allowed

    else:  # experimental, generated
        raise ValueError(
            f"Cannot parse {resume_type} resumes (wrong direction: use generate instead)"
        )


def _validate_generate_allowed(resume_name: str) -> None:
    """
    Check if generation is allowed for this resume. Raises ValueError if not.

    Generation (YAML → LaTeX) is allowed for:
    - experimental: must be 'drafting_completed'
    - generated: must be 'targeting_completed'
    - test: any status

    Raises:
        ValueError: If resume not registered or invalid type/status for generation
    """
    if not resume_is_registered(resume_name):
        raise ValueError(f"Resume not registered: {resume_name}")

    info = get_resume_status(resume_name)
    resume_type = info.get("resume_type")
    status = info.get("status")

    if resume_type == "experimental":
        if status != "drafting_completed":
            raise ValueError(f"Experimental resume must be 'drafting_completed', got '{status}'")

    elif resume_type == "generated":
        if status != "targeting_completed":
            raise ValueError(f"Generated resume must be 'targeting_completed', got '{status}'")

    elif resume_type == "test":
        pass  # Test resumes always allowed

    else:  # historical
        raise ValueError("Cannot generate LaTeX for historical resumes (they already have LaTeX)")


# Orchestration configs and helper function

PARSE_CONFIG = ConversionConfig(
    phase_name="parse",
    status_in_progress="parsing",
    status_success="parsed",
    status_failure="parsing_failed",
    output_extension=".yaml",
    intermediate_suffix="_parsed",
    convert_fn=latex_to_yaml,
)

GENERATE_CONFIG = ConversionConfig(
    phase_name="generate",
    status_in_progress="templating",
    status_success="templating_completed",
    status_failure="templating_failed",
    output_extension=".tex",
    intermediate_suffix="_generated_normalized",
    convert_fn=yaml_to_latex,
)


def _run_conversion(
    resume_name: str,
    input_path: Path,
    output_dir: Path,
    max_latex_diffs: int,
    max_yaml_diffs: int,
    config: ConversionConfig,
) -> ConversionResult:
    """
    Shared orchestration logic for both conversion directions.

    Caller must validate that operation is allowed before calling this function.
    Always runs roundtrip validation. Use yaml_to_latex/latex_to_yaml directly
    if you need to skip validation.

    Handles:
    1. Setup two-tier logging
    2. Run roundtrip validation
    3. If validation passes: copy output to final location
    4. Update registry status based on outcome
    5. Clean up artifacts on success, keep on failure

    Args:
        resume_name: Resume identifier
        input_path: Path to input file
        output_dir: Directory for output
        max_latex_diffs: Maximum LaTeX diffs allowed for validation
        max_yaml_diffs: Maximum YAML diffs allowed for validation
        config: Direction-specific configuration

    Returns:
        ConversionResult with success status, paths, validation info, and timing
    """
    start_time = time.time()

    # Setup logging
    log_dir = LOGS_PATH / f"{config.phase_name}_{now()}"
    log_file = setup_templating_logger(log_dir, phase=config.phase_name)
    log_conversion_start(resume_name, input_path, log_file, config.phase_name)

    # Update status to in-progress
    update_resume_status(
        updates={resume_name: config.status_in_progress},
        source="templating",
    )

    # Determine final output path
    output_dir.mkdir(parents=True, exist_ok=True)
    final_output_path = output_dir / f"{resume_name}{config.output_extension}"

    # Run roundtrip validation (routes based on input_path extension)
    output_filename = f"{resume_name}{config.intermediate_suffix}{config.output_extension}"
    try:
        roundtrip_validation_result = validate_roundtrip_conversion(
            input_path, log_dir, max_latex_diffs, max_yaml_diffs
        )

        elapsed = time.time() - start_time

        # Create base result with known values
        result = ConversionResult(
            success=roundtrip_validation_result["validation_passed"],
            error=roundtrip_validation_result["error"],
            input_path=input_path,
            time_s=elapsed,
            log_dir=log_dir,
            yaml_diffs=roundtrip_validation_result["yaml_roundtrip"]["num_diffs"],
            latex_diffs=roundtrip_validation_result["latex_roundtrip"]["num_diffs"],
        )
    except Exception as e:
        elapsed = time.time() - start_time
        result = ConversionResult(
            success=False,
            error=str(e),
            input_path=input_path,
            time_s=elapsed,
            log_dir=log_dir,
        )

    # Handle success vs failure
    if result.success:
        # Copy output to final location
        shutil.copy(log_dir / output_filename, final_output_path)

        # Clean up intermediate validation artifacts but keep log
        for file in log_dir.iterdir():
            if file.name != "template.log":
                file.unlink()
        _log_debug("Cleaned up validation artifacts.")

        # Update result with output path
        result.output_path = final_output_path

        # Prepare success metadata for pipeline events
        extra_fields_for_pipeline_event = {"output_path": str(final_output_path)}
        outcome = config.status_success
    else:
        # Keep all artifacts for debugging
        _log_debug("Keeping artifacts for debugging.")

        # Update result with error
        result.error = result.error or "Roundtrip validation failed"

        # Prepare failure metadata for pipeline events
        extra_fields_for_pipeline_event = {
            "error": result.error,
            "yaml_diffs": result.yaml_diffs,
            "latex_diffs": result.latex_diffs,
        }
        outcome = config.status_failure

    # Update registry status with metadata
    update_resume_status(
        updates={resume_name: outcome},
        source="templating",
        time_s=elapsed,
        **extra_fields_for_pipeline_event,
    )

    log_conversion_result(resume_name, result, elapsed, config.phase_name)
    return result


def parse_resume(
    resume_name: str,
    output_dir: Optional[Path] = None,
    max_latex_diffs: int = 6,
    max_yaml_diffs: int = 0,
    allow_overwrite: bool = True,
) -> ConversionResult:
    """
    Parse LaTeX resume to YAML with registry tracking, validation, and logging.

    Always runs roundtrip validation. Use latex_to_yaml() directly if you need
    to skip validation.

    Args:
        resume_name: Resume identifier (looked up in registry)
        output_dir: Directory for YAML output. If None, uses structured/ parallel to tex file.
        max_latex_diffs: Maximum LaTeX diffs allowed for validation (default: 6)
        max_yaml_diffs: Maximum YAML diffs allowed for validation (default: 0)
        allow_overwrite: Allow overwriting existing output file (default: True)

    Returns:
        ConversionResult with success status, paths, validation info, and timing
    """
    # Validate parsing is allowed (raises ValueError if not)
    _validate_parse_allowed(resume_name)

    # Get input file (raises ValueError if not found)
    tex_file = get_resume_file(resume_name, "tex")

    # Default output: use registry to get expected yaml path
    if output_dir is None:
        expected_yaml = get_resume_file(resume_name, "yaml", file_expected=False)
        output_dir = expected_yaml.parent

    # Check overwrite before starting orchestration
    output_path = output_dir / f"{resume_name}.yaml"
    if not allow_overwrite and output_path.exists():
        raise ValueError(f"Output file already exists: {output_path}")

    return _run_conversion(
        resume_name=resume_name,
        input_path=tex_file,
        output_dir=output_dir,
        max_latex_diffs=max_latex_diffs,
        max_yaml_diffs=max_yaml_diffs,
        config=PARSE_CONFIG,
    )


def generate_resume(
    resume_name: str,
    output_dir: Optional[Path] = None,
    max_latex_diffs: int = 6,
    max_yaml_diffs: int = 0,
    allow_overwrite: bool = True,
) -> ConversionResult:
    """
    Generate LaTeX from YAML with registry tracking, validation, and logging.

    Always runs roundtrip validation. Use yaml_to_latex() directly if you need
    to skip validation.

    Args:
        resume_name: Resume identifier (looked up in registry)
        output_dir: Directory for LaTeX output. If None, uses raw/ parallel to YAML file.
        max_latex_diffs: Maximum LaTeX diffs allowed for validation (default: 6)
        max_yaml_diffs: Maximum YAML diffs allowed for validation (default: 0)
        allow_overwrite: Allow overwriting existing output file (default: True)

    Returns:
        ConversionResult with success status, paths, validation info, and timing
    """
    # Validate generation is allowed (raises ValueError if not)
    _validate_generate_allowed(resume_name)

    # Get input file (raises ValueError if not found)
    yaml_path = get_resume_file(resume_name, "yaml")

    # Default output: use registry to get expected tex path (normalized location)
    if output_dir is None:
        expected_tex = get_resume_file(resume_name, "tex", file_expected=False)
        output_dir = expected_tex.parent

    # Check overwrite before starting orchestration
    output_path = output_dir / f"{resume_name}.tex"
    if not allow_overwrite and output_path.exists():
        raise ValueError(f"Output file already exists: {output_path}")

    return _run_conversion(
        resume_name=resume_name,
        input_path=yaml_path,
        output_dir=output_dir,
        max_latex_diffs=max_latex_diffs,
        max_yaml_diffs=max_yaml_diffs,
        config=GENERATE_CONFIG,
    )
