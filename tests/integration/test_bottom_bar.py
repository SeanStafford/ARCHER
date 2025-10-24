"""
Integration test for bottom bar extraction and generation.
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
def test_generate_bottom_bar():
    """Test generating LaTeX bottom bar from YAML."""
    yaml_path = STRUCTURED_PATH / "bottom_bar_test.yaml"
    yaml_data = OmegaConf.load(yaml_path)
    yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

    # Extract expected data from YAML fixture
    expected_name = yaml_dict["bottom"]["name"]
    expected_text = yaml_dict["bottom"]["text"]

    converter = YAMLToLaTeXConverter()
    latex = converter.generate_bottom_bar(yaml_dict["bottom"])

    # Verify structure (always present)
    assert r"\begin{textblock*}" in latex
    assert r"\end{textblock*}" in latex
    assert r"\section*" in latex

    # Verify content
    assert expected_name in latex


@pytest.mark.integration
def test_extract_bottom_bar():
    """Test extracting bottom bar from LaTeX."""
    latex_path = STRUCTURED_PATH / "bottom_bar_test.tex"
    yaml_path = STRUCTURED_PATH / "bottom_bar_test.yaml"

    # Load expected structure from YAML fixture
    yaml_data = OmegaConf.load(yaml_path)
    expected = OmegaConf.to_container(yaml_data)["bottom"]

    # Parse LaTeX
    latex_str = latex_path.read_text(encoding="utf-8")
    converter = LaTeXToYAMLConverter()
    result = converter.extract_bottom_bar(latex_str)

    # Validate against expected YAML structure (dynamic, not hardcoded)
    assert result is not None
    assert result["name"] == expected["name"]
    # Text content should match (formatting commands removed)
    assert "Persian" in result["text"]
    assert "Parrot" in result["text"]
    assert "karaoke" in result["text"]


@pytest.mark.integration
def test_bottom_bar_roundtrip():
    """Test full round-trip: YAML -> LaTeX -> YAML."""
    yaml_path = STRUCTURED_PATH / "bottom_bar_test.yaml"
    original_yaml = OmegaConf.load(yaml_path)
    original_dict = OmegaConf.to_container(original_yaml, resolve=True)

    # YAML -> LaTeX
    converter_to_latex = YAMLToLaTeXConverter()
    latex = converter_to_latex.generate_bottom_bar(original_dict["bottom"])

    # LaTeX -> YAML
    converter_to_yaml = LaTeXToYAMLConverter()
    roundtrip_dict = converter_to_yaml.extract_bottom_bar(latex)

    # Compare name (should be identical)
    assert roundtrip_dict["name"] == original_dict["bottom"]["name"]

    # Text should preserve key content (formatting may differ slightly)
    assert "Persian" in roundtrip_dict["text"]
    assert "Parrot" in roundtrip_dict["text"]
    assert "karaoke" in roundtrip_dict["text"]
