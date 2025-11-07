"""
Integration test for skill_list_pipes round-trip conversion.
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
def test_yaml_to_latex_skill_list_pipes():
    """Test converting YAML skill list to LaTeX pipe-separated format."""
    yaml_path = FIXTURES_PATH / "languages_test.yaml"
    yaml_data = OmegaConf.load(yaml_path)
    yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

    # Extract expected items from YAML fixture
    expected_items = yaml_dict["section"]["content"]["items"]

    converter = YAMLToLaTeXConverter()
    latex = converter.convert_skill_list_pipes(yaml_dict["section"])

    # Verify all expected items present in generated LaTeX
    for item in expected_items:
        assert item['latex_raw'] in latex

    # Verify pipe separators present
    assert " | " in latex


@pytest.mark.integration
def test_latex_to_yaml_skill_list_pipes():
    """Test parsing LaTeX pipe-separated skill list to YAML structure."""
    latex_path = FIXTURES_PATH / "languages_test.tex"
    yaml_path = FIXTURES_PATH / "languages_test.yaml"

    # Load expected structure from YAML fixture
    yaml_data = OmegaConf.load(yaml_path)
    expected = OmegaConf.to_container(yaml_data)["section"]

    # Parse LaTeX (extract just the content line, not the section header)
    latex_str = latex_path.read_text(encoding="utf-8")
    # Extract the pipe-separated content line (skip section header)
    content_line = [line for line in latex_str.split('\n') if '|' in line][0].strip()

    converter = LaTeXToYAMLConverter()
    result = converter.parse_skill_list_pipes(content_line)

    # Validate against expected YAML structure (dynamic, not hardcoded)
    assert result["type"] == expected["type"]
    assert "items" in result["content"]
    assert len(result["content"]["items"]) == len(expected["content"]["items"])

    # Verify all expected items are parsed in correct order
    assert result["content"]["items"] == expected["content"]["items"]


@pytest.mark.integration
def test_skill_list_pipes_roundtrip():
    """Test full round-trip: YAML -> LaTeX -> YAML."""
    yaml_path = FIXTURES_PATH / "languages_test.yaml"
    original_yaml = OmegaConf.load(yaml_path)
    original_dict = OmegaConf.to_container(original_yaml, resolve=True)

    # YAML -> LaTeX
    converter_to_latex = YAMLToLaTeXConverter()
    latex = converter_to_latex.convert_skill_list_pipes(original_dict["section"])

    # LaTeX -> YAML
    converter_to_yaml = LaTeXToYAMLConverter()
    roundtrip_dict = converter_to_yaml.parse_skill_list_pipes(latex)

    # Compare structures (should be identical)
    assert roundtrip_dict == original_dict["section"]

    # Verify order preservation (critical for languages - Python first = primary)
    assert roundtrip_dict["content"]["items"] == original_dict["section"]["content"]["items"]


@pytest.mark.integration
def test_skill_list_pipes_special_characters():
    """Test handling of special characters like ++ in C++."""
    # Test data with special characters (formatted as in LaTeX source)
    expected_items_plain = ["C++", "C\\#", "F\\#"]
    expected_items_formatted = [f"\\texttt{{{item}}}" for item in expected_items_plain]
    latex_snippet = " | ".join(expected_items_formatted)

    converter = LaTeXToYAMLConverter()
    result = converter.parse_skill_list_pipes(latex_snippet)

    items = result["content"]["items"]
    # Parser preserves formatting in latex_raw field, check structured dicts
    latex_raws = [item["latex_raw"] for item in items]
    for expected_formatted in expected_items_formatted:
        assert expected_formatted in latex_raws
