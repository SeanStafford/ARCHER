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
    # Need to wrap in full document for extract_pages()
    paracol_content = latex_path.read_text(encoding="utf-8")
    latex_str = "\\begin{document}\n" + paracol_content + "\n\\end{document}"

    parser = LaTeXToYAMLConverter()
    pages = parser.extract_pages(latex_str)

    # Verify two pages extracted
    assert len(pages) == 2

    # Verify page 1 structure
    page1 = pages[0]
    assert page1["page_number"] == 1
    assert page1["regions"]["top"]["show_professional_profile"] == True
    assert page1["regions"]["left_column"] is not None
    assert page1["regions"]["main_column"] is not None

    # Verify page 1 sections
    left_sections = page1["regions"]["left_column"]["sections"]
    assert len(left_sections) == 1
    assert left_sections[0]["name"] == "Core Skills"

    main_sections = page1["regions"]["main_column"]["sections"]
    assert len(main_sections) == 1
    assert main_sections[0]["name"] == "Experience"

    # Verify page 2 structure
    page2 = pages[1]
    assert page2["page_number"] == 2
    assert page2["regions"]["top"]["show_professional_profile"] == False

    # Page 2 should have no left column (continuation of main column only)
    assert page2["regions"]["left_column"] is None
    assert page2["regions"]["main_column"] is not None

    # Verify page 2 sections
    page2_sections = page2["regions"]["main_column"]["sections"]
    assert len(page2_sections) == 1
    assert page2_sections[0]["name"] == "More Experience"


@pytest.mark.integration
def test_two_page_content_preservation():
    """Test that content is preserved across pages."""
    latex_path = STRUCTURED_PATH / "two_page_test.tex"
    paracol_content = latex_path.read_text(encoding="utf-8")
    latex_str = "\\begin{document}\n" + paracol_content + "\n\\end{document}"

    parser = LaTeXToYAMLConverter()
    pages = parser.extract_pages(latex_str)

    # Page 1 content
    page1_exp = pages[0]["regions"]["main_column"]["sections"][0]
    assert page1_exp["subsections"][0]["metadata"]["company"] == "Test Company"
    assert len(page1_exp["subsections"][0]["content"]["bullets"]) == 2

    # Page 2 content
    page2_exp = pages[1]["regions"]["main_column"]["sections"][0]
    assert page2_exp["subsections"][0]["metadata"]["company"] == "Another Company"
    assert page2_exp["subsections"][0]["metadata"]["title"] == "Senior Engineer"
    assert len(page2_exp["subsections"][0]["content"]["bullets"]) == 2


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
