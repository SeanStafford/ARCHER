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
STRUCTURED_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH")) / "structured"


@pytest.mark.integration
def test_yaml_to_latex_skill_list_caps():
    """Test converting YAML skill list to LaTeX format."""
    yaml_path = STRUCTURED_PATH / "core_skills_test.yaml"
    yaml_data = OmegaConf.load(yaml_path)
    yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

    converter = YAMLToLaTeXConverter()
    latex = converter.convert_skill_list_caps(yaml_dict["section"])

    # Verify structure
    assert "\\setlength{\\baselineskip}" in latex
    assert "\\scshape" in latex
    assert "Machine Learning (ML)" in latex
    assert "High-Performance\\\\Computing (HPC)" in latex
    assert "Data Visualization" in latex


@pytest.mark.integration
def test_latex_to_yaml_skill_list_caps():
    """Test parsing LaTeX skill list to YAML structure."""
    latex_path = STRUCTURED_PATH / "core_skills_test.tex"
    latex_str = latex_path.read_text(encoding="utf-8")

    converter = LaTeXToYAMLConverter()
    result = converter.parse_skill_list_caps(latex_str)

    # Verify structure
    assert result["type"] == "skill_list_caps"
    assert "list" in result["content"]
    assert len(result["content"]["list"]) == 8

    # Verify specific items
    items = result["content"]["list"]
    assert "Machine Learning (ML)" in items
    assert "High-Performance\\\\Computing (HPC)" in items
    assert "Data Visualization" in items


@pytest.mark.integration
def test_skill_list_caps_roundtrip():
    """Test full round-trip: YAML -> LaTeX -> YAML."""
    yaml_path = STRUCTURED_PATH / "core_skills_test.yaml"
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
