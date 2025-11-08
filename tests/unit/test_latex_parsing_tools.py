"""
Unit tests for LaTeX parsing tools.

Tests core parsing utilities in archer.utils.latex_parsing_tools.
"""

import pytest
from archer.utils.latex_parsing_tools import (
    extract_itemize_entry,
    split_itemize_entries,
    parse_itemize_content,
    extract_environment,
    extract_all_environments,
    parse_itemize_with_complex_markers,
    extract_sequential_params,
    extract_environment_content,
    to_plaintext,
    to_latex,
    extract_brace_arguments,
    replace_command,
    strip_formatting,
    LaTeXPatterns
)


class TestExtractItemizeEntry:
    """Tests for extract_itemize_entry function."""

    def test_alphabetic_marker_simple(self):
        """Test extraction with simple alphabetic marker (itemi)."""
        entry = r'\itemi Simple text content'
        result = extract_itemize_entry(entry, LaTeXPatterns.ITEM_ALPHABETIC)

        assert result['marker'] == 'itemi'
        assert result['latex_raw'] == 'Simple text content'
        assert result['plaintext'] == 'Simple text content'

    def test_alphabetic_marker_with_formatting(self):
        """Test extraction with formatted content (textbf, textit)."""
        entry = r'\itemii \textbf{Bold} and \textit{italic} text'
        result = extract_itemize_entry(entry, LaTeXPatterns.ITEM_ALPHABETIC)

        assert result['marker'] == 'itemii'
        assert result['latex_raw'] == r'\textbf{Bold} and \textit{italic} text'
        assert result['plaintext'] == 'Bold and italic text'

    def test_alphabetic_marker_with_braces(self):
        """Test extraction with brace-wrapped terms (skill lists)."""
        entry = r'\itemLL {PyTorch} and {JAX}/{Equinox}'
        result = extract_itemize_entry(entry, LaTeXPatterns.ITEM_ALPHABETIC)

        assert result['marker'] == 'itemLL'
        assert result['latex_raw'] == r'{PyTorch} and {JAX}/{Equinox}'
        assert result['plaintext'] == 'PyTorch and JAX/Equinox'

    def test_alphabetic_marker_multiline(self):
        """Test extraction with multiline content."""
        entry = r'''\itemi \textbf{Developed pipeline}
        across multiple lines with
        indentation'''
        result = extract_itemize_entry(entry, LaTeXPatterns.ITEM_ALPHABETIC)

        assert result['marker'] == 'itemi'
        assert 'Developed pipeline' in result['latex_raw']
        assert 'multiple lines' in result['latex_raw']
        assert 'Developed pipeline' in result['plaintext']
        assert 'multiple lines' in result['plaintext']

    def test_bracketed_marker_with_icon(self):
        """Test extraction with bracketed marker containing icon."""
        entry = r'\item[\faIcon] Text with icon'
        result = extract_itemize_entry(entry, LaTeXPatterns.ITEM_BRACKETED)

        assert result['marker'] == r'item[\faIcon]'
        assert result['latex_raw'] == 'Text with icon'
        assert result['plaintext'] == 'Text with icon'

    def test_bracketed_marker_with_dash(self):
        """Test extraction with bracketed marker containing dash."""
        entry = r'\item[--] {PostgreSQL} database'
        result = extract_itemize_entry(entry, LaTeXPatterns.ITEM_BRACKETED)

        assert result['marker'] == 'item[--]'
        assert result['latex_raw'] == r'{PostgreSQL} database'
        assert result['plaintext'] == 'PostgreSQL database'

    def test_bracketed_marker_empty(self):
        """Test extraction with empty bracketed marker."""
        entry = r'\item[] Content without icon'
        result = extract_itemize_entry(entry, LaTeXPatterns.ITEM_BRACKETED)

        assert result['marker'] == 'item[]'
        assert result['latex_raw'] == 'Content without icon'
        assert result['plaintext'] == 'Content without icon'

    def test_any_pattern_alphabetic(self):
        """Test ITEM_ANY pattern with alphabetic marker."""
        entry = r'\itemi Content'
        result = extract_itemize_entry(entry, LaTeXPatterns.ITEM_ANY)

        assert result['marker'] == 'itemi'
        assert result['latex_raw'] == 'Content'
        assert result['plaintext'] == 'Content'

    def test_any_pattern_bracketed(self):
        """Test ITEM_ANY pattern with bracketed marker."""
        entry = r'\item[\faIcon] Content'
        result = extract_itemize_entry(entry, LaTeXPatterns.ITEM_ANY)

        assert result['marker'] == r'item[\faIcon]'
        assert result['latex_raw'] == 'Content'
        assert result['plaintext'] == 'Content'

    def test_special_characters_in_content(self):
        """Test extraction with special LaTeX characters (%, $, &)."""
        entry = r'\itemi \textbf{Unlocked 40\% gain} with \$500 cost'
        result = extract_itemize_entry(entry, LaTeXPatterns.ITEM_ALPHABETIC)

        assert result['marker'] == 'itemi'
        assert r'40\%' in result['latex_raw']
        assert r'\$500' in result['latex_raw']
        # Plaintext should preserve these (to_plaintext handles escape sequences)
        assert '40' in result['plaintext']
        assert '500' in result['plaintext']

    def test_nested_braces(self):
        """Test extraction with nested brace structures."""
        entry = r'\itemii Text with {outer {nested} structure}'
        result = extract_itemize_entry(entry, LaTeXPatterns.ITEM_ALPHABETIC)

        assert result['marker'] == 'itemii'
        assert 'outer {nested} structure' in result['latex_raw']

    def test_commands_stripped_in_plaintext(self):
        """Test that LaTeX commands are stripped in plaintext field."""
        entry = r'\itemi \centering \textbf{Bold}\par \vspace{10pt} text'
        result = extract_itemize_entry(entry, LaTeXPatterns.ITEM_ALPHABETIC)

        assert result['marker'] == 'itemi'
        # latex_raw preserves commands
        assert r'\textbf{Bold}' in result['latex_raw']
        assert r'\centering' in result['latex_raw']
        # plaintext strips all commands
        assert 'Bold' in result['plaintext']
        assert 'text' in result['plaintext']
        assert '\\textbf' not in result['plaintext']
        assert '\\centering' not in result['plaintext']
        assert '\\vspace' not in result['plaintext']

    def test_error_no_marker_found(self):
        """Test that ValueError is raised when no marker matches."""
        entry = r'Text without any marker'
        with pytest.raises(ValueError, match="No marker found"):
            extract_itemize_entry(entry, LaTeXPatterns.ITEM_ALPHABETIC)

    def test_error_wrong_pattern_type(self):
        """Test that ValueError is raised when pattern type doesn't match."""
        entry = r'\itemi Content'
        # Try to match with ITEM_BRACKETED pattern (should fail)
        with pytest.raises(ValueError, match="No marker found"):
            extract_itemize_entry(entry, LaTeXPatterns.ITEM_BRACKETED)

    def test_whitespace_handling(self):
        """Test that leading/trailing whitespace is handled correctly."""
        entry = '  \n  \\itemi   \n  Content with spaces  \n  '
        result = extract_itemize_entry(entry, LaTeXPatterns.ITEM_ALPHABETIC)

        assert result['marker'] == 'itemi'
        assert result['latex_raw'] == 'Content with spaces'
        assert result['plaintext'] == 'Content with spaces'

    def test_empty_content(self):
        """Test extraction with marker but no content."""
        entry = r'\itemi'
        result = extract_itemize_entry(entry, LaTeXPatterns.ITEM_ALPHABETIC)

        assert result['marker'] == 'itemi'
        assert result['latex_raw'] == ''
        assert result['plaintext'] == ''

    def test_content_with_linebreaks(self):
        """Test extraction with LaTeX line break commands."""
        entry = r'\itemi First line\\Second line\\Third line'
        result = extract_itemize_entry(entry, LaTeXPatterns.ITEM_ALPHABETIC)

        assert result['marker'] == 'itemi'
        assert r'First line\\Second line\\Third line' in result['latex_raw']
        # Plaintext handling of \\ depends on to_plaintext implementation
        assert 'First line' in result['plaintext']
        assert 'Second line' in result['plaintext']


