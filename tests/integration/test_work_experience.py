"""
Integration test for work_experience round-trip conversion.
Tests: YAML -> LaTeX -> YAML produces identical structure.

work_experience is the most critical content type - every resume has it.
Tests cover:
- itemizeAcademic environment
- Multi-level bullets (itemi, itemii)
- Nested projects (itemizeKeyProject)
- Company/title/location/dates parsing
- Subtitle handling (title split on \\)
- Dual-field architecture (latex_raw + plaintext)
"""

import os
from pathlib import Path

import pytest
from omegaconf import OmegaConf
from dotenv import load_dotenv

from archer.contexts.templating.latex_generator import YAMLToLaTeXConverter
from archer.contexts.templating.latex_parser import LaTeXToYAMLConverter

load_dotenv()
FIXTURES_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH")) / "fixtures"


@pytest.mark.integration
def test_yaml_to_latex_work_experience():
    """Test converting YAML work_experience to LaTeX format."""
    yaml_path = FIXTURES_PATH / "work_experience_test.yaml"
    yaml_data = OmegaConf.load(yaml_path)
    yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

    # Extract expected data from YAML fixture
    expected_company = yaml_dict["subsection"]["metadata"]["company"]
    expected_title = yaml_dict["subsection"]["metadata"]["title"]
    expected_subtitle = yaml_dict["subsection"]["metadata"]["subtitle"]
    expected_location = yaml_dict["subsection"]["metadata"]["location"]
    expected_dates = yaml_dict["subsection"]["metadata"]["dates"]
    expected_bullets = yaml_dict["subsection"]["content"]["bullets"]
    expected_projects = yaml_dict["subsection"]["content"]["projects"]

    converter = YAMLToLaTeXConverter()
    latex = converter.convert_work_experience(yaml_dict["subsection"])

    # Verify itemizeAcademic environment
    assert r"\begin{itemizeAcademic}" in latex
    assert r"\end{itemizeAcademic}" in latex

    # Verify metadata in header
    assert expected_company in latex
    assert expected_title in latex
    assert expected_subtitle in latex
    assert expected_location in latex
    assert expected_dates in latex

    # Verify all top-level bullets present
    for bullet in expected_bullets:
        assert bullet["latex_raw"] in latex
        assert f"\\{bullet['marker']}" in latex

    # Verify nested project present
    assert r"\begin{itemizeKeyProject}" in latex
    assert r"\end{itemizeKeyProject}" in latex
    assert expected_projects[0]["metadata"]["name"] in latex

    # Verify project bullets
    for bullet in expected_projects[0]["bullets"]:
        assert bullet["latex_raw"] in latex
        assert f"\\{bullet['marker']}" in latex


@pytest.mark.integration
def test_latex_to_yaml_work_experience():
    """Test parsing LaTeX work_experience to YAML structure."""
    latex_path = FIXTURES_PATH / "work_experience_test.tex"
    yaml_path = FIXTURES_PATH / "work_experience_test.yaml"

    # Load expected structure from YAML fixture
    yaml_data = OmegaConf.load(yaml_path)
    expected = OmegaConf.to_container(yaml_data)["subsection"]

    # Parse LaTeX
    latex_str = latex_path.read_text(encoding="utf-8")
    converter = LaTeXToYAMLConverter()
    result = converter.parse_work_experience(latex_str)

    # Validate type
    assert result["type"] == expected["type"]

    # Validate metadata fields
    assert result["metadata"]["company"] == expected["metadata"]["company"]
    assert result["metadata"]["title"] == expected["metadata"]["title"]
    assert result["metadata"]["subtitle"] == expected["metadata"]["subtitle"]
    assert result["metadata"]["location"] == expected["metadata"]["location"]
    assert result["metadata"]["dates"] == expected["metadata"]["dates"]

    # Validate bullets structure
    assert "bullets" in result["content"]
    assert len(result["content"]["bullets"]) == len(expected["content"]["bullets"])

    # Verify each bullet matches (marker, latex_raw, plaintext)
    for i, expected_bullet in enumerate(expected["content"]["bullets"]):
        result_bullet = result["content"]["bullets"][i]
        assert result_bullet["marker"] == expected_bullet["marker"]
        assert result_bullet["latex_raw"] == expected_bullet["latex_raw"]
        assert result_bullet["plaintext"] == expected_bullet["plaintext"]

    # Validate nested projects structure
    assert "projects" in result["content"]
    assert len(result["content"]["projects"]) == len(expected["content"]["projects"])

    # Verify project metadata
    expected_project = expected["content"]["projects"][0]
    result_project = result["content"]["projects"][0]
    assert result_project["type"] == expected_project["type"]
    assert result_project["metadata"]["environment_type"] == expected_project["metadata"]["environment_type"]
    assert result_project["metadata"]["name"] == expected_project["metadata"]["name"]
    assert result_project["metadata"]["dates"] == expected_project["metadata"]["dates"]

    # Verify project bullets
    for i, expected_bullet in enumerate(expected_project["bullets"]):
        result_bullet = result_project["bullets"][i]
        assert result_bullet["marker"] == expected_bullet["marker"]
        assert result_bullet["latex_raw"] == expected_bullet["latex_raw"]
        assert result_bullet["plaintext"] == expected_bullet["plaintext"]


