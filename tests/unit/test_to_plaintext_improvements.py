"""
Tests for to_plaintext() improvements documented in templating/TODO.md.

These tests currently FAIL and document desired behavior for future implementation.
"""

import pytest
from archer.utils.latex_parsing_tools import to_plaintext


class TestHyperlinkHandling:
    """Test \href{url}{text} command handling."""

    def test_href_extracts_text_only(self):
        """Should extract only the display text, not the URL."""
        latex = r"Visit \href{https://example.com}{our website} for more"
        result = to_plaintext(latex)
        assert result == "Visit our website for more"
        assert "https://example.com" not in result
        assert r"\href" not in result

    def test_href_with_complex_text(self):
        """Should handle nested formatting in href text."""
        latex = r"\href{https://example.com}{\textbf{Bold Link}}"
        result = to_plaintext(latex)
        assert result == "Bold Link"
        assert r"\href" not in result
        assert r"\textbf" not in result

    def test_href_complex_real_world(self):
        """Test actual miniGAP example from structured YAMLs."""
        latex = r'\href{https://github.com/alvarovm/minigap}{ {\color{black} \texttt{miniGAP} (\faGithub)}}: {Built standalone ML app from scratch and released initial version}'
        result = to_plaintext(latex)
        # Should extract just the visible text, removing href, color, texttt, and faGithub icon
        assert "miniGAP" in result
        assert "Built standalone ML app" in result
        assert "github.com" not in result
        assert r"\href" not in result
        assert r"\faGithub" not in result


class TestColorEmphHandling:
    """Test \coloremph{text} custom command handling."""

    @pytest.mark.xfail(reason="TODO: Add coloremph to unwrap commands in to_plaintext()")
    def test_coloremph_unwraps(self):
        """Should unwrap \coloremph{} like other formatting commands."""
        latex = r"This is \coloremph{emphasized} text"
        result = to_plaintext(latex)
        assert result == "This is emphasized text"
        assert r"\coloremph" not in result

    @pytest.mark.xfail(reason="TODO: Add coloremph to unwrap commands in to_plaintext()")
    def test_coloremph_nested(self):
        """Should handle nested commands."""
        latex = r"\textbf{\coloremph{nested}}"
        result = to_plaintext(latex)
        assert result == "nested"


class TestEscapedSpaces:
    """Test backslash-space handling."""

    @pytest.mark.xfail(reason="TODO: Handle escaped spaces in to_plaintext()")
    def test_escaped_space(self):
        """Backslash-space should become regular space."""
        latex = r"Dr.\ John Smith"
        result = to_plaintext(latex)
        assert result == "Dr. John Smith"
        assert r"\ " not in result

    @pytest.mark.xfail(reason="TODO: Handle escaped spaces in to_plaintext()")
    def test_multiple_escaped_spaces(self):
        """Multiple escaped spaces should be handled."""
        latex = r"A\ B\ C"
        result = to_plaintext(latex)
        assert result == "A B C"


class TestSymbolCommands:
    """Test special LaTeX symbol commands."""

    @pytest.mark.xfail(reason="TODO: Add symbol mapping table in to_plaintext()")
    def test_texttimes(self):
        r"""\texttimes should become multiplication sign."""
        latex = r"3\texttimes 4 = 12"
        result = to_plaintext(latex)
        assert result == "3× 4 = 12"

    @pytest.mark.xfail(reason="TODO: Add symbol mapping table in to_plaintext()")
    def test_textdegree(self):
        r"""\textdegree should become degree symbol."""
        latex = r"Temperature: 72\textdegree F"
        result = to_plaintext(latex)
        assert result == "Temperature: 72° F"

    @pytest.mark.xfail(reason="TODO: Add symbol mapping table in to_plaintext()")
    def test_textpm(self):
        r"""\textpm should become plus-minus symbol."""
        latex = r"Error: \textpm 5\%"
        result = to_plaintext(latex)
        assert result == "Error: ± 5%"