class TestSplitItemizeEntries:
    """Tests for split_itemize_entries function."""

    def test_single_entry(self):
        """Test splitting with single entry."""
        content = r'\itemi Single entry'
        result = split_itemize_entries(content, LaTeXPatterns.ITEM_ALPHABETIC)

        assert len(result) == 1
        assert result[0] == r'\itemi Single entry'

    def test_multiple_entries(self):
        """Test splitting multiple entries."""
        content = r'\itemi First\itemi Second\itemi Third'
        result = split_itemize_entries(content, LaTeXPatterns.ITEM_ALPHABETIC)

        assert len(result) == 3
        assert result[0] == r'\itemi First'
        assert result[1] == r'\itemi Second'
        assert result[2] == r'\itemi Third'

    def test_multiline_entries(self):
        """Test splitting with multiline content."""
        content = r'''\itemi First line
        continues here
        \itemi Second entry'''
        result = split_itemize_entries(content, LaTeXPatterns.ITEM_ALPHABETIC)

        assert len(result) == 2
        assert 'First line' in result[0]
        assert 'continues here' in result[0]
        assert r'\itemi Second entry' in result[1]

    def test_bracketed_markers(self):
        """Test splitting with bracketed markers."""
        content = r'\item[\faIcon] First\item[--] Second\item[] Third'
        result = split_itemize_entries(content, LaTeXPatterns.ITEM_BRACKETED)

        assert len(result) == 3
        assert r'\item[\faIcon] First' in result[0]
        assert r'\item[--] Second' in result[1]
        assert r'\item[] Third' in result[2]

    def test_empty_content(self):
        """Test with empty content."""
        result = split_itemize_entries('', LaTeXPatterns.ITEM_ALPHABETIC)
        assert result == []

    def test_no_markers(self):
        """Test content with no matching markers."""
        content = 'Some text without markers'
        result = split_itemize_entries(content, LaTeXPatterns.ITEM_ALPHABETIC)
        assert result == []

    def test_mixed_markers_with_any_pattern(self):
        """Test ITEM_ANY pattern with mixed marker types."""
        content = r'\itemi First\item[--] Second\itemLL Third'
        result = split_itemize_entries(content, LaTeXPatterns.ITEM_ANY)

        assert len(result) == 3
        assert r'\itemi First' in result[0]
        assert r'\item[--] Second' in result[1]
        assert r'\itemLL Third' in result[2]

    def test_entries_with_formatting(self):
        """Test splitting entries that contain LaTeX formatting."""
        content = r'\itemi \textbf{Bold} text\itemi {Braces} content'
        result = split_itemize_entries(content, LaTeXPatterns.ITEM_ALPHABETIC)

        assert len(result) == 2
        assert r'\textbf{Bold}' in result[0]
        assert r'{Braces}' in result[1]

    def test_entries_with_whitespace_variation(self):
        """Test that entries are properly trimmed."""
        content = '  \n  \\itemi   First  \n\n  \\itemi  Second  '
        result = split_itemize_entries(content, LaTeXPatterns.ITEM_ALPHABETIC)

        assert len(result) == 2
        # Each entry should be trimmed
        assert result[0].startswith(r'\itemi')
        assert result[1].startswith(r'\itemi')


