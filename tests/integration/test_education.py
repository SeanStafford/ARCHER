"""
Integration test for education round-trip conversion.
Tests: YAML -> LaTeX -> YAML produces identical structure.

Education section uses simplified approach: static content with metadata toggles.
"""

import os
from pathlib import Path

import pytest
from omegaconf import OmegaConf
from dotenv import load_dotenv

from archer.contexts.templating.converter import (
    YAMLToLaTeXConverter,
    LaTeXToYAMLConverter,
)

load_dotenv()
FIXTURES_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH")) / "fixtures"


@pytest.mark.integration
def test_yaml_to_latex_education():
    """Test converting YAML education section to LaTeX format."""
    yaml_path = FIXTURES_PATH / "education_test.yaml"
    yaml_data = OmegaConf.load(yaml_path)
    yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

    # Extract metadata toggles from YAML fixture
    include_dissertation = yaml_dict["section"]["metadata"].get("include_dissertation", False)
    include_minor = yaml_dict["section"]["metadata"].get("include_minor", False)

    converter = YAMLToLaTeXConverter()
    latex = converter.convert_education(yaml_dict["section"])

    # Verify static content (always present)
    assert r"\begin{itemize}[leftmargin=0pt, itemsep = 0pt]" in latex
    assert r"\end{itemize}" in latex
    assert "Florida State University" in latex
    assert "Tallahassee, FL" in latex
    assert "Doctor of Philosophy in Physics" in latex
    assert "July 2022" in latex
    assert "Master of Science in Physics" in latex
    assert "Apr 2021" in latex
    assert "St. Mary's College of Maryland" in latex
    assert "St. Mary's City, MD" in latex
    assert "Bachelor of Arts in Physics and Biochemistry" in latex
    assert "May 2015" in latex

    # Verify optional dissertation
    if include_dissertation:
        assert "Dissertation" in latex
    else:
        assert "Dissertation" not in latex

    # Verify optional minor
    if include_minor:
        assert "Minor in Neuroscience" in latex
    else:
        assert "Minor in Neuroscience" not in latex


@pytest.mark.integration
def test_latex_to_yaml_education():
    """Test parsing LaTeX education section to YAML structure."""
    latex_path = FIXTURES_PATH / "education_test.tex"
    yaml_path = FIXTURES_PATH / "education_test.yaml"

    # Load expected structure from YAML fixture
    yaml_data = OmegaConf.load(yaml_path)
    expected = OmegaConf.to_container(yaml_data)["section"]

    # Parse LaTeX
    latex_str = latex_path.read_text(encoding="utf-8")
    converter = LaTeXToYAMLConverter()
    result = converter.parse_education(latex_str)

    # Validate against expected YAML structure (dynamic, not hardcoded)
    assert result["type"] == expected["type"]
    assert "metadata" in result
    assert result["metadata"]["include_dissertation"] == expected["metadata"]["include_dissertation"]
    assert result["metadata"]["include_minor"] == expected["metadata"]["include_minor"]


@pytest.mark.integration
def test_education_roundtrip():
    """Test full round-trip: YAML -> LaTeX -> YAML."""
    yaml_path = FIXTURES_PATH / "education_test.yaml"
    original_yaml = OmegaConf.load(yaml_path)
    original_dict = OmegaConf.to_container(original_yaml, resolve=True)

    # YAML -> LaTeX
    converter_to_latex = YAMLToLaTeXConverter()
    latex = converter_to_latex.convert_education(original_dict["section"])

    # LaTeX -> YAML
    converter_to_yaml = LaTeXToYAMLConverter()
    roundtrip_dict = converter_to_yaml.parse_education(latex)

    # Compare structures (parser may add extra metadata fields like use_icon_bullets)
    # Check that all original fields match, but allow extra fields in roundtrip
    assert roundtrip_dict["type"] == original_dict["section"]["type"]
    for key in original_dict["section"]["metadata"]:
        assert roundtrip_dict["metadata"][key] == original_dict["section"]["metadata"][key]