@pytest.mark.integration
def test_work_experience_roundtrip():
    """Test full round-trip: YAML -> LaTeX -> YAML."""
    yaml_path = FIXTURES_PATH / "work_experience_test.yaml"
    original_yaml = OmegaConf.load(yaml_path)
    original_dict = OmegaConf.to_container(original_yaml, resolve=True)

    # YAML -> LaTeX
    converter_to_latex = YAMLToLaTeXConverter()
    latex = converter_to_latex.convert_work_experience(original_dict["subsection"])

    # LaTeX -> YAML
    converter_to_yaml = LaTeXToYAMLConverter()
    roundtrip_dict = converter_to_yaml.parse_work_experience(latex)

    # Compare structures
    assert roundtrip_dict["type"] == original_dict["subsection"]["type"]

    # Metadata should match
    for key in original_dict["subsection"]["metadata"]:
        assert roundtrip_dict["metadata"][key] == original_dict["subsection"]["metadata"][key]

    # Bullets should match
    assert len(roundtrip_dict["content"]["bullets"]) == len(original_dict["subsection"]["content"]["bullets"])
    for i, original_bullet in enumerate(original_dict["subsection"]["content"]["bullets"]):
        roundtrip_bullet = roundtrip_dict["content"]["bullets"][i]
        assert roundtrip_bullet["marker"] == original_bullet["marker"]
        assert roundtrip_bullet["latex_raw"] == original_bullet["latex_raw"]
        assert roundtrip_bullet["plaintext"] == original_bullet["plaintext"]

    # Projects should match
    assert len(roundtrip_dict["content"]["projects"]) == len(original_dict["subsection"]["content"]["projects"])
    for i, original_project in enumerate(original_dict["subsection"]["content"]["projects"]):
        roundtrip_project = roundtrip_dict["content"]["projects"][i]
        assert roundtrip_project["type"] == original_project["type"]

        # Project metadata should match
        for key in original_project["metadata"]:
            assert roundtrip_project["metadata"][key] == original_project["metadata"][key]

        # Project bullets should match
        for j, original_bullet in enumerate(original_project["bullets"]):
            roundtrip_bullet = roundtrip_project["bullets"][j]
            assert roundtrip_bullet["marker"] == original_bullet["marker"]
            assert roundtrip_bullet["latex_raw"] == original_bullet["latex_raw"]
            assert roundtrip_bullet["plaintext"] == original_bullet["plaintext"]


@pytest.mark.integration
def test_work_experience_subtitle_parsing():
    """Test that subtitle is correctly extracted when title contains \\."""
    latex_path = FIXTURES_PATH / "work_experience_test.tex"
    latex_str = latex_path.read_text(encoding="utf-8")

    converter = LaTeXToYAMLConverter()
    result = converter.parse_work_experience(latex_str)

    # Verify title/subtitle split
    assert result["metadata"]["title"] == "Machine Learning Engineer"
    assert "subcontractor" in result["metadata"]["subtitle"]
    assert r"\textit{\color{verygray}" in result["metadata"]["subtitle"]