class TestParseItemizeContent:
    """Tests for parse_itemize_content function."""

    def test_simple_entries(self):
        """Test parsing simple entries without formatting."""
        content = r'\itemi First entry\itemi Second entry\itemi Third entry'
        entries = parse_itemize_content(content, LaTeXPatterns.ITEM_ALPHABETIC)

        assert len(entries) == 3
        assert entries[0]['marker'] == 'itemi'
        assert entries[0]['plaintext'] == 'First entry'
        assert entries[1]['plaintext'] == 'Second entry'
        assert entries[2]['plaintext'] == 'Third entry'

    def test_entries_with_formatting(self):
        """Test parsing entries with LaTeX formatting."""
        content = r'\itemi \textbf{Bold} text\itemi \textit{Italic} content'
        entries = parse_itemize_content(content, LaTeXPatterns.ITEM_ALPHABETIC)

        assert len(entries) == 2
        assert entries[0]['latex_raw'] == r'\textbf{Bold} text'
        assert entries[0]['plaintext'] == 'Bold text'
        assert entries[1]['latex_raw'] == r'\textit{Italic} content'
        assert entries[1]['plaintext'] == 'Italic content'

    def test_multiline_entries(self):
        """Test parsing multiline entries."""
        content = r'''\itemi First entry
        spanning multiple
        lines
        \itemi Second entry'''
        entries = parse_itemize_content(content, LaTeXPatterns.ITEM_ALPHABETIC)

        assert len(entries) == 2
        assert 'spanning multiple' in entries[0]['plaintext']
        assert 'lines' in entries[0]['plaintext']

    def test_bracketed_markers(self):
        """Test parsing entries with bracketed markers."""
        content = r'\item[\faDatabase] SQL\item[\faCode] Python'
        entries = parse_itemize_content(content, LaTeXPatterns.ITEM_BRACKETED)

        assert len(entries) == 2
        assert entries[0]['marker'] == r'item[\faDatabase]'
        assert entries[0]['plaintext'] == 'SQL'
        assert entries[1]['marker'] == r'item[\faCode]'
        assert entries[1]['plaintext'] == 'Python'

    def test_mixed_markers_with_any_pattern(self):
        """Test parsing mixed marker types with ITEM_ANY."""
        content = r'\itemi First\item[--] Second\itemLL Third'
        entries = parse_itemize_content(content, LaTeXPatterns.ITEM_ANY)

        assert len(entries) == 3
        assert entries[0]['marker'] == 'itemi'
        assert entries[1]['marker'] == 'item[--]'
        assert entries[2]['marker'] == 'itemLL'

    def test_empty_content(self):
        """Test parsing empty content."""
        entries = parse_itemize_content('', LaTeXPatterns.ITEM_ALPHABETIC)
        assert entries == []

    def test_no_markers(self):
        """Test content without markers."""
        content = 'Just plain text without markers'
        entries = parse_itemize_content(content, LaTeXPatterns.ITEM_ALPHABETIC)
        assert entries == []

    def test_entries_with_special_characters(self):
        """Test parsing entries with special LaTeX characters."""
        content = r'\itemi Improved by 40\% using \$1M budget'
        entries = parse_itemize_content(content, LaTeXPatterns.ITEM_ALPHABETIC)

        assert len(entries) == 1
        assert '40' in entries[0]['plaintext']
        assert '1M' in entries[0]['plaintext']


class TestExtractEnvironment:
    """Tests for extract_environment function."""

    def test_simple_environment_no_params(self):
        """Test extracting environment without parameters."""
        text = r'''\begin{itemize}
        Some content here
        \end{itemize}'''

        params, content, begin_pos, end_pos = extract_environment(
            text, "itemize"
        )

        assert params == []
        assert 'Some content here' in content
        assert begin_pos > 0
        assert end_pos > begin_pos

    def test_environment_with_params(self):
        """Test extracting environment with parameters."""
        text = r'''\begin{itemizeAcademic}{Company Name}{Job Title}{Location}{2020-2023}
        Content without params
        \end{itemizeAcademic}'''

        params, content, _, _ = extract_environment(
            text, "itemizeAcademic", num_params=4
        )

        assert len(params) == 4
        assert params[0] == 'Company Name'
        assert params[1] == 'Job Title'
        assert params[2] == 'Location'
        assert params[3] == '2020-2023'
        assert 'Content without params' in content
        # Params should be stripped from content
        assert 'Company Name' not in content
        assert 'Job Title' not in content

    def test_params_with_nested_braces(self):
        """Test parameters containing nested braces."""
        text = r'''\begin{env}{Simple}{Complex {with \textit{nested}} text}{Another}
        Inner content
        \end{env}'''

        params, content, _, _ = extract_environment(
            text, "env", num_params=3
        )

        assert params[0] == 'Simple'
        assert params[1] == r'Complex {with \textit{nested}} text'
        assert params[2] == 'Another'
        assert 'Inner content' in content

    def test_environment_with_special_chars(self):
        """Test environment name with special regex chars."""
        text = r'\begin{textblock*}{width}Content\end{textblock*}'

        params, content, _, _ = extract_environment(
            text, "textblock*", num_params=1
        )

        assert len(params) == 1
        assert params[0] == 'width'
        assert content == 'Content'

    def test_multiline_content(self):
        """Test environment with multiline content."""
        text = r'''\begin{itemize}
        Line 1
        Line 2
        Line 3
        \end{itemize}'''

        _, content, _, _ = extract_environment(text, "itemize")

        assert 'Line 1' in content
        assert 'Line 2' in content
        assert 'Line 3' in content

    def test_empty_content_no_params(self):
        """Test environment with empty content and no params."""
        text = r'\begin{itemize}\end{itemize}'

        params, content, _, _ = extract_environment(text, "itemize")

        assert params == []
        assert content == ''

    def test_empty_content_with_params(self):
        """Test environment with params but no additional content."""
        text = r'\begin{env}{param1}{param2}\end{env}'

        params, content, _, _ = extract_environment(text, "env", num_params=2)

        assert len(params) == 2
        assert params[0] == 'param1'
        assert params[1] == 'param2'
        assert content == ''

    def test_start_position(self):
        """Test using start_pos to skip initial text."""
        text = r'''Preamble text
        \begin{itemize}{param}
        Content
        \end{itemize}'''

        params, content, _, _ = extract_environment(
            text, "itemize", num_params=1, start_pos=0
        )

        assert len(params) == 1
        assert params[0] == 'param'
        assert 'Content' in content

    def test_position_tracking(self):
        """Test that position values are correctly returned."""
        text = r'\begin{itemize}{arg}content\end{itemize}'

        _, _, begin_pos, end_pos = extract_environment(
            text, "itemize", num_params=1
        )

        # begin_pos should be after \begin{itemize}
        assert '{arg}' in text[begin_pos:end_pos]
        # end_pos should be at \end{itemize}
        assert text[end_pos:].startswith(r'\end{itemize}')

    def test_environment_not_found_error(self):
        """Test that ValueError is raised when environment not found."""
        text = r'Some text without the environment'

        with pytest.raises(ValueError, match=r"No \\begin\{itemize\} found"):
            extract_environment(text, "itemize")

    def test_unmatched_environment_error(self):
        """Test that ValueError is raised for unmatched environment."""
        text = r'\begin{itemize}{param}Content'

        with pytest.raises(ValueError, match="Unmatched"):
            extract_environment(text, "itemize", num_params=1)

    def test_buggy_parameter_combination_error(self):
        """Test that NotImplementedError is raised for buggy parameter combination."""
        text = r'''\begin{itemizeAcademic}{Company}{Title}{Location}{Dates}
        Content
        \end{itemizeAcademic}'''

        # Should raise NotImplementedError when both include_env_command_in_positions=True
        # and num_params > 0
        with pytest.raises(NotImplementedError, match="Parameter extraction does not work correctly"):
            extract_environment(text, "itemizeAcademic", num_params=4,
                              include_env_command_in_positions=True)

        # Should also raise for optional params
        with pytest.raises(NotImplementedError, match="Parameter extraction does not work correctly"):
            extract_environment(text, "itemizeAcademic", num_optional_params=1,
                              include_env_command_in_positions=True)

        # Should also raise when both types of params present
        with pytest.raises(NotImplementedError, match="Parameter extraction does not work correctly"):
            extract_environment(text, "itemizeAcademic", num_params=3, num_optional_params=1,
                              include_env_command_in_positions=True)

        # Should NOT raise when include_env_command_in_positions=False (the default)
        params, content, _, _ = extract_environment(text, "itemizeAcademic", num_params=4,
                                                    include_env_command_in_positions=False)
        assert len(params) == 4
        assert params[0] == 'Company'


