"""Unit tests for TemplateRegistry class."""

import pytest
from pathlib import Path
from jinja2 import TemplateNotFound

from archer.contexts.templating.registries import TemplateRegistry


@pytest.mark.unit
def test_template_registry_init():
    """Test TemplateRegistry initialization."""
    registry = TemplateRegistry()
    assert registry.types_base_path.exists()
    assert registry._cache == {}


@pytest.mark.unit
def test_get_template_skill_list_caps():
    """Test loading skill_list_caps template."""
    registry = TemplateRegistry()
    template = registry.get_template("skill_list_caps")

    assert template is not None
    assert "skill_list_caps" in registry._cache


@pytest.mark.unit
def test_template_caching():
    """Test that templates are cached after first load."""
    registry = TemplateRegistry()

    # First load
    template1 = registry.get_template("skill_list_caps")
    assert registry.is_cached("skill_list_caps")

    # Second load should return same object from cache
    template2 = registry.get_template("skill_list_caps")
    assert template1 is template2


@pytest.mark.unit
def test_get_template_not_found():
    """Test error handling for missing template."""
    registry = TemplateRegistry()

    with pytest.raises(TemplateNotFound):
        registry.get_template("nonexistent_type")


@pytest.mark.unit
def test_get_template_path():
    """Test getting template file path."""
    registry = TemplateRegistry()
    path = registry.get_template_path("skill_list_caps")

    assert isinstance(path, Path)
    assert path.name == "template.tex.jinja"
    assert "skill_list_caps" in str(path)


@pytest.mark.unit
def test_clear_cache():
    """Test cache clearing."""
    registry = TemplateRegistry()

    # Load template
    registry.get_template("skill_list_caps")
    assert len(registry._cache) == 1

    # Clear cache
    registry.clear_cache()
    assert len(registry._cache) == 0


@pytest.mark.unit
def test_template_rendering():
    """Test that loaded template can render with data."""
    registry = TemplateRegistry()
    template = registry.get_template("skill_list_caps")

    # Test data matching skill_list_caps structure
    test_data = {
        "type": "skill_list_caps",
        "content": {
            "items": [
                {"latex_raw": "Python", "plaintext": "Python"},
                {"latex_raw": "Machine Learning", "plaintext": "Machine Learning"},
                {"latex_raw": "High Performance Computing", "plaintext": "High Performance Computing"}
            ]
        }
    }

    # Render template
    result = template.render(test_data)

    # Verify output contains expected elements
    assert "\\setlength{\\baselineskip}{10pt}" in result
    assert "\\scshape" in result
    assert "Python" in result
    assert "Machine Learning" in result
    assert "High Performance Computing" in result


@pytest.mark.unit
def test_custom_delimiters():
    """Test that custom delimiters work (no conflict with LaTeX braces)."""
    registry = TemplateRegistry()
    template = registry.get_template("skill_list_caps")

    # Template should use <<< >>> not {{ }}
    # If we render with LaTeX commands containing {}, they should not be interpreted
    test_data = {
        "type": "skill_list_caps",
        "content": {
            "items": [
                {"latex_raw": "\\textbf{Bold Text}", "plaintext": "Bold Text"},  # LaTeX command with braces
            ]
        }
    }

    result = template.render(test_data)

    # LaTeX braces should be preserved
    assert "\\textbf{Bold Text}" in result