@pytest.mark.integration
def test_work_experience_multi_level_bullets():
    """Test that multi-level bullets (itemi, itemii) are preserved."""
    yaml_path = FIXTURES_PATH / "work_experience_test.yaml"
    yaml_data = OmegaConf.load(yaml_path)
    yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

    # Verify fixture has both itemi and itemii
    top_level_markers = [b["marker"] for b in yaml_dict["subsection"]["content"]["bullets"]]
    assert all(marker == "itemi" for marker in top_level_markers), "Top-level bullets should use itemi"

    project_markers = [b["marker"] for b in yaml_dict["subsection"]["content"]["projects"][0]["bullets"]]
    assert all(marker == "itemii" for marker in project_markers), "Project bullets should use itemii"

    # Test roundtrip preserves markers
    converter_to_latex = YAMLToLaTeXConverter()
    latex = converter_to_latex.convert_work_experience(yaml_dict["subsection"])

    converter_to_yaml = LaTeXToYAMLConverter()
    roundtrip_dict = converter_to_yaml.parse_work_experience(latex)

    # Verify markers preserved
    roundtrip_top_markers = [b["marker"] for b in roundtrip_dict["content"]["bullets"]]
    assert roundtrip_top_markers == top_level_markers

    roundtrip_project_markers = [b["marker"] for b in roundtrip_dict["content"]["projects"][0]["bullets"]]
    assert roundtrip_project_markers == project_markers


@pytest.mark.integration
def test_work_experience_nested_project_environment_type():
    """Test that nested project environment type (itemizeKeyProject) is preserved."""
    yaml_path = FIXTURES_PATH / "work_experience_test.yaml"
    yaml_data = OmegaConf.load(yaml_path)
    yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

    original_env_type = yaml_dict["subsection"]["content"]["projects"][0]["metadata"]["environment_type"]
    assert original_env_type == "itemizeKeyProject"

    # Test roundtrip preserves environment type
    converter_to_latex = YAMLToLaTeXConverter()
    latex = converter_to_latex.convert_work_experience(yaml_dict["subsection"])

    # Verify LaTeX uses correct environment
    assert r"\begin{itemizeKeyProject}" in latex
    assert r"\end{itemizeKeyProject}" in latex

    converter_to_yaml = LaTeXToYAMLConverter()
    roundtrip_dict = converter_to_yaml.parse_work_experience(latex)

    # Verify environment type preserved in metadata
    assert roundtrip_dict["content"]["projects"][0]["metadata"]["environment_type"] == original_env_type


@pytest.mark.integration
def test_work_experience_dual_field_preservation():
    """Test that dual-field architecture (latex_raw + plaintext) is preserved."""
    latex_path = FIXTURES_PATH / "work_experience_test.tex"
    latex_str = latex_path.read_text(encoding="utf-8")

    converter = LaTeXToYAMLConverter()
    result = converter.parse_work_experience(latex_str)

    # Check top-level bullets have both fields
    for bullet in result["content"]["bullets"]:
        assert "latex_raw" in bullet
        assert "plaintext" in bullet

        # Verify plaintext has no LaTeX commands (key requirement)
        assert r"\textbf{" not in bullet["plaintext"]
        assert r"\texttt{" not in bullet["plaintext"]
        assert "$" not in bullet["plaintext"]  # Math mode

        # If latex_raw has formatting, plaintext should differ
        has_formatting = any(cmd in bullet["latex_raw"] for cmd in [r"\textbf{", r"\texttt{", r"$\to$"])
        if has_formatting:
            assert bullet["latex_raw"] != bullet["plaintext"]

    # Check project bullets have both fields
    for project in result["content"]["projects"]:
        for bullet in project["bullets"]:
            assert "latex_raw" in bullet
            assert "plaintext" in bullet