class TestExtractSequentialParams:
    """Tests for extract_sequential_params function."""

    def test_simple_params(self):
        """Test extracting simple parameters without nesting."""
        latex = r'{Company}{Title}{Location}{Dates}'
        params = extract_sequential_params(latex, 0, 4)

        assert len(params) == 4
        assert params[0] == 'Company'
        assert params[1] == 'Title'
        assert params[2] == 'Location'
        assert params[3] == 'Dates'

    def test_params_with_nested_braces(self):
        """Test extracting parameters with nested braces."""
        latex = r'{Simple}{Title {with \textit{nested}} content}{Location}'
        params = extract_sequential_params(latex, 0, 3)

        assert len(params) == 3
        assert params[0] == 'Simple'
        assert params[1] == r'Title {with \textit{nested}} content'
        assert params[2] == 'Location'

    def test_params_with_latex_commands(self):
        """Test parameters containing LaTeX commands."""
        latex = r'{\textbf{Bold}}{\textit{Italic}}{\color{red}{Colored}}'
        params = extract_sequential_params(latex, 0, 3)

        assert len(params) == 3
        assert params[0] == r'\textbf{Bold}'
        assert params[1] == r'\textit{Italic}'
        assert params[2] == r'\color{red}{Colored}'

    def test_params_with_whitespace(self):
        """Test parameters with various whitespace."""
        latex = '  {First}  \n  {Second}  \t  {Third}  '
        params = extract_sequential_params(latex, 0, 3)

        assert len(params) == 3
        assert params[0] == 'First'
        assert params[1] == 'Second'
        assert params[2] == 'Third'

    def test_start_position_offset(self):
        """Test extracting params starting from non-zero position."""
        latex = r'Preamble {First}{Second}{Third}'
        params = extract_sequential_params(latex, 9, 3)

        assert len(params) == 3
        assert params[0] == 'First'
        assert params[1] == 'Second'

    def test_fewer_params_than_requested(self):
        """Test when fewer params available than requested."""
        latex = r'{First}{Second}'
        params = extract_sequential_params(latex, 0, 5)

        assert len(params) == 2
        assert params[0] == 'First'
        assert params[1] == 'Second'

    def test_empty_params(self):
        """Test extracting empty parameters."""
        latex = r'{}{Non-empty}{}'
        params = extract_sequential_params(latex, 0, 3)

        assert len(params) == 3
        assert params[0] == ''
        assert params[1] == 'Non-empty'
        assert params[2] == ''


