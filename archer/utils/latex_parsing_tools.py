"""
LaTeX Parsing Tools

Fundamental parsing utilities for extracting LaTeX structures.

Self-contained module with no project dependencies - designed for reusability.
All LaTeX patterns are defined as constants below for visibility and maintainability.
"""

import re
from dataclasses import dataclass
from typing import List, Tuple

from archer.utils.text_processing import extract_balanced_delimiters


@dataclass(frozen=True)
class LaTeXPatterns:
    """
    LaTeX pattern templates for parsing and manipulation.

    These are format string templates that accept command/environment names.
    Use .format() or f-strings to substitute the command name.
    """

    # Command patterns (use with .format(command=name))
    COMMAND_WITH_BRACES: str = (
        r"\\{command}\{{([^}}]+)\}}"  # Matches \cmd{content}, captures content
    )
    COMMAND_WITH_WHITESPACE: str = r"\\{command}\s*"  # Matches \cmd with trailing whitespace
    COMMAND_AT_END: str = r"\\{command}\s*$"  # Matches \cmd at end of string

    # Environment patterns (use with .format(env=name))
    BEGIN_ENV: str = r"\\begin\{{{env}\}}"  # Matches \begin{envname}
    END_ENV: str = r"\\end\{{{env}\}}"  # Matches \end{envname}
    BEGIN_ENV_PATTERN: str = (
        r"\\begin\{{({pattern})\}}"  # Matches \begin with pattern, captures env name
    )

    # Brace extraction patterns
    SIMPLE_BRACES: str = r"\{([^}]+)\}"  # Matches {content}, no nesting

    # Itemize marker patterns (use with named group (?P<marker>...))
    ITEM_ALPHABETIC: str = r"\\(?P<marker>item[A-Za-z]*)"  # Matches \itemi, \itemii, \itemLL, etc.
    ITEM_BRACKETED: str = r"\\(?P<marker>item\[[^\]]*\])"  # Matches \item[icon], \item[--], \item[]
    ITEM_ANY: str = r"\\(?P<marker>item(?:\[[^\]]*\])?[A-Za-z]*)"  # Matches any \item variant

    # Plaintext conversion patterns (for stripping LaTeX in to_plaintext())
    COLOR_WITH_TEXT: str = (
        r"\\color\{[^}]+\}\{([^}]*)\}"  # Matches \color{red}{text}, captures text
    )
    COLOR_STANDALONE: str = r"\\color\{[^}]+\}"  # Matches \color{red}, removes entirely
    SPACING_COMMANDS: str = r"\\[vh]space\{[^}]*\}"  # Matches \vspace{...} or \hspace{...}
    ANY_COMMAND_WITH_BRACES: str = r"\\[a-zA-Z]+\{[^}]*\}"  # Matches any \command{...}
    ANY_COMMAND_NO_BRACES: str = r"\\[a-zA-Z]+"  # Matches any \command


# Used only twice, might not be useful. Might replace it with other, more general function(s)
def extract_brace_arguments(latex_str: str) -> List[str]:
    """
    Extract all brace-delimited arguments from a LaTeX command (simple, no nesting).

    Given a command like \\command{arg1}{arg2}{arg3}, extracts ["arg1", "arg2", "arg3"].
    Does NOT handle nested braces - use extract_sequential_params() for that.

    Args:
        latex_str: LaTeX command string with brace arguments

    Returns:
        List of argument strings (content between braces)

    Example:
        >>> extract_brace_arguments("\\leftgrad{\\leftbarwidth}{60pt}{0.4\\paperheight}")
        ['\\leftbarwidth', '60pt', '0.4\\paperheight']
    """
    return re.findall(LaTeXPatterns.SIMPLE_BRACES, latex_str)


