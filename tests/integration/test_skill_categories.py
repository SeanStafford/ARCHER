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
FIXTURES_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH")) / "fixtures"


@pytest.mark.integration
def test_yaml_to_latex_skill_categories():
    """Test converting YAML nested categories to LaTeX format."""
    yaml_path = FIXTURES_PATH / "software_tools_test.yaml"
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
        marker = subsection["metadata"]["marker"]
        name_raw = subsection["metadata"]["name_raw"]
        assert marker in latex
        assert name_raw in latex
        for item_dict in subsection["content"]["bullets"]:
            assert f"\\{item_dict['marker']} {item_dict['latex_raw']}" in latex


@pytest.mark.integration
def test_latex_to_yaml_skill_categories():
    """Test parsing LaTeX nested categories to YAML structure."""
    latex_path = FIXTURES_PATH / "software_tools_test.tex"
    yaml_path = FIXTURES_PATH / "software_tools_test.yaml"

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
        assert parsed_cat["metadata"]["marker"] == expected_cat["metadata"]["marker"]
        assert len(parsed_cat["content"]["bullets"]) == len(expected_cat["content"]["bullets"])
        # Items are structured dicts, compare plaintext values
        for expected_item, parsed_item in zip(expected_cat["content"]["bullets"], parsed_cat["content"]["bullets"]):
            assert parsed_item["plaintext"] == expected_item["plaintext"]


@pytest.mark.integration
def test_skill_categories_roundtrip():
    """Test full round-trip: YAML -> LaTeX -> YAML."""
    yaml_path = FIXTURES_PATH / "software_tools_test.yaml"
    original_yaml = OmegaConf.load(yaml_path)
    original_dict = OmegaConf.to_container(original_yaml, resolve=True)

    # YAML -> LaTeX
    converter_to_latex = YAMLToLaTeXConverter()
    latex = converter_to_latex.convert_skill_categories(original_dict["section"])

    # LaTeX -> YAML
    converter_to_yaml = LaTeXToYAMLConverter()
    roundtrip_dict = converter_to_yaml.parse_skill_categories(latex)

    # Compare structures (roundtrip may add extra None fields, filter them out)
    def filter_none_fields(d):
        """Recursively remove keys with None values for comparison"""
        if isinstance(d, dict):
            return {k: filter_none_fields(v) for k, v in d.items() if v is not None}
        elif isinstance(d, list):
            return [filter_none_fields(item) for item in d]
        else:
            return d

    roundtrip_filtered = filter_none_fields(roundtrip_dict)
    original_filtered = filter_none_fields(original_dict["section"])
    assert roundtrip_filtered == original_filtered

    # Verify category count preserved
    assert len(roundtrip_dict["subsections"]) == len(original_dict["section"]["subsections"])

    # Verify order preservation (categories should appear in same order)
    for i, (orig_cat, rt_cat) in enumerate(zip(
        original_dict["section"]["subsections"],
        roundtrip_dict["subsections"]
    )):
        assert orig_cat["metadata"]["name"] == rt_cat["metadata"]["name"], \
            f"Category {i} name mismatch"
        assert orig_cat["content"]["bullets"] == rt_cat["content"]["bullets"], \
            f"Category {i} list mismatch"


@pytest.mark.integration
def test_skill_categories_icon_preservation():
    """Test that FontAwesome icons are preserved correctly."""
    # Test data
    expected_marker = "\\item[\\faDatabase]"
    expected_name_raw = "{\\scshape Databases}"
    expected_name = "Databases"
    expected_items_plaintext = ["PostgreSQL", "Redis"]

    latex_snippet = f"""
\\begin{{itemize}}[leftmargin=\\firstlistindent, labelsep = 0pt, align=center, labelwidth=\\firstlistlabelsep, itemsep = 8pt]

{expected_marker} {expected_name_raw}
\\addcontentsline{{toc}}{{section}}{{{expected_name}}}
\\begin{{itemizeLL}}
    \\itemLL {{{expected_items_plaintext[0]}}}
    \\itemLL {{{expected_items_plaintext[1]}}}
\\end{{itemizeLL}}

\\end{{itemize}}
"""

    converter = LaTeXToYAMLConverter()
    result = converter.parse_skill_categories(latex_snippet)

    assert len(result["subsections"]) == 1
    category = result["subsections"][0]
    assert category["metadata"]["marker"] == expected_marker
    assert category["metadata"]["name"] == expected_name
    # Check items by plaintext
    parsed_plaintexts = [item["plaintext"] for item in category["content"]["bullets"]]
    for item in expected_items_plaintext:
        assert item in parsed_plaintexts


@pytest.mark.integration
def test_skill_categories_special_characters():
    """Test handling of special characters in category items."""
    # Test data with special characters
    expected_marker = "\\item[\\faCode]"
    expected_name = "Languages"
    # Note: Parser converts LaTeX escapes to plaintext (C\# -> C#)
    expected_items_plaintext = ["C++", "C#", "Python 3.9+"]

    latex_snippet = f"""
\\begin{{itemize}}[leftmargin=\\firstlistindent, labelsep = 0pt, align=center, labelwidth=\\firstlistlabelsep, itemsep = 8pt]

{expected_marker} {{\\scshape {expected_name}}}
\\addcontentsline{{toc}}{{section}}{{{expected_name}}}
\\begin{{itemizeLL}}
    \\itemLL {{{expected_items_plaintext[0]}}}
    \\itemLL {{{expected_items_plaintext[1]}}}
    \\itemLL {{{expected_items_plaintext[2]}}}
\\end{{itemizeLL}}

\\end{{itemize}}
"""

    converter = LaTeXToYAMLConverter()
    result = converter.parse_skill_categories(latex_snippet)

    # Check items by plaintext
    parsed_plaintexts = [item["plaintext"] for item in result["subsections"][0]["content"]["bullets"]]
    for item in expected_items_plaintext:
        assert item in parsed_plaintexts