class TestExtractEnvironmentContent:
    """Tests for extract_environment_content function."""

    def test_simple_environment(self):
        """Test extracting content from simple environment."""
        text = r'\begin{itemize} content here \end{itemize}'
        content, begin_pos, end_pos = extract_environment_content(text, 'itemize')

        assert content == ' content here '
        assert text[begin_pos:end_pos] == ' content here '

    def test_nested_same_environment(self):
        """Test nested environments of the same type."""
        text = r'\begin{itemize} outer \begin{itemize} inner \end{itemize} outer \end{itemize}'
        content, _, _ = extract_environment_content(text, 'itemize')

        assert content == r' outer \begin{itemize} inner \end{itemize} outer '

    def test_multiline_content(self):
        """Test environment with multiline content."""
        text = r'''\begin{itemizeMain}
        Line 1
        Line 2
        \end{itemizeMain}'''
        content, _, _ = extract_environment_content(text, 'itemizeMain')

        assert 'Line 1' in content
        assert 'Line 2' in content

    def test_environment_with_special_chars(self):
        """Test environment name with special regex chars (e.g., *)."""
        text = r'\begin{textblock*} content \end{textblock*}'
        content, _, _ = extract_environment_content(text, 'textblock*')

        assert content == ' content '

    def test_start_position(self):
        """Test extracting from non-zero start position."""
        text = r'Preamble \begin{itemize} content \end{itemize}'
        content, _, _ = extract_environment_content(text, 'itemize', start_pos=9)

        assert content == ' content '

    def test_position_values(self):
        """Test that position values are correct."""
        text = r'\begin{itemize}content\end{itemize}'
        content, begin_pos, end_pos = extract_environment_content(text, 'itemize')

        assert text[begin_pos:end_pos] == 'content'
        assert text[:begin_pos] == r'\begin{itemize}'
        assert text[end_pos:] == r'\end{itemize}'

    def test_environment_not_found(self):
        """Test ValueError when environment not found."""
        text = r'No environment here'
        with pytest.raises(ValueError, match=r"No \\begin\{itemize\} found"):
            extract_environment_content(text, 'itemize')

    def test_unmatched_begin(self):
        """Test ValueError for unmatched begin."""
        text = r'\begin{itemize} no end tag'
        with pytest.raises(ValueError, match="Unmatched"):
            extract_environment_content(text, 'itemize')

    def test_empty_content(self):
        """Test environment with empty content."""
        text = r'\begin{itemize}\end{itemize}'
        content, _, _ = extract_environment_content(text, 'itemize')

        assert content == ''


class TestToPlaintext:
    """Tests for to_plaintext function."""

    def test_simple_text(self):
        """Test plaintext with no LaTeX commands."""
        result = to_plaintext('Simple plain text')
        assert result == 'Simple plain text'

    def test_textbf_unwrapping(self):
        """Test unwrapping textbf command."""
        result = to_plaintext(r'\textbf{Bold text}')
        assert result == 'Bold text'
        assert '\\textbf' not in result

    def test_textit_unwrapping(self):
        """Test unwrapping textit command."""
        result = to_plaintext(r'\textit{Italic text}')
        assert result == 'Italic text'

    def test_multiple_formatting(self):
        """Test mixed formatting commands."""
        result = to_plaintext(r'\textbf{Bold} and \textit{italic} text')
        assert result == 'Bold and italic text'

    def test_color_commands(self):
        """Test removing color commands."""
        result = to_plaintext(r'\color{red}{Colored} text')
        assert result == 'Colored text'
        assert '\\color' not in result

    def test_spacing_commands(self):
        """Test removing spacing commands."""
        result = to_plaintext(r'Text \vspace{10pt} more \hspace{5pt} text')
        assert 'Text' in result
        assert 'more' in result
        assert 'text' in result
        assert '\\vspace' not in result
        assert '\\hspace' not in result

    def test_centering_and_par(self):
        """Test removing centering and par commands."""
        result = to_plaintext(r'\centering Some text\par')
        assert result == 'Some text'

    def test_line_breaks(self):
        """Test converting line breaks to spaces."""
        result = to_plaintext(r'Line one\\Line two')
        assert 'Line one' in result
        assert 'Line two' in result
        assert '\\\\' not in result

    def test_grouping_braces(self):
        """Test removing grouping braces."""
        result = to_plaintext('{PyTorch} and {JAX}')
        assert result == 'PyTorch and JAX'

    def test_escaped_braces(self):
        """Test preserving escaped braces as literals."""
        result = to_plaintext(r'Use \{ and \} for braces')
        assert result == 'Use { and } for braces'

    def test_nested_commands(self):
        """Test nested formatting commands."""
        result = to_plaintext(r'\textbf{\textit{Nested}} text')
        assert result == 'Nested text'

    def test_complex_example(self):
        """Test complex real-world example."""
        latex = r'\centering \textbf{Bold text} \par with {braces}'
        result = to_plaintext(latex)
        assert result == 'Bold text with braces'
        assert '\\' not in result

    def test_empty_string(self):
        """Test empty string."""
        result = to_plaintext('')
        assert result == ''

    def test_whitespace_cleanup(self):
        """Test that extra whitespace is cleaned up."""
        result = to_plaintext('Text   with    extra   spaces')
        assert result == 'Text with extra spaces'