def extract_sequential_params(latex_str: str, start_pos: int, num_params: int) -> List[str]:
    """
    Extract N sequential brace-delimited parameters from a position, handling nested braces.

    Uses brace counting to correctly handle nested structures like {text {nested} more}.

    Args:
        latex_str: LaTeX source
        start_pos: Position to start searching
        num_params: Number of {...} parameters to extract

    Returns:
        List of extracted parameter values

    Example:
        >>> latex = (
        ...     "\\begin{itemizeAcademic}{Company}{Title {with \\textit{nested}}}{Location}{Dates}"
        ... )
        >>> extract_sequential_params(latex, 23, 4)  # Start after {itemizeAcademic}
        ['Company', 'Title {with \\textit{nested}}', 'Location', 'Dates']
    """
    params = []
    pos = start_pos

    for _ in range(num_params):
        # Find opening brace
        while pos < len(latex_str) and latex_str[pos] != "{":
            pos += 1

        if pos >= len(latex_str):
            break

        # Count braces to find matching close
        pos += 1  # Skip opening brace
        brace_count = 1
        param_start = pos

        while pos < len(latex_str) and brace_count > 0:
            if latex_str[pos] == "\\":
                pos += 2  # Skip escaped char
                continue
            elif latex_str[pos] == "{":
                brace_count += 1
            elif latex_str[pos] == "}":
                brace_count -= 1
            pos += 1

        if brace_count == 0:
            param_value = latex_str[param_start : pos - 1]
            params.append(param_value)

    return params


def extract_environment_content(
    text: str, env_name: str, start_pos: int = 0, include_env_command_in_positions: bool = False
) -> Tuple[str, int, int]:
    """
    Extract content from LaTeX environment, handling nested environments.

    Finds \\begin{env_name} and matching \\end{env_name}, correctly handling
    nested environments of the same name.

    Args:
        text: LaTeX text
        env_name: Environment name (e.g., 'itemize', 'itemizeMain', 'textblock*')
        start_pos: Position to start searching (default: 0)
        include_env_command_in_positions: If True, begin_end_pos points to start of \\begin
                                          instead of after it (default: False)

    Returns:
        (content, begin_end_pos, end_start_pos) where:
        - content: Text between \\begin{env} and \\end{env}
        - begin_end_pos: Position after \\begin{env_name} (or at \\begin if include_env_command_in_positions=True)
        - end_start_pos: Position at \\end{env_name}

    Raises:
        ValueError: If environment is not found or unmatched

    Example:
        >>> text = "\\\\begin{itemize} foo \\\\begin{itemize} bar \\\\end{itemize} \\\\end{itemize}"
        >>> content, begin_end, end_start = extract_environment_content(text, "itemize")
        >>> content
        ' foo \\\\begin{itemize} bar \\\\end{itemize} '
    """
    # Escape special regex characters in env_name (e.g., * in textblock*)
    env_name_escaped = re.escape(env_name)

    # Build patterns from templates
    begin_pattern = LaTeXPatterns.BEGIN_ENV.format(env=env_name_escaped)
    end_pattern = LaTeXPatterns.END_ENV.format(env=env_name_escaped)

    # Find \begin{env_name}
    begin_match = re.search(begin_pattern, text[start_pos:])

    if not begin_match:
        raise ValueError(f"No \\begin{{{env_name}}} found")

    begin_end_pos = start_pos + begin_match.end()

    # Count nested environments to find matching \end{env_name}
    pos = begin_end_pos
    depth = 1

    while pos < len(text) and depth > 0:
        begin_nested = re.search(begin_pattern, text[pos:])
        end_nested = re.search(end_pattern, text[pos:])

        if end_nested:
            if begin_nested and begin_nested.start() < end_nested.start():
                # Found nested \begin before \end
                depth += 1
                pos += begin_nested.end()
            else:
                # Found \end
                depth -= 1
                if depth == 0:
                    # Adjust begin position if requested to include \begin command
                    if include_env_command_in_positions:
                        begin_pos_to_return = start_pos + begin_match.start()
                        end_pos_to_return = pos + end_nested.end()
                    else:
                        begin_pos_to_return = begin_end_pos
                        end_pos_to_return = pos + end_nested.start()

                    content = text[begin_pos_to_return:end_pos_to_return]
                    return content, begin_pos_to_return, end_pos_to_return
                pos += end_nested.end()
        else:
            break

    raise ValueError(f"Unmatched \\begin{{{env_name}}}")


