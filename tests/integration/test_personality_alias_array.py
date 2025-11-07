"""
Integration test for personality_alias_array round-trip conversion.
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
def test_yaml_to_latex_personality_alias_array():
    """Test converting YAML personality alias array to LaTeX format."""
    yaml_path = FIXTURES_PATH / "alias_array_test.yaml"
    yaml_data = OmegaConf.load(yaml_path)
    yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

    # Extract expected items from YAML fixture
    expected_items = yaml_dict["section"]["content"]["bullets"]

    converter = YAMLToLaTeXConverter()
    latex = converter.convert_personality_alias_array(yaml_dict["section"])

    # Verify structure (always present)
    assert r"\begin{itemizeMain}" in latex
    assert r"\end{itemizeMain}" in latex

    # Verify all expected items present in generated LaTeX (marker and content)
    for item in expected_items:
        assert f"\\{item['marker']}" in latex
        assert item["latex_raw"] in latex


@pytest.mark.integration
def test_latex_to_yaml_personality_alias_array():
    """Test parsing LaTeX personality alias array to YAML structure."""
    latex_path = FIXTURES_PATH / "alias_array_test.tex"
    yaml_path = FIXTURES_PATH / "alias_array_test.yaml"

    # Load expected structure from YAML fixture
    yaml_data = OmegaConf.load(yaml_path)
    expected = OmegaConf.to_container(yaml_data)["section"]

    # Parse LaTeX
    latex_str = latex_path.read_text(encoding="utf-8")
    converter = LaTeXToYAMLConverter()
    result = converter.parse_personality_alias_array(latex_str)

    # Validate against expected YAML structure (dynamic, not hardcoded)
    assert result["type"] == expected["type"]
    assert "bullets" in result["content"]
    assert len(result["content"]["bullets"]) == len(expected["content"]["bullets"])

    # Verify each item matches (using structured format with marker, latex_raw, plaintext)
    for i, expected_item in enumerate(expected["content"]["bullets"]):
        result_item = result["content"]["bullets"][i]
        assert result_item["marker"] == expected_item["marker"]
        assert result_item["latex_raw"] == expected_item["latex_raw"]
        assert result_item["plaintext"] == expected_item["plaintext"]


@pytest.mark.integration
def test_personality_alias_array_roundtrip():
    """Test full round-trip: YAML -> LaTeX -> YAML."""
    yaml_path = FIXTURES_PATH / "alias_array_test.yaml"
    original_yaml = OmegaConf.load(yaml_path)
    original_dict = OmegaConf.to_container(original_yaml, resolve=True)

    # YAML -> LaTeX
    converter_to_latex = YAMLToLaTeXConverter()
    latex = converter_to_latex.convert_personality_alias_array(original_dict["section"])

    # LaTeX -> YAML
    converter_to_yaml = LaTeXToYAMLConverter()
    roundtrip_dict = converter_to_yaml.parse_personality_alias_array(latex)

    # Compare structures (parser may not return empty metadata dict)
    assert roundtrip_dict["type"] == original_dict["section"]["type"]
    assert roundtrip_dict["content"] == original_dict["section"]["content"]
