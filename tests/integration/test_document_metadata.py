"""
Integration test for document metadata parsing and generation.
Tests: LaTeX preamble → parsed metadata → LaTeX produces correct preamble.
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
FIXTURES_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH")) / "fixtures"


@pytest.mark.integration
def test_parse_document_metadata():
    """Test parsing document metadata from LaTeX preamble."""
    latex_path = FIXTURES_PATH / "document_metadata_test.tex"
    yaml_path = FIXTURES_PATH / "document_metadata_test.yaml"

    # Load expected values from YAML fixture
    expected_yaml = OmegaConf.load(yaml_path)
    expected = OmegaConf.to_container(expected_yaml)["document"]["metadata"]

    # Parse LaTeX
    parser = LaTeXToYAMLConverter()
    latex_str = latex_path.read_text(encoding="utf-8")
    metadata = parser.extract_document_metadata(latex_str)

    # Validate against expected YAML values (dynamic, not hardcoded)
    # Parser returns dual fields: raw (with LaTeX formatting) + plaintext
    # The fixture stores semantic plaintext values, so compare against name_plaintext
    assert metadata["name_plaintext"] == expected["name"]
    assert metadata["date"] == expected["date"]
    assert metadata["brand_plaintext"] == expected["brand"]

    # Verify name field preserves LaTeX formatting
    assert "\\textbf{" in metadata["name"]
    assert expected["name"] in metadata["name"]  # Plaintext is contained in raw

    # Verify professional profile (dual fields)
    assert metadata["professional_profile_plaintext"] == expected["professional_profile"]

    # Verify colors
    for color_key in expected["colors"]:
        assert metadata["colors"][color_key] == expected["colors"][color_key]

    # Verify other fields
    for field_key in expected["fields"]:
        assert field_key in metadata["fields"]
        assert metadata["fields"][field_key] == expected["fields"][field_key]


@pytest.mark.integration
def test_generate_preamble():
    """Test generating LaTeX preamble from metadata."""
    metadata = {
        "name": "\\textbf{Sean Stafford}",  # Raw LaTeX for template
        "date": "July 2025",
        "brand": "Research Infrastructure Engineer | Physicist",
        "professional_profile": "\\centering \\textbf{Physicist scaling research infrastructure from quantum simulation pipelines to LLM benchmarking systems}\\par",
        "colors": {
            "emphcolor": "NetflixDark",
            "topbarcolor": "black",
            "leftbarcolor": "gray9",
            "brandcolor": "white",
            "namecolor": "Netflix",
        },
        "fields": {
            "pdfkeywords": "Sean, Stafford, Resume"
        },
        "setlengths": {  # Required by template
            "leftmargin": "0.4in",
            "rightmargin": "0.5in",
            "aboveheader": "10pt",
            "bottommargin": "0.2in"
        },
        "deflens": {}  # Required by template (can be empty)
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
    latex_path = FIXTURES_PATH / "document_metadata_test.tex"
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

    # Parser returns dual fields: raw + plaintext
    assert metadata["name_plaintext"] == "Test Name"
    assert "\\textbf{Test Name}" == metadata["name"]  # Raw preserves formatting
    assert metadata["date"] == "January 2025"
    assert metadata["brand_plaintext"] == "Software Engineer"
    assert metadata["professional_profile"] is None
    assert metadata["professional_profile_plaintext"] is None
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

    # Known fields extracted correctly (dual fields: raw + plaintext)
    assert metadata["name_plaintext"] == "Test User"
    assert metadata["name"] == "\\textbf{Test User}"  # Raw preserves formatting
    assert metadata["brand_plaintext"] == "Test Brand"
    assert metadata["brand"] == "Test Brand"  # Brand has no formatting in this test

    # Custom fields preserved in fields dict
    assert "customfield" in metadata["fields"]
    assert metadata["fields"]["customfield"] == "Custom Value"
    assert "anotherfield" in metadata["fields"]
    assert metadata["fields"]["anotherfield"] == "Another Value"