def extract_environment(
    text: str,
    env_name: str,
    num_params: int = 0,
    num_optional_params: int = 0,
    start_pos: int = 0,
    include_env_command_in_positions: bool = False,
) -> Tuple[List[str], str, int, int]:
    """
    Extract environment with optional and mandatory parameters, returning params and inner content separately.

    General-purpose function for extracting any LaTeX environment. Handles environments
    with optional [...] and mandatory {...} parameters by extracting them separately from the content.

    Args:
        text: LaTeX text containing environment
        env_name: Environment name (e.g., "itemize", "itemizeAcademic", "textblock*")
        num_params: Number of mandatory {...} parameters after \\begin{env} (default: 0)
        num_optional_params: Number of optional [...] parameters after \\begin{env} (default: 0)
        start_pos: Position to start searching (default: 0)

    Returns:
        (params, content, begin_end_pos, end_start_pos) where:
        - params: List of parameter values (optional first, then mandatory)
        - content: Inner content with parameters removed
        - begin_end_pos: Position after \\begin{env_name}
        - end_start_pos: Position at \\end{env_name}

    Raises:
        ValueError: If environment not found or unmatched

    Example:
        >>> text = r'''\\begin{itemizeAcademic}{Company}{Title}{Location}{Dates}
        ...     Content here
        ...     \\end{itemizeAcademic}'''
        >>> params, content, _, _ = extract_environment(text, "itemizeAcademic", num_params=4)
        >>> params
        ['Company', 'Title', 'Location', 'Dates']
        >>> content.strip()
        'Content here'

        >>> text2 = r'''\\begin{itemize}[leftmargin=0pt, itemsep=8pt]
        ...     \\item First
        ...     \\end{itemize}'''
        >>> params2, content2, _, _ = extract_environment(text2, "itemize", num_optional_params=1)
        >>> params2
        ['leftmargin=0pt, itemsep=8pt']
        >>> "\\item First" in content2
        True
    """
    # Guard against buggy parameter combination
    if include_env_command_in_positions and (num_params > 0 or num_optional_params > 0):
        raise NotImplementedError(
            "Parameter extraction does not work correctly when "
            "include_env_command_in_positions=True. "
            "The raw_env_content will include '\\begin{env_name}' which causes "
            "extract_sequential_params to incorrectly extract '{env_name}' as the first parameter. "
            "\n\nWorkaround: Use include_env_command_in_positions=False (the default), "
            "or extract params separately after getting the environment content."
        )

    # Extract environment with parameters still in content
    raw_env_content, begin_end_pos, end_start_pos = extract_environment_content(
        text, env_name, start_pos, include_env_command_in_positions
    )

    # Extract parameters if specified
    params = []
    content = raw_env_content

    if num_optional_params > 0 or num_params > 0:
        # Use skip_latex_arguments to extract and skip both optional and mandatory params
        content = skip_latex_arguments(
            raw_env_content, optional=num_optional_params, mandatory=num_params
        )

        # Extract optional params
        pos = 0
        for _ in range(num_optional_params):
            # Find opening [
            match = re.match(r"\s*\[", raw_env_content[pos:])
            if not match:
                break
            pos += match.end()

            # Find matching ]
            bracket_count = 1
            param_start = pos
            while pos < len(raw_env_content) and bracket_count > 0:
                if raw_env_content[pos] == "\\":
                    pos += 2  # Skip escaped char
                    continue
                elif raw_env_content[pos] == "[":
                    bracket_count += 1
                elif raw_env_content[pos] == "]":
                    bracket_count -= 1
                pos += 1

            if bracket_count == 0:
                params.append(raw_env_content[param_start : pos - 1])

        # Extract mandatory params
        if num_params > 0:
            mandatory_params = extract_sequential_params(raw_env_content, pos, num_params)
            params.extend(mandatory_params)

    return params, content, begin_end_pos, end_start_pos


def extract_all_environments(
    text: str, env_pattern: str, num_params: int = 0, include_env_command_in_positions: bool = True
) -> List[Tuple[str, List[str], str, int, int]]:
    """
    Extract all environments matching a regex pattern.

    Thin wrapper around extract_environment() that finds all matching \\begin{pattern}.

    Args:
        text: LaTeX text
        env_pattern: Regex pattern for environment name (e.g., 'itemize.*Project')
        num_params: Number of mandatory {...} parameters after \\begin{env}
        include_env_command_in_positions: If True, positions include \\begin command (default: True)

    Returns:
        List of (env_name, params, content, begin_end_pos, end_start_pos) tuples
    """
    # Use LaTeXPatterns template for consistency with extract_environment_content()
    begin_pattern = LaTeXPatterns.BEGIN_ENV_PATTERN.format(pattern=env_pattern)

    results = []
    for match in re.finditer(begin_pattern, text):
        env_name = match.group(1)  # Captured environment name
        params, content, begin_end_pos, end_start_pos = extract_environment(
            text,
            env_name,
            num_params,
            start_pos=match.start(),
            include_env_command_in_positions=include_env_command_in_positions,
        )
        results.append((env_name, params, content, begin_end_pos, end_start_pos))
    return results


