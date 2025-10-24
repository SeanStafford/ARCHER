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

    # Extract expected categories from YAML fixture
    expected_subsections = yaml_dict["section"]["subsections"]

    converter = YAMLToLaTeXConverter()
    latex = converter.convert_skill_categories(yaml_dict["section"])

    # Verify structure
    assert "\\begin{itemize}" in latex
    assert "\\end{itemize}" in latex
    assert "\\begin{itemizeLL}" in latex
    assert "\\end{itemizeLL}" in latex

    # Verify all expected categories and items present
    for subsection in expected_subsections:
        icon = subsection["metadata"]["icon"]
        name = subsection["metadata"]["name"]
        assert f"\\item[{icon}]" in latex
        assert f"{{\\scshape {name}}}" in latex
        for item in subsection["content"]["list"]:
            assert f"\\itemLL {{{item}}}" in latex


@pytest.mark.integration
def test_latex_to_yaml_skill_categories():
    """Test parsing LaTeX nested categories to YAML structure."""
    latex_path = STRUCTURED_PATH / "software_tools_test.tex"
    yaml_path = STRUCTURED_PATH / "software_tools_test.yaml"

    # Load expected structure from YAML fixture
    yaml_data = OmegaConf.load(yaml_path)
    expected = OmegaConf.to_container(yaml_data)["section"]

    # Parse LaTeX
    latex_str = latex_path.read_text(encoding="utf-8")
    converter = LaTeXToYAMLConverter()
    result = converter.parse_skill_categories(latex_str)

    # Validate against expected YAML structure (dynamic, not hardcoded)
    assert result["type"] == expected["type"]
    assert "subsections" in result
    assert len(result["subsections"]) == len(expected["subsections"])

    # Verify each category matches expected
    for i, expected_cat in enumerate(expected["subsections"]):
        parsed_cat = result["subsections"][i]
        assert parsed_cat["type"] == expected_cat["type"]
        assert parsed_cat["metadata"]["name"] == expected_cat["metadata"]["name"]
        assert parsed_cat["metadata"]["icon"] == expected_cat["metadata"]["icon"]
        assert len(parsed_cat["content"]["list"]) == len(expected_cat["content"]["list"])
        for item in expected_cat["content"]["list"]:
            assert item in parsed_cat["content"]["list"]


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
    # Test data
    expected_icon = "\\faDatabase"
    expected_name = "Databases"
    expected_items = ["PostgreSQL", "Redis"]

    latex_snippet = f"""
\\begin{{itemize}}[leftmargin=\\firstlistindent, labelsep = 0pt, align=center, labelwidth=\\firstlistlabelsep, itemsep = 8pt]

\\item[{expected_icon}] {{\\scshape {expected_name}}}
\\begin{{itemizeLL}}
    \\itemLL {{{expected_items[0]}}}
    \\itemLL {{{expected_items[1]}}}
\\end{{itemizeLL}}

\\end{{itemize}}
"""

    converter = LaTeXToYAMLConverter()
    result = converter.parse_skill_categories(latex_snippet)

    assert len(result["subsections"]) == 1
    category = result["subsections"][0]
    assert category["metadata"]["icon"] == expected_icon
    assert category["metadata"]["name"] == expected_name
    for item in expected_items:
        assert item in category["content"]["list"]


@pytest.mark.integration
def test_skill_categories_special_characters():
    """Test handling of special characters in category items."""
    # Test data with special characters
    expected_icon = "\\faCode"
    expected_name = "Languages"
    expected_items = ["C++", "C\\#", "Python 3.9+"]

    latex_snippet = f"""
\\begin{{itemize}}[leftmargin=\\firstlistindent, labelsep = 0pt, align=center, labelwidth=\\firstlistlabelsep, itemsep = 8pt]

\\item[{expected_icon}] {{\\scshape {expected_name}}}
\\begin{{itemizeLL}}
    \\itemLL {{{expected_items[0]}}}
    \\itemLL {{{expected_items[1]}}}
    \\itemLL {{{expected_items[2]}}}
\\end{{itemizeLL}}

\\end{{itemize}}
"""

    converter = LaTeXToYAMLConverter()
    result = converter.parse_skill_categories(latex_snippet)

    items = result["subsections"][0]["content"]["list"]
    for item in expected_items:
        assert item in items