class TestToLatex:
    """Tests for to_latex function."""

    # Tests for current functionality (ampersand escaping)
    def test_escape_ampersand(self):
        """Test escaping single ampersand."""
        result = to_latex('AI & Machine Learning')
        assert result == r'AI \& Machine Learning'

    def test_multiple_ampersands(self):
        """Test escaping multiple ampersands."""
        result = to_latex('A & B & C')
        assert result == r'A \& B \& C'

    def test_ampersand_only(self):
        """Test escaping ampersand alone."""
        result = to_latex('&')
        assert result == r'\&'

    def test_empty_string(self):
        """Test empty string returns empty string."""
        result = to_latex('')
        assert result == ''

    def test_no_special_chars(self):
        """Test text without special characters passes through unchanged."""
        result = to_latex('Hello World')
        assert result == 'Hello World'

    # Tests for future functionality (marked xfail)
    @pytest.mark.xfail(reason="Percent escaping not yet implemented")
    def test_escape_percent(self):
        """Test escaping percent sign."""
        result = to_latex('50% improvement')
        assert result == r'50\% improvement'

    @pytest.mark.xfail(reason="Dollar sign escaping not yet implemented")
    def test_escape_dollar(self):
        """Test escaping dollar sign."""
        result = to_latex('Cost: $100')
        assert result == r'Cost: \$100'

    @pytest.mark.xfail(reason="Hash escaping not yet implemented")
    def test_escape_hash(self):
        """Test escaping hash/pound sign."""
        result = to_latex('Issue #123')
        assert result == r'Issue \#123'

    @pytest.mark.xfail(reason="Underscore escaping not yet implemented")
    def test_escape_underscore(self):
        """Test escaping underscore."""
        result = to_latex('variable_name')
        assert result == r'variable\_name'

    @pytest.mark.xfail(reason="Brace escaping not yet implemented")
    def test_escape_braces(self):
        """Test escaping literal braces."""
        result = to_latex('Use { and } for grouping')
        assert result == r'Use \{ and \} for grouping'

    @pytest.mark.xfail(reason="Tilde escaping not yet implemented")
    def test_escape_tilde(self):
        """Test escaping tilde."""
        result = to_latex('~username')
        # Could be \textasciitilde or \~{}
        assert r'\textasciitilde' in result or r'\~{}' in result

    @pytest.mark.xfail(reason="Caret escaping not yet implemented")
    def test_escape_caret(self):
        """Test escaping caret."""
        result = to_latex('x^2')
        # Could be \textasciicircum or \^{}
        assert r'\textasciicircum' in result or r'\^{}' in result

    @pytest.mark.xfail(reason="Backslash escaping not yet implemented")
    def test_escape_backslash(self):
        """Test escaping backslash."""
        result = to_latex(r'C:\path\to\file')
        assert r'\textbackslash' in result

    @pytest.mark.xfail(reason="Multiple special character escaping not yet implemented")
    def test_multiple_special_chars(self):
        """Test escaping multiple different special characters."""
        result = to_latex('50% of $100 & #1 rank')
        assert result == r'50\% of \$100 \& \#1 rank'

    @pytest.mark.xfail(reason="Line break conversion not yet implemented")
    def test_line_breaks(self):
        """Test converting line breaks to LaTeX."""
        result = to_latex('Line one\nLine two')
        # Should convert to \\ or \par
        assert r'\\' in result or r'\par' in result

    @pytest.mark.xfail(reason="Text formatting conversion not yet implemented")
    def test_bold_formatting(self):
        """Test converting bold markdown to LaTeX."""
        result = to_latex('This is **bold** text')
        assert r'\textbf{bold}' in result

    @pytest.mark.xfail(reason="Text formatting conversion not yet implemented")
    def test_italic_formatting(self):
        """Test converting italic markdown to LaTeX."""
        result = to_latex('This is *italic* text')
        assert r'\textit{italic}' in result


class TestExtractBraceArguments:
    """Tests for extract_brace_arguments function."""

    def test_simple_arguments(self):
        """Test extracting simple arguments."""
        latex = r'\command{arg1}{arg2}{arg3}'
        args = extract_brace_arguments(latex)

        assert len(args) == 3
        assert args[0] == 'arg1'
        assert args[1] == 'arg2'
        assert args[2] == 'arg3'

    def test_arguments_with_latex_commands(self):
        """Test arguments containing LaTeX commands."""
        latex = r'\leftgrad{\leftbarwidth}{60pt}{0.4\paperheight}'
        args = extract_brace_arguments(latex)

        assert len(args) == 3
        assert args[0] == r'\leftbarwidth'
        assert args[1] == '60pt'
        assert args[2] == r'0.4\paperheight'

    def test_no_arguments(self):
        """Test with no brace arguments."""
        latex = r'\command without braces'
        args = extract_brace_arguments(latex)
        assert args == []

    def test_empty_arguments(self):
        """Test with empty brace arguments.

        Note: extract_brace_arguments uses simple regex that doesn't match
        empty braces {}. For empty params, use extract_sequential_params instead.
        """
        latex = r'\command{}{non-empty}{}'
        args = extract_brace_arguments(latex)

        # Simple pattern only matches non-empty braces
        assert len(args) == 1
        assert args[0] == 'non-empty'


class TestReplaceCommand:
    """Tests for replace_command function."""

    def test_unwrap_textbf(self):
        """Test unwrapping textbf command (no prefix/suffix)."""
        result = replace_command(r'\textbf{bold text}', 'textbf')
        assert result == 'bold text'

    def test_multiple_occurrences(self):
        """Test unwrapping multiple occurrences."""
        result = replace_command(r'\textbf{first} and \textbf{second}', 'textbf')
        assert result == 'first and second'

    def test_unwrap_textit(self):
        """Test unwrapping textit command."""
        result = replace_command(r'Normal \textit{italic} text', 'textit')
        assert result == 'Normal italic text'

    def test_no_match(self):
        """Test text without the specified command."""
        result = replace_command(r'\textbf{bold}', 'textit')
        assert result == r'\textbf{bold}'

    def test_with_markdown_bold(self):
        """Test replacing with markdown bold formatting."""
        result = replace_command(r'\textbf{bold}', 'textbf', '**', '**')
        assert result == '**bold**'

    def test_with_markdown_italic(self):
        """Test replacing with markdown italic formatting."""
        result = replace_command(r'\textit{italic}', 'textit', '*', '*')
        assert result == '*italic*'

    def test_nested_braces_with_markdown(self):
        """Test nested braces with markdown replacement."""
        result = replace_command(r'\textbf{text \texttt{nested} more}', 'textbf', '**', '**')
        assert result == r'**text \texttt{nested} more**'


class TestStripFormatting:
    """Tests for strip_formatting function."""

    def test_strip_centering(self):
        """Test stripping centering command."""
        result = strip_formatting(r'\centering Some text', ['centering'])
        assert result == 'Some text'

    def test_strip_multiple_commands(self):
        """Test stripping multiple commands."""
        result = strip_formatting(r'\centering Text \par', ['centering', 'par'])
        assert 'Text' in result

    def test_strip_with_whitespace(self):
        """Test that trailing whitespace is removed."""
        result = strip_formatting(r'\centering   Text', ['centering'])
        assert result == 'Text'

    def test_no_commands_to_strip(self):
        """Test text without specified commands."""
        result = strip_formatting(r'Plain text', ['centering', 'par'])
        assert result == 'Plain text'