def extract_itemize_entry(entry_latex: str, marker_pattern: str) -> dict:
    """
    Extract marker, plaintext, and latex_raw from an itemize list entry.

    Standardizes itemize entry parsing into a 3-field structure for uniform
    representation. Supports any LaTeX item marker variant.

    Args:
        entry_latex: LaTeX string for one complete entry (marker + content).
                    Should start with the item marker (\\itemi, \\item[...], etc.)
        marker_pattern: Regex pattern to match and extract marker.
                       Must include named capture group (?P<marker>...).
                       Use patterns from LaTeXPatterns:
                       - LaTeXPatterns.ITEM_ALPHABETIC for \\itemi, \\itemii, \\itemLL
                       - LaTeXPatterns.ITEM_BRACKETED for \\item[icon], \\item[--]
                       - LaTeXPatterns.ITEM_ANY for any variant

    Returns:
        Dict with 3 standardized fields:
        - marker: The item command without leading backslash
                 (e.g., "itemi", "itemLL", "item[--]", "item[\\faIcon]")
        - latex_raw: Content text preserving all LaTeX formatting commands
        - plaintext: Content text with all LaTeX commands stripped

    Raises:
        ValueError: If no marker found matching the provided pattern

    Example:
        >>> entry = r"\\itemi \\textbf{Bold} text with {formatting}"
        >>> extract_itemize_entry(entry, LaTeXPatterns.ITEM_ALPHABETIC)
        {
            'marker': 'itemi',
            'latex_raw': r'\\textbf{Bold} text with {formatting}',
            'plaintext': 'Bold text with formatting'
        }

        >>> entry2 = r"\\item[\\faIcon] Item text"
        >>> extract_itemize_entry(entry2, LaTeXPatterns.ITEM_BRACKETED)
        {
            'marker': 'item[\\faIcon]',
            'latex_raw': 'Item text',
            'plaintext': 'Item text'
        }
    """
    # Strip whitespace and match marker at start
    entry_stripped = entry_latex.strip()
    match = re.match(marker_pattern, entry_stripped)
    if not match:
        raise ValueError(
            f"No marker found matching pattern '{marker_pattern}' in entry: {entry_latex[:50]}..."
        )

    # Extract marker (without leading backslash)
    marker = match.group("marker")

    # Extract content (everything after marker, from stripped version)
    content_start = match.end()
    latex_raw = entry_stripped[content_start:].strip()

    # Generate plaintext version by stripping all LaTeX commands
    plaintext = to_plaintext(latex_raw)

    return {"marker": marker, "latex_raw": latex_raw, "plaintext": plaintext}


def split_itemize_entries(content: str, marker_pattern: str) -> List[str]:
    """
    Split itemize content into individual entry strings.

    Finds all item markers and slices content between them.
    Each returned string includes the marker and its content.

    Args:
        content: LaTeX content containing multiple itemize entries
        marker_pattern: Regex pattern to match markers (use LaTeXPatterns constants)

    Returns:
        List of entry strings, each starting with its marker

    Example:
        >>> content = r"\\itemi First\\itemi Second\\itemi Third"
        >>> split_itemize_entries(content, LaTeXPatterns.ITEM_ALPHABETIC)
        ['\\itemi First', '\\itemi Second', '\\itemi Third']
    """
    # Find all marker positions
    matches = list(re.finditer(marker_pattern, content))

    if not matches:
        return []

    entries = []
    for i, match in enumerate(matches):
        start = match.start()
        # End is either next marker start or end of content
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)

        entry = content[start:end].strip()
        if entry:  # Skip empty entries
            entries.append(entry)

    return entries


