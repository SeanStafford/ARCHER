"""
Integration test for skill_list_caps round-trip conversion.
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
FIXTURES_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH")) / "fixtures"


@pytest.mark.integration
def test_yaml_to_latex_skill_list_caps():
    """Test converting YAML skill list to LaTeX format."""
    yaml_path = FIXTURES_PATH / "core_skills_test.yaml"
    yaml_data = OmegaConf.load(yaml_path)
    yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

    # Extract expected items from YAML fixture
    expected_items = yaml_dict["section"]["content"]["items"]

    converter = YAMLToLaTeXConverter()
    latex = converter.convert_skill_list_caps(yaml_dict["section"])

    # Verify structure (always present for this type)
    assert "\\setlength{\\baselineskip}" in latex
    assert "\\scshape" in latex

    # Verify all expected items present in generated LaTeX
    for item in expected_items:
        assert item['latex_raw'] in latex


@pytest.mark.integration
def test_latex_to_yaml_skill_list_caps():
    """Test parsing LaTeX skill list to YAML structure."""
    latex_path = FIXTURES_PATH / "core_skills_test.tex"
    yaml_path = FIXTURES_PATH / "core_skills_test.yaml"

    # Load expected structure from YAML fixture
    yaml_data = OmegaConf.load(yaml_path)
    expected = OmegaConf.to_container(yaml_data)["section"]

    # Parse LaTeX
    latex_str = latex_path.read_text(encoding="utf-8")
    converter = LaTeXToYAMLConverter()
    result = converter.parse_skill_list_caps(latex_str)

    # Validate against expected YAML structure (dynamic, not hardcoded)
    assert result["type"] == expected["type"]
    assert "items" in result["content"]
    assert len(result["content"]["items"]) == len(expected["content"]["items"])

    # Verify all expected items are parsed
    for item in expected["content"]["items"]:
        assert item in result["content"]["items"]


@pytest.mark.integration
def test_skill_list_caps_roundtrip():
    """Test full round-trip: YAML -> LaTeX -> YAML."""
    yaml_path = FIXTURES_PATH / "core_skills_test.yaml"
    original_yaml = OmegaConf.load(yaml_path)
    original_dict = OmegaConf.to_container(original_yaml, resolve=True)

    # YAML -> LaTeX
    converter_to_latex = YAMLToLaTeXConverter()
    latex = converter_to_latex.convert_skill_list_caps(original_dict["section"])

    # LaTeX -> YAML
    converter_to_yaml = LaTeXToYAMLConverter()
    roundtrip_dict = converter_to_yaml.parse_skill_list_caps(latex)

    # Compare structures (should be identical)
    assert roundtrip_dict == original_dict["section"]