class TestExtractAllEnvironments:
    """Tests for extract_all_environments function."""

    def test_single_environment_match(self):
        """Test extracting single environment by exact name."""
        text = r'''\begin{itemize}
        \item First
        \end{itemize}'''

        results = extract_all_environments(text, 'itemize')

        assert len(results) == 1
        env_name, params, content, _, _ = results[0]
        assert env_name == 'itemize'
        assert params == []
        assert r'\item First' in content

    def test_multiple_environments_same_type(self):
        """Test extracting multiple environments of same type."""
        text = r'''\begin{itemize}
        Content 1
        \end{itemize}
        Some text
        \begin{itemize}
        Content 2
        \end{itemize}'''

        results = extract_all_environments(text, 'itemize', include_env_command_in_positions=False)

        assert len(results) == 2
        assert results[0][2].strip() == 'Content 1'
        assert results[1][2].strip() == 'Content 2'

    def test_pattern_matching_multiple_env_names(self):
        """Test using regex pattern to match multiple environment names."""
        text = r'''\begin{itemizeAProject}
        Project content
        \end{itemizeAProject}
        \begin{itemizeKeyProject}
        Key project content
        \end{itemizeKeyProject}
        \begin{itemizeMain}
        Main content
        \end{itemizeMain}'''

        results = extract_all_environments(text, r'itemize.*Project')

        assert len(results) == 2
        assert results[0][0] == 'itemizeAProject'
        assert results[1][0] == 'itemizeKeyProject'
        assert 'Project content' in results[0][2]
        assert 'Key project content' in results[1][2]

    def test_environments_with_parameters(self):
        """Test extracting environments with mandatory parameters."""
        text = r'''\begin{itemizeAcademic}{CompanyA}{TitleA}{LocA}{DatesA}
        Content A
        \end{itemizeAcademic}
        \begin{itemizeAcademic}{CompanyB}{TitleB}{LocB}{DatesB}
        Content B
        \end{itemizeAcademic}'''

        results = extract_all_environments(text, 'itemizeAcademic', num_params=4,
                                          include_env_command_in_positions=False)

        assert len(results) == 2

        env_name, params, content, _, _ = results[0]
        assert env_name == 'itemizeAcademic'
        assert len(params) == 4
        assert params[0] == 'CompanyA'
        assert params[1] == 'TitleA'
        assert 'Content A' in content

        env_name, params, content, _, _ = results[1]
        assert params[0] == 'CompanyB'
        assert params[1] == 'TitleB'
        assert 'Content B' in content

    def test_nested_environments_not_double_counted(self):
        """Test that nested environments are properly handled."""
        text = r'''\begin{itemize}
        Outer
        \begin{itemize}
        Inner
        \end{itemize}
        Outer again
        \end{itemize}'''

        results = extract_all_environments(text, 'itemize')

        # Should find 2 environments (outer and inner)
        assert len(results) == 2
        # First one found is the outer
        assert 'Outer' in results[0][2]
        assert 'Inner' in results[0][2]  # Contains nested content
        # Second is the inner
        assert 'Inner' in results[1][2]
        assert 'Outer again' not in results[1][2]

    def test_position_tracking_with_include_env_command(self):
        """Test position tracking includes environment commands."""
        text = r'\begin{itemize}\item Content\end{itemize}'

        results = extract_all_environments(text, 'itemize', include_env_command_in_positions=True)

        assert len(results) == 1
        _, _, content, begin_pos, end_pos = results[0]

        # Content should include \begin and \end commands
        assert text[begin_pos:end_pos].startswith(r'\begin{itemize}')
        assert text[begin_pos:end_pos].endswith(r'\end{itemize}')

    def test_position_tracking_without_include_env_command(self):
        """Test position tracking excludes environment commands."""
        text = r'\begin{itemize}\item Content\end{itemize}'

        results = extract_all_environments(text, 'itemize', include_env_command_in_positions=False)

        assert len(results) == 1
        _, _, content, begin_pos, end_pos = results[0]

        # Content should NOT include \begin and \end commands
        assert not text[begin_pos:end_pos].startswith(r'\begin')
        assert not text[begin_pos:end_pos].endswith(r'\end')
        assert r'\item Content' in text[begin_pos:end_pos]

    def test_no_matching_environments(self):
        """Test when no environments match the pattern."""
        text = r'''\begin{itemize}
        Content
        \end{itemize}'''

        results = extract_all_environments(text, 'enumerate')

        assert results == []

    def test_pattern_with_special_regex_chars(self):
        """Test pattern with regex special characters."""
        text = r'''\begin{textblock*}
        Content
        \end{textblock*}'''

        # Need to escape * for regex
        results = extract_all_environments(text, r'textblock\*')

        assert len(results) == 1
        assert results[0][0] == 'textblock*'

    def test_complex_pattern_matching(self):
        """Test complex regex pattern for environment matching."""
        text = r'''\begin{itemizeA}
        A
        \end{itemizeA}
        \begin{itemizeB}
        B
        \end{itemizeB}
        \begin{itemizeC}
        C
        \end{itemizeC}
        \begin{other}
        Other
        \end{other}'''

        # Match itemize followed by single letter
        results = extract_all_environments(text, r'itemize[A-Z]')

        assert len(results) == 3
        assert results[0][0] == 'itemizeA'
        assert results[1][0] == 'itemizeB'
        assert results[2][0] == 'itemizeC'

    def test_empty_environments(self):
        """Test extracting empty environments."""
        text = r'''\begin{itemize}\end{itemize}
        \begin{itemize}\end{itemize}'''

        results = extract_all_environments(text, 'itemize', include_env_command_in_positions=False)

        assert len(results) == 2
        assert results[0][2] == ''
        assert results[1][2] == ''