def parse_itemize_content(content: str, marker_pattern: str) -> List[dict]:
    """
    Parse itemize content into list of entry dictionaries.

    Convenience function that combines split_itemize_entries + extract_itemize_entry.
    Use when you already have the environment content extracted.

    Args:
        content: LaTeX content containing itemize entries
        marker_pattern: Regex pattern to match markers (use LaTeXPatterns constants)

    Returns:
        List of entry dicts with {marker, latex_raw, plaintext}

    Example:
        >>> content = r"\\itemi \\textbf{First}\\itemi Second"
        >>> entries = parse_itemize_content(content, LaTeXPatterns.ITEM_ALPHABETIC)
        >>> entries[0]
        {'marker': 'itemi', 'latex_raw': '\\\\textbf{First}', 'plaintext': 'First'}
        >>> entries[1]
        {'marker': 'itemi', 'latex_raw': 'Second', 'plaintext': 'Second'}
    """
    entry_strs = split_itemize_entries(content, marker_pattern)
    return [extract_itemize_entry(e, marker_pattern) for e in entry_strs]


def parse_itemize_with_complex_markers(content: str) -> List[dict]:
    """
    Parse itemize content with balanced bracket matching for complex item markers.

    Similar to parse_itemize_content() but handles markers with nested braces like:
        \\item[\\raisebox{-1pt}{>} 20,000]

    Standard parse_itemize_content() can't handle these because ITEM_ANY pattern
    stops at the first brace. This function uses extract_balanced_delimiters() for
    proper bracket/brace matching.

    Args:
        content: LaTeX content containing itemize entries with complex markers

    Returns:
        List of entry dicts with {marker, latex_raw, plaintext}

    Example:
        >>> content = r"\\item[\\raisebox{-1pt}{>} 20,000] GPU-hours\\item[X] Other"
        >>> entries = parse_itemize_with_complex_markers(content)
        >>> entries[0]["marker"]
        '\\item[\\raisebox{-1pt}{>} 20,000]'
        >>> entries[0]["latex_raw"]
        'GPU-hours'
    """
    items = []
    item_pattern = r"\\item"

    for match in re.finditer(item_pattern, content):
        item_pos = match.end()

        # Check if this is \item[...] (with bracket)
        if item_pos < len(content) and content[item_pos : item_pos + 1] == "[":
            # Use extract_balanced_delimiters to handle nested braces
            try:
                bracket_content, item_pos = extract_balanced_delimiters(
                    content, item_pos + 1, open_char="[", close_char="]"
                )
                # Reconstruct full marker including brackets
                marker = f"\\item[{bracket_content}]"
            except ValueError:
                # Fallback to simple \item if bracket matching fails
                marker = "\\item"
        else:
            # Simple \item without bracket
            marker = "\\item"

        # Find start of next \item or end of content
        next_item = re.search(item_pattern, content[item_pos:])
        if next_item:
            content_end = item_pos + next_item.start()
        else:
            content_end = len(content)

        # Extract item content
        item_content = content[item_pos:content_end].strip()

        items.append(
            {"marker": marker, "latex_raw": item_content, "plaintext": to_plaintext(item_content)}
        )

    return items


def replace_command(text: str, command: str, prefix: str = "", suffix: str = "") -> str:
    """
    Replace LaTeX command with optional prefix/suffix around content.

    Handles nested braces correctly using balanced delimiter matching.

    Args:
        text: Text containing the command
        command: Command name without backslash (e.g., "textbf", "centering")
        prefix: String to insert before content (default: "")
        suffix: String to insert after content (default: "")

    Returns:
        Text with command replaced by prefix + content + suffix

    Examples:
        >>> replace_command("\\\\textbf{bold text}", "textbf")
        'bold text'
        >>> replace_command("\\\\textbf{bold}", "textbf", "**", "**")
        '**bold**'
        >>> replace_command("Normal \\\\textbf{bold} text", "textbf", "**", "**")
        'Normal **bold** text'
        >>> replace_command("\\\\textbf{text \\\\texttt{nested} more}", "textbf")
        'text \\\\texttt{nested} more'
    """
    result = text
    command_pattern = f"\\{command}{{"

    while True:
        # Find next occurrence of \command{
        pos = result.find(command_pattern)
        if pos == -1:
            break

        # Position AFTER opening brace (extract_balanced_delimiters expects this)
        brace_pos = pos + len(command_pattern)

        try:
            # Extract content using balanced delimiter matching
            content, end_pos = extract_balanced_delimiters(result, brace_pos)

            # Replace \command{content} with prefix + content + suffix
            result = result[:pos] + prefix + content + suffix + result[end_pos:]
        except ValueError:
            # Unmatched braces, skip this occurrence
            break

    return result


