"""
Integration test for education round-trip conversion.
Tests: YAML -> LaTeX -> YAML produces identical structure.
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
STRUCTURED_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH")) / "structured"


@pytest.mark.integration
def test_yaml_to_latex_education():
    """Test converting YAML education section to LaTeX format."""
    yaml_path = STRUCTURED_PATH / "education_test.yaml"
    yaml_data = OmegaConf.load(yaml_path)
    yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

    # Extract expected data from YAML fixture
    expected_institutions = yaml_dict["section"]["content"]["institutions"]

    converter = YAMLToLaTeXConverter()
    latex = converter.convert_education(yaml_dict["section"])

    # Verify outer structure (always present)
    assert r"\begin{itemize}[leftmargin=0pt, itemsep = 0pt]" in latex
    assert r"\end{itemize}" in latex

    # Verify all expected institutions are present
    for institution in expected_institutions:
        assert institution["institution"] in latex
        assert institution["location"] in latex

        # Verify all degrees are present
        for degree in institution["degrees"]:
            assert degree["title"] in latex
            assert degree["date"] in latex

            # Verify details if present
            if "details" in degree:
                for detail in degree["details"]:
                    assert detail in latex


@pytest.mark.integration
def test_latex_to_yaml_education():
    """Test parsing LaTeX education section to YAML structure."""
    latex_path = STRUCTURED_PATH / "education_test.tex"
    yaml_path = STRUCTURED_PATH / "education_test.yaml"

    # Load expected structure from YAML fixture
    yaml_data = OmegaConf.load(yaml_path)
    expected = OmegaConf.to_container(yaml_data)["section"]

    # Parse LaTeX
    latex_str = latex_path.read_text(encoding="utf-8")
    converter = LaTeXToYAMLConverter()
    result = converter.parse_education(latex_str)

    # Validate against expected YAML structure (dynamic, not hardcoded)
    assert result["type"] == expected["type"]
    assert "institutions" in result["content"]
    assert len(result["content"]["institutions"]) == len(expected["content"]["institutions"])

    # Verify each institution matches
    for i, expected_inst in enumerate(expected["content"]["institutions"]):
        result_inst = result["content"]["institutions"][i]

        assert result_inst["institution"] == expected_inst["institution"]
        assert result_inst["location"] == expected_inst["location"]
        assert len(result_inst["degrees"]) == len(expected_inst["degrees"])

        # Verify each degree
        for j, expected_degree in enumerate(expected_inst["degrees"]):
            result_degree = result_inst["degrees"][j]

            assert result_degree["title"] == expected_degree["title"]
            assert result_degree["date"] == expected_degree["date"]

            # Verify details if present
            if "details" in expected_degree:
                assert "details" in result_degree
                assert len(result_degree["details"]) == len(expected_degree["details"])
                for detail in expected_degree["details"]:
                    assert detail in result_degree["details"]


@pytest.mark.integration
def test_education_roundtrip():
    """Test full round-trip: YAML -> LaTeX -> YAML."""
    yaml_path = STRUCTURED_PATH / "education_test.yaml"
    original_yaml = OmegaConf.load(yaml_path)
    original_dict = OmegaConf.to_container(original_yaml, resolve=True)

    # YAML -> LaTeX
    converter_to_latex = YAMLToLaTeXConverter()
    latex = converter_to_latex.convert_education(original_dict["section"])

    # LaTeX -> YAML
    converter_to_yaml = LaTeXToYAMLConverter()
    roundtrip_dict = converter_to_yaml.parse_education(latex)

    # Compare structures (should be identical)
    assert roundtrip_dict == original_dict["section"]
