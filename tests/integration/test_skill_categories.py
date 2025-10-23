"""
Integration test for skill_categories round-trip conversion.
Tests: YAML -> LaTeX -> YAML produces identical structure for nested categories.
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
def test_yaml_to_latex_skill_categories():
    """Test converting YAML nested categories to LaTeX format."""
    yaml_path = STRUCTURED_PATH / "software_tools_test.yaml"
    yaml_data = OmegaConf.load(yaml_path)
    yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

    converter = YAMLToLaTeXConverter()
    latex = converter.convert_skill_categories(yaml_dict["section"])

    # Verify structure
    assert "\\begin{itemize}" in latex
    assert "\\end{itemize}" in latex

    # Verify all categories present
    assert "\\item[\\faRobot]" in latex
    assert "\\item[\\faChartLine]" in latex
    assert "\\item[\\faCode]" in latex

    # Verify category names with small caps
    assert "{\\scshape LLM Architectures}" in latex
    assert "{\\scshape ML Frameworks}" in latex
    assert "{\\scshape Development}" in latex

    # Verify itemizeLL environments
    assert "\\begin{itemizeLL}" in latex
    assert "\\end{itemizeLL}" in latex

    # Verify specific items
    assert "\\itemLL {Mixture of Experts (MoE)}" in latex
    assert "\\itemLL {PyTorch}" in latex
    assert "\\itemLL {Git}" in latex


@pytest.mark.integration
def test_latex_to_yaml_skill_categories():
    """Test parsing LaTeX nested categories to YAML structure."""
    latex_path = STRUCTURED_PATH / "software_tools_test.tex"
    latex_str = latex_path.read_text(encoding="utf-8")

    converter = LaTeXToYAMLConverter()
    result = converter.parse_skill_categories(latex_str)

    # Verify structure
    assert result["type"] == "skill_categories"
    assert "subsections" in result
    assert len(result["subsections"]) == 3

    # Verify first category
    cat1 = result["subsections"][0]
    assert cat1["type"] == "skill_category"
    assert cat1["metadata"]["name"] == "LLM Architectures"
    assert cat1["metadata"]["icon"] == "\\faRobot"
    assert len(cat1["content"]["list"]) == 3
    assert "Mixture of Experts (MoE)" in cat1["content"]["list"]

    # Verify second category
    cat2 = result["subsections"][1]
    assert cat2["metadata"]["name"] == "ML Frameworks"
    assert cat2["metadata"]["icon"] == "\\faChartLine"
    assert "PyTorch" in cat2["content"]["list"]
    assert "JAX/Equinox" in cat2["content"]["list"]

    # Verify third category
    cat3 = result["subsections"][2]
    assert cat3["metadata"]["name"] == "Development"
    assert cat3["metadata"]["icon"] == "\\faCode"
    assert "Git" in cat3["content"]["list"]


@pytest.mark.integration
def test_skill_categories_roundtrip():
    """Test full round-trip: YAML -> LaTeX -> YAML."""
    yaml_path = STRUCTURED_PATH / "software_tools_test.yaml"
    original_yaml = OmegaConf.load(yaml_path)
    original_dict = OmegaConf.to_container(original_yaml, resolve=True)

    # YAML -> LaTeX
    converter_to_latex = YAMLToLaTeXConverter()
    latex = converter_to_latex.convert_skill_categories(original_dict["section"])

    # LaTeX -> YAML
    converter_to_yaml = LaTeXToYAMLConverter()
    roundtrip_dict = converter_to_yaml.parse_skill_categories(latex)

    # Compare structures (should be identical)
    assert roundtrip_dict == original_dict["section"]

    # Verify category count preserved
    assert len(roundtrip_dict["subsections"]) == len(original_dict["section"]["subsections"])

    # Verify order preservation (categories should appear in same order)
    for i, (orig_cat, rt_cat) in enumerate(zip(
        original_dict["section"]["subsections"],
        roundtrip_dict["subsections"]
    )):
        assert orig_cat["metadata"]["name"] == rt_cat["metadata"]["name"], \
            f"Category {i} name mismatch"
        assert orig_cat["content"]["list"] == rt_cat["content"]["list"], \
            f"Category {i} list mismatch"


@pytest.mark.integration
def test_skill_categories_icon_preservation():
    """Test that FontAwesome icons are preserved correctly."""
    latex_snippet = """
\\begin{itemize}[leftmargin=\\firstlistindent, labelsep = 0pt, align=center, labelwidth=\\firstlistlabelsep, itemsep = 8pt]

\\item[\\faDatabase] {\\scshape Databases}
\\begin{itemizeLL}
    \\itemLL {PostgreSQL}
    \\itemLL {Redis}
\\end{itemizeLL}

\\end{itemize}
"""

    converter = LaTeXToYAMLConverter()
    result = converter.parse_skill_categories(latex_snippet)

    assert len(result["subsections"]) == 1
    category = result["subsections"][0]
    assert category["metadata"]["icon"] == "\\faDatabase"
    assert category["metadata"]["name"] == "Databases"
    assert "PostgreSQL" in category["content"]["list"]
    assert "Redis" in category["content"]["list"]


@pytest.mark.integration
def test_skill_categories_special_characters():
    """Test handling of special characters in category items."""
    latex_snippet = """
\\begin{itemize}[leftmargin=\\firstlistindent, labelsep = 0pt, align=center, labelwidth=\\firstlistlabelsep, itemsep = 8pt]

\\item[\\faCode] {\\scshape Languages}
\\begin{itemizeLL}
    \\itemLL {C++}
    \\itemLL {C\\#}
    \\itemLL {Python 3.9+}
\\end{itemizeLL}

\\end{itemize}
"""

    converter = LaTeXToYAMLConverter()
    result = converter.parse_skill_categories(latex_snippet)

    items = result["subsections"][0]["content"]["list"]
    assert "C++" in items
    assert "C\\#" in items  # Escaped # preserved
    assert "Python 3.9+" in items