def strip_formatting(text: str, commands: List[str]) -> str:
    """
    Remove LaTeX formatting commands from text.

    Commands are removed entirely (along with any trailing whitespace).
    This is for commands that don't wrap content (like \\centering, \\par).

    Args:
        text: Text containing formatting commands
        commands: List of command names to remove (without backslash)

    Returns:
        Text with formatting commands removed

    Example:
        >>> strip_formatting("\\\\centering Some text\\\\par", ["centering", "par"])
        ' Some text'
        >>> strip_formatting("\\\\centering \\\\textit{text}", ["centering"])
        '\\\\textit{text}'
    """
    result = text
    for command in commands:
        # Build pattern from template, escaping command name
        pattern = LaTeXPatterns.COMMAND_WITH_WHITESPACE.format(command=re.escape(command))
        result = re.sub(pattern, "", result)
    return result


def remove_command_at_end(text: str, command: str) -> str:
    """
    Remove LaTeX command at the end of text.

    Args:
        text: Text that may end with command
        command: Command name to remove (without backslash)

    Returns:
        Text with command removed from end

    Example:
        >>> remove_command_at_end("Some text\\\\par", "par")
        'Some text'
        >>> remove_command_at_end("Some text", "par")
        'Some text'
    """
    # Build pattern from template, escaping command name
    pattern = LaTeXPatterns.COMMAND_AT_END.format(command=re.escape(command))
    return re.sub(pattern, "", text)


def to_plaintext(latex_str: str, strip_latex_params: bool = True) -> str:
    """
    Strip ALL LaTeX commands from text, returning pure plaintext.

    Removes:
    - Content wrappers (\\textbf{...}, \\textit{...}, \\color{...}{...})
    - Standalone commands (\\centering, \\par, \\vspace{...})
    - Literal braces used for grouping ({text})
    - All other backslash commands
    - Extra whitespace
    - LaTeX optional parameters like [leftmargin=0pt] (if strip_latex_params=True)

    Converts to plaintext equivalents:
    - Escaped braces (\\{ and \\}) become literal { and }
    - Escaped special chars (\\%, \\$, \\&, \\#, \\_) become their characters
    - LaTeX spacing (\\;, \\,, \\:) become regular spaces
    - Negative thin space (\\!) is removed

    Use for creating plaintext versions of metadata for Targeting context.
    Future use: Targeting context can work with clean text without parsing LaTeX.

    Args:
        latex_str: LaTeX string with formatting commands
        strip_latex_params: If True, remove bracket params containing = (default: True)

    Returns:
        Plain text with all LaTeX commands removed

    Example:
        >>> to_plaintext("\\\\centering \\\\textbf{\\\\vspace{0pt} Bold text}\\\\par")
        'Bold text'
        >>> to_plaintext("\\\\color{red}{Colored} normal")
        'Colored normal'
        >>> to_plaintext("{PyTorch} and {NumPy}")
        'PyTorch and NumPy'
        >>> to_plaintext("Use \\\\{ and \\\\} for literal braces")
        'Use { and } for literal braces'
    """
    if not latex_str:
        return ""

    result = latex_str

    # Remove common content wrappers by unwrapping them
    wrappers = [
        "textbf",
        "textit",
        "emph",
        "underline",
        "texttt",
        "scshape",
        "coloremph",
        "textnormal",
    ]
    for wrapper in wrappers:
        result = replace_command(result, wrapper)

    # Remove color commands (\\color{...}{...} or \\color{...})
    result = re.sub(LaTeXPatterns.COLOR_WITH_TEXT, r"\1", result)
    result = re.sub(LaTeXPatterns.COLOR_STANDALONE, "", result)

    # Remove common standalone commands
    standalone = ["centering", "par", "nolinebreak", "nopagebreak"]
    result = strip_formatting(result, standalone)

    # Remove spacing commands (\\vspace{...}, \\hspace{...})
    result = re.sub(LaTeXPatterns.SPACING_COMMANDS, "", result)

    # Handle line breaks (\\) - convert to space
    result = result.replace(r"\\", " ")

    # Handle common math mode symbols before general command removal
    math_symbols = [
        (" to ", r"$\to$"),  # Arrow: 1 $\to$ 64 -> 1 to 64
        ("->", r"\to"),  # Bare arrow command
        ("->", r"\rightarrow"),  # Right arrow
        ("<-", r"\leftarrow"),  # Left arrow
        ("<=", r"\leq"),  # Less than or equal
        (">=", r"\geq"),  # Greater than or equal
        ("!=", r"\neq"),  # Not equal
        ("~", r"\sim"),  # Similar to
        ("≈", r"\approx"),  # Approximately
        ("×", r"\texttimes"),  # Multiplication sign (text mode)
        ("×", r"\times"),  # Multiplication sign (math mode)
        ("half", r"\textonehalf"),  # One half
    ]
    for replacement, latex_cmd in math_symbols:
        result = result.replace(latex_cmd, replacement)

    # Handle escaped special characters and spacing commands
    # These must be done before general command removal
    escaped_chars = [
        ("%", r"\%"),  # Escaped percent
        ("$", r"\$"),  # Escaped dollar
        ("&", r"\&"),  # Escaped ampersand
        ("#", r"\#"),  # Escaped hash
        ("_", r"\_"),  # Escaped underscore
        (" ", r"\ "),  # Explicit space (backslash-space)
        (" ", r"\;"),  # Thin space
        (" ", r"\,"),  # Thin space
        (" ", r"\:"),  # Medium space
        ("", r"\!"),  # Negative thin space (remove)
    ]
    for replacement, escaped in escaped_chars:
        result = result.replace(escaped, replacement)

    # Remove math mode delimiters ($...$) after handling math symbols
    result = result.replace("$", "")

    # Remove any remaining backslash commands (\\command or \\command{...})
    # First remove commands with braces
    result = re.sub(LaTeXPatterns.ANY_COMMAND_WITH_BRACES, "", result)
    # Then remove commands without braces
    result = re.sub(LaTeXPatterns.ANY_COMMAND_NO_BRACES, "", result)

    # Remove LaTeX optional parameters (brackets containing =, like [leftmargin=0pt])
    # These are left behind after \begin{env} is stripped. Content brackets like [1] are preserved.
    if strip_latex_params:
        result = re.sub(r"\[[^\]]*=[^\]]*\]", "", result)

    # Remove literal braces used for grouping (not escaped braces)
    # Escaped braces (\{ and \}) should be converted to literal { and }
    result = result.replace(r"\{", "<<<LEFTBRACE>>>")
    result = result.replace(r"\}", "<<<RIGHTBRACE>>>")
    # Remove unescaped braces
    result = result.replace("{", "").replace("}", "")
    # Restore escaped braces as literal characters
    result = result.replace("<<<LEFTBRACE>>>", "{")
    result = result.replace("<<<RIGHTBRACE>>>", "}")

    # Clean up extra whitespace
    result = re.sub(r"\s+", " ", result)
    result = result.strip()

    return result