class TestParseItemizeWithComplexMarkers:
    """Tests for parse_itemize_with_complex_markers function."""

    def test_simple_item_markers(self):
        """Test parsing simple item markers without brackets."""
        content = r'''\item First item
        \item Second item
        \item Third item'''

        entries = parse_itemize_with_complex_markers(content)

        assert len(entries) == 3
        assert entries[0]['marker'] == r'\item'
        assert entries[0]['plaintext'] == 'First item'
        assert entries[1]['plaintext'] == 'Second item'
        assert entries[2]['plaintext'] == 'Third item'

    def test_simple_bracketed_markers(self):
        """Test parsing simple bracketed markers."""
        content = r'''\item[--] First
        \item[>] Second
        \item[*] Third'''

        entries = parse_itemize_with_complex_markers(content)

        assert len(entries) == 3
        assert entries[0]['marker'] == r'\item[--]'
        assert entries[1]['marker'] == r'\item[>]'
        assert entries[2]['marker'] == r'\item[*]'

    def test_complex_nested_braces_in_marker(self):
        """Test parsing markers with nested braces."""
        content = r'''\item[\raisebox{-1pt}{>} 20,000] GPU-hours
        \item[\textbf{Bold}] Content with bold marker
        \item[{\color{red}{Red}}] Colored marker'''

        entries = parse_itemize_with_complex_markers(content)

        assert len(entries) == 3
        assert entries[0]['marker'] == r'\item[\raisebox{-1pt}{>} 20,000]'
        assert entries[0]['latex_raw'] == 'GPU-hours'
        assert entries[0]['plaintext'] == 'GPU-hours'

        assert entries[1]['marker'] == r'\item[\textbf{Bold}]'
        assert entries[1]['plaintext'] == 'Content with bold marker'

        assert entries[2]['marker'] == r'\item[{\color{red}{Red}}]'
        assert 'Colored marker' in entries[2]['plaintext']

    def test_deeply_nested_braces_in_marker(self):
        """Test markers with multiple levels of nesting."""
        content = r'''\item[\raisebox{-2pt}{\textbf{\color{blue}{Icon}}}] Content here'''

        entries = parse_itemize_with_complex_markers(content)

        assert len(entries) == 1
        assert entries[0]['marker'] == r'\item[\raisebox{-2pt}{\textbf{\color{blue}{Icon}}}]'
        assert entries[0]['plaintext'] == 'Content here'

    def test_multiline_entries(self):
        """Test parsing multiline item content."""
        content = r'''\item[--] First line
        continues here
        and here
        \item[>] Second entry'''

        entries = parse_itemize_with_complex_markers(content)

        assert len(entries) == 2
        assert 'First line' in entries[0]['plaintext']
        assert 'continues here' in entries[0]['plaintext']
        assert 'and here' in entries[0]['plaintext']
        assert entries[1]['plaintext'] == 'Second entry'

    def test_entries_with_latex_formatting(self):
        """Test that LaTeX formatting is preserved in latex_raw and stripped in plaintext."""
        content = r'''\item[--] \textbf{Bold} and \textit{italic}
        \item[>] {Braced} content'''

        entries = parse_itemize_with_complex_markers(content)

        assert len(entries) == 2
        assert r'\textbf{Bold}' in entries[0]['latex_raw']
        assert r'\textit{italic}' in entries[0]['latex_raw']
        assert 'Bold' in entries[0]['plaintext']
        assert 'italic' in entries[0]['plaintext']
        assert r'\textbf' not in entries[0]['plaintext']

    def test_mixed_marker_types(self):
        """Test mixing simple and complex markers."""
        content = r'''\item Simple
        \item[\raisebox{-1pt}{>}] Complex
        \item[--] Bracketed
        \item Another simple'''

        entries = parse_itemize_with_complex_markers(content)

        assert len(entries) == 4
        assert entries[0]['marker'] == r'\item'
        assert entries[1]['marker'] == r'\item[\raisebox{-1pt}{>}]'
        assert entries[2]['marker'] == r'\item[--]'
        assert entries[3]['marker'] == r'\item'

    def test_empty_content(self):
        """Test parsing empty content."""
        content = ''
        entries = parse_itemize_with_complex_markers(content)
        assert entries == []

    def test_no_items(self):
        """Test content without any item markers."""
        content = 'Just plain text without markers'
        entries = parse_itemize_with_complex_markers(content)
        assert entries == []

    def test_item_at_end(self):
        """Test item marker at end of content with no content after it."""
        content = r'''\item First
        \item'''

        entries = parse_itemize_with_complex_markers(content)

        assert len(entries) == 2
        assert entries[0]['plaintext'] == 'First'
        assert entries[1]['plaintext'] == ''

    def test_special_characters_in_content(self):
        """Test entries with special LaTeX characters."""
        content = r'''\item[>] Improved by 40\% with \$500 budget
        \item[--] Used {PyTorch} and {JAX}'''

        entries = parse_itemize_with_complex_markers(content)

        assert len(entries) == 2
        assert '40' in entries[0]['plaintext']
        assert '500' in entries[0]['plaintext']
        assert 'PyTorch' in entries[1]['plaintext']
        assert 'JAX' in entries[1]['plaintext']

    def test_unmatched_bracket_fallback(self):
        """Test fallback behavior when bracket matching fails."""
        # This is a pathological case - unmatched bracket
        content = r'''\item[ Unmatched bracket content
        \item Normal item'''

        entries = parse_itemize_with_complex_markers(content)

        # Should handle gracefully even with malformed input
        assert len(entries) >= 1
        # The exact behavior depends on implementation, but it shouldn't crash
