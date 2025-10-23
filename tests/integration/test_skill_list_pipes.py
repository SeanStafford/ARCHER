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
STRUCTURED_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH")) / "structured"


@pytest.mark.integration
def test_yaml_to_latex_skill_list_pipes():
    """Test converting YAML skill list to LaTeX pipe-separated format."""
    yaml_path = STRUCTURED_PATH / "languages_test.yaml"
    yaml_data = OmegaConf.load(yaml_path)
    yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

    converter = YAMLToLaTeXConverter()
    latex = converter.convert_skill_list_pipes(yaml_dict["section"])

    # Verify structure
    assert "\\texttt{Python}" in latex
    assert "\\texttt{Bash}" in latex
    assert "\\texttt{C++}" in latex
    assert "\\texttt{MATLAB}" in latex
    assert "\\texttt{Mathematica}" in latex
    assert " | " in latex  # Pipe separators


@pytest.mark.integration
def test_latex_to_yaml_skill_list_pipes():
    """Test parsing LaTeX pipe-separated skill list to YAML structure."""
    latex_path = STRUCTURED_PATH / "languages_test.tex"
    latex_str = latex_path.read_text(encoding="utf-8")

    converter = LaTeXToYAMLConverter()
    result = converter.parse_skill_list_pipes(latex_str)

    # Verify structure
    assert result["type"] == "skill_list_pipes"
    assert "list" in result["content"]
    assert len(result["content"]["list"]) == 5

    # Verify specific items (order matters!)
    items = result["content"]["list"]
    assert items[0] == "Python"
    assert items[1] == "Bash"
    assert items[2] == "C++"
    assert items[3] == "MATLAB"
    assert items[4] == "Mathematica"


@pytest.mark.integration
def test_skill_list_pipes_roundtrip():
    """Test full round-trip: YAML -> LaTeX -> YAML."""
    yaml_path = STRUCTURED_PATH / "languages_test.yaml"
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
    assert roundtrip_dict["content"]["list"] == original_dict["section"]["content"]["list"]


@pytest.mark.integration
def test_skill_list_pipes_special_characters():
    """Test handling of special characters like ++ in C++."""
    latex_snippet = "\\texttt{C++} | \\texttt{C\\#} | \\texttt{F\\#}"

    converter = LaTeXToYAMLConverter()
    result = converter.parse_skill_list_pipes(latex_snippet)

    items = result["content"]["list"]
    assert "C++" in items
    assert "C\\#" in items  # Escaped # preserved
    assert "F\\#" in items
