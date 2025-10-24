"""
Integration test for two-page resume structure.
Tests: LaTeX multi-page → parsed pages → LaTeX produces correct structure.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from omegaconf import OmegaConf

from archer.contexts.templating.converter import (
    YAMLToLaTeXConverter,
    LaTeXToYAMLConverter,
)

load_dotenv()
STRUCTURED_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH")) / "structured"


@pytest.mark.integration
def test_extract_two_pages():
    """Test extracting two pages from LaTeX document."""
    latex_path = STRUCTURED_PATH / "two_page_test.tex"
    yaml_path = STRUCTURED_PATH / "two_page_test.yaml"

    # Load expected structure from YAML fixture
    yaml_data = OmegaConf.load(yaml_path)
    expected_pages = OmegaConf.to_container(yaml_data)["document"]["pages"]

    # Need to wrap in full document for extract_pages()
    paracol_content = latex_path.read_text(encoding="utf-8")
    latex_str = "\\begin{document}\n" + paracol_content + "\n\\end{document}"

    parser = LaTeXToYAMLConverter()
    pages = parser.extract_pages(latex_str)

    # Verify page count matches expected
    assert len(pages) == len(expected_pages)

    # Verify each page structure matches expected
    for i, expected_page in enumerate(expected_pages):
        parsed_page = pages[i]
        assert parsed_page["page_number"] == expected_page["page_number"]
        assert parsed_page["regions"]["top"]["show_professional_profile"] == expected_page["regions"]["top"]["show_professional_profile"]

        # Verify left column (may be None for continuation pages)
        expected_left = expected_page["regions"]["left_column"]
        if expected_left is None:
            assert parsed_page["regions"]["left_column"] is None
        else:
            assert parsed_page["regions"]["left_column"] is not None
            parsed_left_sections = parsed_page["regions"]["left_column"]["sections"]
            expected_left_sections = expected_left["sections"]
            assert len(parsed_left_sections) == len(expected_left_sections)
            for j, expected_section in enumerate(expected_left_sections):
                assert parsed_left_sections[j]["name"] == expected_section["name"]

        # Verify main column
        parsed_main_sections = parsed_page["regions"]["main_column"]["sections"]
        expected_main_sections = expected_page["regions"]["main_column"]["sections"]
        assert len(parsed_main_sections) == len(expected_main_sections)
        for j, expected_section in enumerate(expected_main_sections):
            assert parsed_main_sections[j]["name"] == expected_section["name"]


@pytest.mark.integration
def test_two_page_content_preservation():
    """Test that content is preserved across pages."""
    latex_path = STRUCTURED_PATH / "two_page_test.tex"
    yaml_path = STRUCTURED_PATH / "two_page_test.yaml"

    # Load expected structure from YAML fixture
    yaml_data = OmegaConf.load(yaml_path)
    expected_pages = OmegaConf.to_container(yaml_data)["document"]["pages"]

    # Parse LaTeX
    paracol_content = latex_path.read_text(encoding="utf-8")
    latex_str = "\\begin{document}\n" + paracol_content + "\n\\end{document}"
    parser = LaTeXToYAMLConverter()
    pages = parser.extract_pages(latex_str)

    # Verify content on all pages matches expected
    for i, expected_page in enumerate(expected_pages):
        parsed_page = pages[i]
        expected_main_sections = expected_page["regions"]["main_column"]["sections"]
        parsed_main_sections = parsed_page["regions"]["main_column"]["sections"]

        for j, expected_section in enumerate(expected_main_sections):
            parsed_section = parsed_main_sections[j]
            if "subsections" in expected_section:
                for k, expected_subsection in enumerate(expected_section["subsections"]):
                    parsed_subsection = parsed_section["subsections"][k]
                    # Verify metadata matches
                    for key in expected_subsection.get("metadata", {}):
                        assert parsed_subsection["metadata"][key] == expected_subsection["metadata"][key]
                    # Verify bullet count matches
                    if "bullets" in expected_subsection.get("content", {}):
                        assert len(parsed_subsection["content"]["bullets"]) == len(expected_subsection["content"]["bullets"])


@pytest.mark.integration
def test_two_page_yaml_match():
    """Test that parsed structure matches expected YAML."""
    latex_path = STRUCTURED_PATH / "two_page_test.tex"
    yaml_path = STRUCTURED_PATH / "two_page_test.yaml"

    paracol_content = latex_path.read_text(encoding="utf-8")
    latex_str = "\\begin{document}\n" + paracol_content + "\n\\end{document}"

    parser = LaTeXToYAMLConverter()
    pages = parser.extract_pages(latex_str)

    # Load expected YAML
    yaml_data = OmegaConf.load(yaml_path)
    expected_pages = OmegaConf.to_container(yaml_data["document"]["pages"], resolve=True)

    # Verify same number of pages
    assert len(pages) == len(expected_pages)

    # Verify page numbers
    for parsed, expected in zip(pages, expected_pages):
        assert parsed["page_number"] == expected["page_number"]

    # Verify section counts
    p1_left_count = len(pages[0]["regions"]["left_column"]["sections"])
    p1_main_count = len(pages[0]["regions"]["main_column"]["sections"])
    e1_left_count = len(expected_pages[0]["regions"]["left_column"]["sections"])
    e1_main_count = len(expected_pages[0]["regions"]["main_column"]["sections"])

    assert p1_left_count == e1_left_count
    assert p1_main_count == e1_main_count


@pytest.mark.integration
def test_clearpage_split():
    """Test that \\clearpage correctly splits pages."""
    # Create test LaTeX with explicit clearpage
    test_latex = """\\begin{document}
\\begin{paracol}{2}

\\section*{Section 1}
Content 1

\\switchcolumn

\\section*{Section 2}
Content 2

\\clearpage

\\section*{Section 3}
Content 3

\\end{paracol}
\\end{document}"""

    parser = LaTeXToYAMLConverter()
    pages = parser.extract_pages(test_latex)

    # Should extract 2 pages
    assert len(pages) == 2

    # Page 1 should have Section 1 and Section 2
    page1_sections = []
    if pages[0]["regions"]["left_column"]:
        page1_sections.extend([s["name"] for s in pages[0]["regions"]["left_column"]["sections"]])
    if pages[0]["regions"]["main_column"]:
        page1_sections.extend([s["name"] for s in pages[0]["regions"]["main_column"]["sections"]])

    # Page 2 should have Section 3
    page2_sections = []
    if pages[1]["regions"]["main_column"]:
        page2_sections.extend([s["name"] for s in pages[1]["regions"]["main_column"]["sections"]])

    assert "Section 3" in page2_sections
    assert "Section 3" not in page1_sections
