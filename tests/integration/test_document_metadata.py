"""
Integration test for document metadata parsing and generation.
Tests: LaTeX preamble → parsed metadata → LaTeX produces correct preamble.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from archer.contexts.templating.converter import (
    YAMLToLaTeXConverter,
    LaTeXToYAMLConverter,
)

load_dotenv()
STRUCTURED_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH")) / "structured"


@pytest.mark.integration
def test_parse_document_metadata():
    """Test parsing document metadata from LaTeX preamble."""
    latex_path = STRUCTURED_PATH / "document_metadata_test.tex"
    latex_str = latex_path.read_text(encoding="utf-8")

    parser = LaTeXToYAMLConverter()
    metadata = parser.extract_document_metadata(latex_str)

    # Verify basic fields
    assert metadata["name"] == "Sean Stafford"
    assert metadata["date"] == "July 2025"
    assert metadata["brand"] == "Research Infrastructure Engineer | Physicist"

    # Verify professional profile
    assert metadata["professional_profile"] is not None
    assert "Physicist scaling research infrastructure" in metadata["professional_profile"]

    # Verify colors
    assert metadata["colors"]["emphcolor"] == "NetflixDark"
    assert metadata["colors"]["topbarcolor"] == "black"
    assert metadata["colors"]["leftbarcolor"] == "gray9"
    assert metadata["colors"]["brandcolor"] == "white"
    assert metadata["colors"]["namecolor"] == "Netflix"

    # Verify other fields
    assert "pdfkeywords" in metadata["fields"]
    assert metadata["fields"]["pdfkeywords"] == "Sean, Stafford, Resume"


@pytest.mark.integration
def test_generate_preamble():
    """Test generating LaTeX preamble from metadata."""
    metadata = {
        "name": "Sean Stafford",
        "date": "July 2025",
        "brand": "Research Infrastructure Engineer | Physicist",
        "professional_profile": "Physicist scaling research infrastructure from quantum simulation pipelines to LLM benchmarking systems",
        "colors": {
            "emphcolor": "NetflixDark",
            "topbarcolor": "black",
            "leftbarcolor": "gray9",
            "brandcolor": "white",
            "namecolor": "Netflix",
        },
        "fields": {
            "pdfkeywords": "Sean, Stafford, Resume"
        }
    }

    generator = YAMLToLaTeXConverter()
    preamble = generator.generate_preamble(metadata)

    # Verify structure
    assert "\\renewcommand{\\myname}{\\textbf{Sean Stafford}}" in preamble
    assert "\\renewcommand{\\mydate}{July 2025}" in preamble
    assert "\\renewcommand{\\brand}{Research Infrastructure Engineer | Physicist}" in preamble

    # Verify colors
    assert "\\renewcommand{\\emphcolor}{NetflixDark}" in preamble
    assert "\\renewcommand{\\topbarcolor}{black}" in preamble

    # Verify professional profile
    assert "\\renewcommand{\\ProfessionalProfile}" in preamble
    assert "Physicist scaling research infrastructure" in preamble

    # Verify pdfkeywords
    assert "\\renewcommand{\\pdfkeywords}{Sean, Stafford, Resume}" in preamble


@pytest.mark.integration
def test_metadata_roundtrip():
    """Test full round-trip: LaTeX → metadata → LaTeX."""
    latex_path = STRUCTURED_PATH / "document_metadata_test.tex"
    original_latex = latex_path.read_text(encoding="utf-8")

    # Parse metadata
    parser = LaTeXToYAMLConverter()
    metadata = parser.extract_document_metadata(original_latex)

    # Generate preamble back
    generator = YAMLToLaTeXConverter()
    generated_preamble = generator.generate_preamble(metadata)

    # Parse generated preamble (need to wrap in document for parser)
    test_latex = generated_preamble + "\n\\begin{document}\n\\end{document}"
    roundtrip_metadata = parser.extract_document_metadata(test_latex)

    # Verify all fields preserved
    assert roundtrip_metadata["name"] == metadata["name"]
    assert roundtrip_metadata["date"] == metadata["date"]
    assert roundtrip_metadata["brand"] == metadata["brand"]

    # Colors should be preserved
    for color_key in metadata["colors"]:
        assert roundtrip_metadata["colors"][color_key] == metadata["colors"][color_key]


@pytest.mark.integration
def test_metadata_without_profile():
    """Test metadata parsing when professional profile is absent."""
    latex = """
\\renewcommand{\\myname}{\\textbf{Test Name}}
\\renewcommand{\\mydate}{January 2025}
\\renewcommand{\\brand}{Software Engineer}
\\renewcommand{\\emphcolor}{black}

\\begin{document}
\\end{document}
"""

    parser = LaTeXToYAMLConverter()
    metadata = parser.extract_document_metadata(latex)

    assert metadata["name"] == "Test Name"
    assert metadata["date"] == "January 2025"
    assert metadata["brand"] == "Software Engineer"
    assert metadata["professional_profile"] is None
    assert metadata["colors"]["emphcolor"] == "black"


@pytest.mark.integration
def test_metadata_field_preservation():
    """Test that all \\renewcommand fields are preserved."""
    latex = """
\\renewcommand{\\myname}{\\textbf{Test User}}
\\renewcommand{\\mydate}{December 2024}
\\renewcommand{\\brand}{Test Brand}
\\renewcommand{\\customfield}{Custom Value}
\\renewcommand{\\anotherfield}{Another Value}
\\renewcommand{\\emphcolor}{blue}

\\begin{document}
\\end{document}
"""

    parser = LaTeXToYAMLConverter()
    metadata = parser.extract_document_metadata(latex)

    # Known fields extracted correctly
    assert metadata["name"] == "Test User"
    assert metadata["brand"] == "Test Brand"

    # Custom fields preserved in fields dict
    assert "customfield" in metadata["fields"]
    assert metadata["fields"]["customfield"] == "Custom Value"
    assert "anotherfield" in metadata["fields"]
    assert metadata["fields"]["anotherfield"] == "Another Value"