def to_latex(plaintext_str: str) -> str:
    """
    Convert plaintext to LaTeX by escaping special characters.

    Escapes LaTeX special characters that have syntactic meaning. This is used
    when converting plaintext content (e.g., from targeting context) to LaTeX-safe
    format for template generation.

    Conversions:
    - \\ → \\textbackslash{} (backslash, must be first to avoid double-escaping)
    - % → \\%
    - $ → \\$
    - & → \\&
    - _ → \\_
    - # → \\#
    - { → \\{
    - } → \\}
    - ~ → \\textasciitilde{}
    - ^ → \\textasciicircum{}

    Args:
        plaintext_str: Plain text string

    Returns:
        LaTeX string with special characters escaped

    Example:
        >>> to_latex("AI & Machine Learning")
        'AI \\\\& Machine Learning'
        >>> to_latex("87% on-time delivery")
        '87\\\\% on-time delivery'
    """
    if not plaintext_str:
        return ""

    result = plaintext_str

    # Escape special LaTeX characters
    # Note: Order matters - backslash must be first to avoid double-escaping
    result = result.replace("\\", r"\textbackslash{}")
    result = result.replace("%", r"\%")
    result = result.replace("$", r"\$")
    result = result.replace("&", r"\&")
    result = result.replace("_", r"\_")
    result = result.replace("#", r"\#")
    result = result.replace("{", r"\{")
    result = result.replace("}", r"\}")
    result = result.replace("~", r"\textasciitilde{}")
    result = result.replace("^", r"\textasciicircum{}")

    return result


