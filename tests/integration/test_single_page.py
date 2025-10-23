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
    latex_str = latex_path.read_text(encoding="utf-8")

    converter = LaTeXToYAMLConverter()
    page_regions = converter.extract_page_regions(latex_str, page_number=1)

    # Verify structure
    assert page_regions["top"]["show_professional_profile"] == True
    assert page_regions["left_column"] is not None
    assert page_regions["main_column"] is not None

    # Verify left column sections
    left_sections = page_regions["left_column"]["sections"]
    assert len(left_sections) == 2
    assert left_sections[0]["name"] == "Core Skills"
    assert left_sections[0]["type"] == "skill_list_caps"
    assert left_sections[1]["name"] == "Languages"
    assert left_sections[1]["type"] == "skill_list_pipes"

    # Verify main column sections
    main_sections = page_regions["main_column"]["sections"]
    assert len(main_sections) == 1
    assert main_sections[0]["name"] == "Experience"
    assert main_sections[0]["type"] == "work_history"


@pytest.mark.integration
def test_generate_single_page_structure():
    """Test generating LaTeX page from structured format."""
    yaml_path = STRUCTURED_PATH / "single_page_test.yaml"
    yaml_data = OmegaConf.load(yaml_path)
    yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

    converter = YAMLToLaTeXConverter()
    latex = converter.generate_page(yaml_dict["page"]["regions"])

    # Verify structure
    assert "\\begin{paracol}{2}" in latex
    assert "\\switchcolumn" in latex
    assert "\\end{paracol}" in latex

    # Verify sections present
    assert "\\section*{Core Skills}" in latex
    assert "\\section*{Languages}" in latex
    assert "\\section*{Experience}" in latex

    # Verify content types
    assert "\\setlength{\\baselineskip}" in latex  # skill_list_caps
    assert "\\texttt{Python}" in latex  # skill_list_pipes
    assert "\\begin{itemizeAcademic}" in latex  # work_experience


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
    latex_str = latex_path.read_text(encoding="utf-8")

    parser = LaTeXToYAMLConverter()
    page_regions = parser.extract_page_regions(latex_str, page_number=1)

    # Check Core Skills content
    core_skills = page_regions["left_column"]["sections"][0]
    assert "Machine Learning" in core_skills["content"]["list"]
    assert "High-Performance\\\\Computing (HPC)" in core_skills["content"]["list"]

    # Check Languages content
    languages = page_regions["left_column"]["sections"][1]
    assert "Python" in languages["content"]["list"]
    assert "Bash" in languages["content"]["list"]
    assert "C++" in languages["content"]["list"]

    # Check Experience content
    experience = page_regions["main_column"]["sections"][0]
    assert len(experience["subsections"]) == 1
    work_exp = experience["subsections"][0]
    assert work_exp["metadata"]["company"] == "Test Company"
    assert len(work_exp["content"]["bullets"]) == 2
