"""
Integration test for single-page resume structure with paracol.
Tests: LaTeX page → parsed structure → LaTeX produces correct structure.
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
def test_parse_single_page_structure():
    """Test parsing LaTeX page with paracol into structured format."""
    latex_path = STRUCTURED_PATH / "single_page_test.tex"
    yaml_path = STRUCTURED_PATH / "single_page_test.yaml"

    # Load expected structure from YAML fixture
    yaml_data = OmegaConf.load(yaml_path)
    expected_regions = OmegaConf.to_container(yaml_data)["page"]["regions"]

    # Parse LaTeX
    latex_str = latex_path.read_text(encoding="utf-8")
    converter = LaTeXToYAMLConverter()
    page_regions = converter.extract_page_regions(latex_str, page_number=1)

    # Verify structure matches expected
    assert page_regions["top"]["show_professional_profile"] == expected_regions["top"]["show_professional_profile"]
    assert page_regions["left_column"] is not None
    assert page_regions["main_column"] is not None

    # Verify left column sections match expected
    left_sections = page_regions["left_column"]["sections"]
    expected_left = expected_regions["left_column"]["sections"]
    assert len(left_sections) == len(expected_left)
    for i, expected_section in enumerate(expected_left):
        assert left_sections[i]["name"] == expected_section["name"]
        assert left_sections[i]["type"] == expected_section["type"]

    # Verify main column sections match expected
    main_sections = page_regions["main_column"]["sections"]
    expected_main = expected_regions["main_column"]["sections"]
    assert len(main_sections) == len(expected_main)
    for i, expected_section in enumerate(expected_main):
        assert main_sections[i]["name"] == expected_section["name"]
        assert main_sections[i]["type"] == expected_section["type"]


@pytest.mark.integration
def test_generate_single_page_structure():
    """Test generating LaTeX page from structured format."""
    yaml_path = STRUCTURED_PATH / "single_page_test.yaml"
    yaml_data = OmegaConf.load(yaml_path)
    yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

    # Extract expected section names and types from YAML fixture
    expected_regions = yaml_dict["page"]["regions"]

    converter = YAMLToLaTeXConverter()
    latex = converter.generate_page(expected_regions)

    # Verify paracol structure
    assert "\\begin{paracol}{2}" in latex
    assert "\\switchcolumn" in latex
    assert "\\end{paracol}" in latex

    # Verify all expected sections present in generated LaTeX
    for section in expected_regions["left_column"]["sections"]:
        assert f"\\section*{{{section['name']}}}" in latex

    for section in expected_regions["main_column"]["sections"]:
        assert f"\\section*{{{section['name']}}}" in latex


@pytest.mark.integration
def test_single_page_roundtrip():
    """Test full round-trip: LaTeX → structure → LaTeX."""
    latex_path = STRUCTURED_PATH / "single_page_test.tex"
    original_latex = latex_path.read_text(encoding="utf-8")

    # Parse LaTeX to structure
    parser = LaTeXToYAMLConverter()
    page_regions = parser.extract_page_regions(original_latex, page_number=1)

    # Generate back to LaTeX
    generator = YAMLToLaTeXConverter()
    generated_latex = generator.generate_page(page_regions)

    # Parse generated LaTeX again
    roundtrip_regions = parser.extract_page_regions(generated_latex, page_number=1)

    # Compare structures (should be identical)
    assert len(roundtrip_regions["left_column"]["sections"]) == len(page_regions["left_column"]["sections"])
    assert len(roundtrip_regions["main_column"]["sections"]) == len(page_regions["main_column"]["sections"])

    # Verify section names preserved
    for orig_sect, rt_sect in zip(
        page_regions["left_column"]["sections"],
        roundtrip_regions["left_column"]["sections"]
    ):
        assert orig_sect["name"] == rt_sect["name"]
        assert orig_sect["type"] == rt_sect["type"]

    for orig_sect, rt_sect in zip(
        page_regions["main_column"]["sections"],
        roundtrip_regions["main_column"]["sections"]
    ):
        assert orig_sect["name"] == rt_sect["name"]
        assert orig_sect["type"] == rt_sect["type"]


@pytest.mark.integration
def test_paracol_column_separation():
    """Test that left and main columns are correctly separated."""
    latex_path = STRUCTURED_PATH / "single_page_test.tex"
    latex_str = latex_path.read_text(encoding="utf-8")

    converter = LaTeXToYAMLConverter()
    page_regions = converter.extract_page_regions(latex_str, page_number=1)

    # Get section names from each column
    left_names = [s["name"] for s in page_regions["left_column"]["sections"]]
    main_names = [s["name"] for s in page_regions["main_column"]["sections"]]

    # Verify columns don't overlap
    assert "Core Skills" in left_names
    assert "Languages" in left_names
    assert "Experience" in main_names

    # Verify Experience is NOT in left column
    assert "Experience" not in left_names
    # Verify Core Skills is NOT in main column
    assert "Core Skills" not in main_names


@pytest.mark.integration
def test_section_content_preserved():
    """Test that section content is correctly preserved in round-trip."""
    latex_path = STRUCTURED_PATH / "single_page_test.tex"
    yaml_path = STRUCTURED_PATH / "single_page_test.yaml"

    # Load expected structure from YAML fixture
    yaml_data = OmegaConf.load(yaml_path)
    expected_regions = OmegaConf.to_container(yaml_data)["page"]["regions"]

    # Parse LaTeX
    latex_str = latex_path.read_text(encoding="utf-8")
    parser = LaTeXToYAMLConverter()
    page_regions = parser.extract_page_regions(latex_str, page_number=1)

    # Verify left column section content matches expected
    for i, expected_section in enumerate(expected_regions["left_column"]["sections"]):
        parsed_section = page_regions["left_column"]["sections"][i]
        if "list" in expected_section.get("content", {}):
            expected_items = expected_section["content"]["list"]
            parsed_items = parsed_section["content"]["list"]
            for item in expected_items:
                assert item in parsed_items, f"Expected item '{item}' not found in parsed content"

    # Verify main column section content matches expected
    for i, expected_section in enumerate(expected_regions["main_column"]["sections"]):
        parsed_section = page_regions["main_column"]["sections"][i]
        if "subsections" in expected_section:
            assert len(parsed_section["subsections"]) == len(expected_section["subsections"])
            for j, expected_subsection in enumerate(expected_section["subsections"]):
                parsed_subsection = parsed_section["subsections"][j]
                # Verify metadata matches
                for key in expected_subsection.get("metadata", {}):
                    assert parsed_subsection["metadata"][key] == expected_subsection["metadata"][key]
                # Verify bullet count matches
                if "bullets" in expected_subsection.get("content", {}):
                    assert len(parsed_subsection["content"]["bullets"]) == len(expected_subsection["content"]["bullets"])