# Used only once in converter, might not be useful. Might replace it with other, more general function(s)
def skip_latex_arguments(
    text: str, optional: int = 0, mandatory: int = 0, special_paren: bool = False
) -> str:
    """
    Skip LaTeX arguments at start of text and return remaining content.

    Handles three argument types in order:
    - Optional: [...] (square brackets)
    - Mandatory: {...} (curly braces, handles nesting)
    - Special paren: (...) (textpos package style coordinates)

    Use for extracting inner content when arguments are captured separately.
    Example: textblock* has {width}(coordinates) before content.

    Args:
        text: LaTeX text starting with arguments
        optional: Number of optional [...] arguments to skip
        mandatory: Number of mandatory {...} arguments to skip
        special_paren: Whether to skip one (...) argument after mandatory args

    Returns:
        Text with arguments stripped from beginning

    Example:
        >>> skip_latex_arguments(
        ...     "{\\\\textwidth}(\\\\leftmargin, 0.5\\\\paperheight)content",
        ...     mandatory=1,
        ...     special_paren=True,
        ... )
        'content'
        >>> skip_latex_arguments("[option]{arg}content", optional=1, mandatory=1)
        'content'
    """
    pos = 0

    # Skip optional arguments [...]
    for _ in range(optional):
        # Find opening [
        match = re.match(r"\s*\[", text[pos:])
        if not match:
            break
        pos += match.end()

        # Find matching ]
        bracket_count = 1
        while pos < len(text) and bracket_count > 0:
            if text[pos] == "\\":
                pos += 2  # Skip escaped char
                continue
            elif text[pos] == "[":
                bracket_count += 1
            elif text[pos] == "]":
                bracket_count -= 1
            pos += 1

    # Skip mandatory arguments {...} (with nesting support)
    if mandatory > 0:
        params = extract_sequential_params(text, pos, mandatory)
        # Calculate how many chars to skip (all the {...} blocks)
        for _ in params:
            # Skip whitespace before {
            match = re.match(r"\s*", text[pos:])
            pos += match.end()
            # Skip the {...} block
            brace_count = 1
            pos += 1  # Skip opening {
            while pos < len(text) and brace_count > 0:
                if text[pos] == "\\":
                    pos += 2
                    continue
                elif text[pos] == "{":
                    brace_count += 1
                elif text[pos] == "}":
                    brace_count -= 1
                pos += 1

    # Skip special paren argument (...)
    if special_paren:
        # Find opening (
        match = re.match(r"\s*\(", text[pos:])
        if match:
            pos += match.end()

            # Find matching )
            paren_count = 1
            while pos < len(text) and paren_count > 0:
                if text[pos] == "\\":
                    pos += 2  # Skip escaped char
                    continue
                elif text[pos] == "(":
                    paren_count += 1
                elif text[pos] == ")":
                    paren_count -= 1
                pos += 1

    return text[pos:].lstrip()


def format_latex_environment(
    env_name: str,
    content: str,
    optional_args: List[str] = None,
    mandatory_args: List[str] = None,
    special_paren_arg: str = None,
) -> str:
    """
    Generate LaTeX environment with arguments.

    Builds: \\begin{env}[opt1][opt2]{arg1}{arg2}(special)
            content
            \\end{env}

    Use for generating environments with complex argument structure.
    Example: textblock* needs {width}(coordinates).

    Args:
        env_name: Environment name (e.g., "textblock*", "itemize")
        content: Inner content
        optional_args: Optional arguments in [...] (default: None)
        mandatory_args: Mandatory arguments in {...} (default: None)
        special_paren_arg: Special coordinate argument in (...) (default: None)

    Returns:
        Complete LaTeX environment string

    Example:
        >>> format_latex_environment(
        ...     "textblock*",
        ...     "content",
        ...     mandatory_args=["\\\\textwidth"],
        ...     special_paren_arg="\\\\leftmargin, 0.5\\\\paperheight",
        ... )
        '\\\\begin{textblock*}{\\\\textwidth}(\\\\leftmargin, 0.5\\\\paperheight)\\ncontent\\n\\\\end{textblock*}'
    """
    # Build opening tag
    opening = f"\\begin{{{env_name}}}"

    # Add optional arguments
    if optional_args:
        for arg in optional_args:
            opening += f"[{arg}]"

    # Add mandatory arguments
    if mandatory_args:
        for arg in mandatory_args:
            opening += f"{{{arg}}}"

    # Add special paren argument
    if special_paren_arg:
        opening += f"({special_paren_arg})"

    # Build closing tag
    closing = f"\\end{{{env_name}}}"

    return f"{opening}\n{content}\n{closing}"
