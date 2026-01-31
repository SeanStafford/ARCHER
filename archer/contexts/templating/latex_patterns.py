"""
LaTeX Pattern Constants

Centralized LaTeX pattern strings used for parsing and generation.
All patterns are stored as regex-ready strings. Use regex_to_literal() to convert for generation.
"""

from dataclasses import dataclass
from typing import List


def regex_to_literal(regex_pattern: str) -> str:
    """
    Convert regex pattern to literal LaTeX string for generation.

    Args:
        regex_pattern: Regex pattern with escaped characters (e.g., r'\\begin\{document\}')

    Returns:
        Literal LaTeX string (e.g., r'\begin{document}')

    Example:
        >>> regex_to_literal(r"\\begin\{document\}")
        '\\begin{document}'
    """
    return (
        regex_pattern.replace("\\\\", "\\")  # Double backslash -> single backslash
        .replace("\\{", "{")  # Escaped brace -> literal brace
        .replace("\\}", "}")  # Escaped brace -> literal brace
        .replace("\\*", "*")
    )  # Escaped asterisk -> literal asterisk


@dataclass(frozen=True)
class DocumentRegex:
    """
    Regex patterns for document-level LaTeX commands.

    For generation, use: regex_to_literal(DocumentRegex.BEGIN_DOCUMENT)
    For parsing, use directly: re.search(DocumentRegex.BEGIN_DOCUMENT, text)
    """

    BEGIN_DOCUMENT: str = r"\\begin\{document\}"
    END_DOCUMENT: str = r"\\end\{document\}"
    CLEARPAGE: str = r"\\clearpage"
    CLEARPAGE_WITH_WHITESPACE: str = r"\\clearpage\s*"


@dataclass(frozen=True)
class PageRegex:
    """
    Regex patterns for page layout (two-column paracol structure).

    For generation, use: regex_to_literal(PageRegex.BEGIN_PARACOL)
    For parsing, use directly: re.search(PageRegex.BEGIN_PARACOL, text)
    """

    BEGIN_PARACOL: str = r"\\begin\{paracol\}\{2\}"
    END_PARACOL: str = r"\\end\{paracol\}"
    SWITCHCOLUMN: str = r"\\switchcolumn"

    # Bottom bar absolute positioning (textblock)
    # Note: textblock* environment is extracted via extract_environment_content(), not regex

    # Gradient and bar decorations (follow textblock, have fixed number of brace groups)
    LEFTGRAD: str = r"\\leftgrad\{[^}]+\}\{[^}]+\}\{[^}]+\}\{[^}]+\}\{[^}]+\}[^\n]*\n?"
    BOTTOMBAR: str = r"\\bottombar\{[^}]+\}\{[^}]+\}\{[^}]+\}\{[^}]+\}[^\n]*\n?"
    TOPGRADTRI: str = r"\\topgradtri\{[^}]+\}\{[^}]+\}\{[^}]+\}\{[^}]+\}\{[^}]+\}\{[^}]+\}[^\n]*\n?"

    # Page setup pattern (appears at start of all pages including page 1)
    PAGE_SETUP: str = r"(\\toggletrue\{useleftbar\}.*?\\pagestyle\{resume\})"

    # Page setup pattern for pages 2+ (after \clearpage)
    PAGE_SETUP_AFTER_CLEARPAGE: str = (
        r"\\clearpage.*?(\\toggletrue\{useleftbar\}.*?\\pagestyle\{resume\})"
    )

    # Decorations following textblock (leftgrad/bottombar commands)
    DECORATIONS_FOLLOWING_TEXTBLOCK: str = (
        r"(\s*\\(?:leftgrad|bottombar)\{[^}]*\}(?:\{[^}]*\})*\s*)*"
    )


@dataclass(frozen=True)
class SectionRegex:
    """
    Regex patterns for section headings.

    For generation, use: regex_to_literal(SectionRegex.SECTION_STAR)
    For parsing, use directly: re.search(SectionRegex.SECTION_STAR, text)
    """

    SECTION_STAR: str = r"\\section\*"
    SECTION_WITH_NAME: str = (
        r"\\section\*?\{"  # Finds section start, name extracted with balanced braces
    )
    TRAILING_VSPACE: str = r"(\n*(?:\\vspace\{[^}]+\}(?:\s*%[^\n]*)?\n*)+)$"  # Captures all consecutive trailing vspace commands with newlines

    # Matches \par at end of line (for normalization to blank lines)
    # Excludes lines containing \centering (where \par has special behavior)
    # Captures everything before \par for replacement
    PAR_AT_LINE_END: str = r"^(?!.*\\centering)(.*)\\par\s*\n"

    # Old Education header (5 old resumes use this non-standard format)
    # \phantomsection \textcolor{black}{\bfseries \large Education} \addcontentsline{toc}{section}{Education} \columnhrule
    OLD_EDUCATION_HEADER: str = r"\\phantomsection\s*\\textcolor\{black\}\{\\bfseries\s+\\large\s+Education\}\s*\\addcontentsline\{toc\}\{section\}\{Education\}\s*\\columnhrule\s*"


@dataclass(frozen=True)
class EnvironmentPatterns:
    """
    Regex patterns for LaTeX environments.

    These are regex-ready patterns (use directly, no re.escape() needed).
    Double backslashes (\\) match literal backslashes in LaTeX source.
    """

    # Work experience
    BEGIN_ITEMIZE_ACADEMIC: str = r"\\begin\{itemizeAcademic\}"
    END_ITEMIZE_ACADEMIC: str = r"\\end\{itemizeAcademic\}"
    ITEMI: str = r"\\itemi\s+"

    # Education (two bullet variants across resumes)
    EDUCATION_ICON_BULLET: str = r"\\faUserGraduate"  # FontAwesome graduation cap
    EDUCATION_CUSTOM_BULLET: str = r"\\itemi"  # Custom marker from tables.sty

    # Projects (handles itemizeAProject, itemizeKeyProject, etc.)
    BEGIN_ITEMIZE_PROJECT: str = r"\\begin\{itemize.*Project\}"
    END_ITEMIZE_PROJECT: str = r"\\end\{itemize.*Project\}"
    ITEMIZE_PROJECT_ENV: str = (
        r"itemize.*Proj(?:ect|Second)"  # Env name pattern for extract_all_environments
    )
    ITEMII: str = r"\\itemii\s+"

    # Standalone projects section
    BEGIN_ITEMIZE_PROJ_MAIN: str = r"\\begin\{itemizeProjMain\}"
    END_ITEMIZE_PROJ_MAIN: str = r"\\end\{itemizeProjMain\}"
    BEGIN_ITEMIZE_PROJ_SECOND: str = r"\\begin\{itemizeProjSecond\}"
    END_ITEMIZE_PROJ_SECOND: str = r"\\end\{itemizeProjSecond\}"
    ITEMIZE_PROJ_SECOND_ENV: str = (
        r"itemizeProjSecond"  # Env name pattern for extract_all_environments
    )

    # Generic itemize environment (for skill_categories, education, etc.)
    BEGIN_ITEMIZE: str = r"\\begin\{itemize\}"
    END_ITEMIZE: str = r"\\end\{itemize\}"
    BEGIN_ITEMIZE_PARTIAL: str = r"\\begin\{itemize"  # For nested depth tracking
    END_ITEMIZE_PARTIAL: str = r"\\end\{itemize"  # For nested depth tracking
    ITEM_BRACKET: str = r"\\item\["  # Item with optional icon/parameter

    # Skill category headers (distinguished from regular items by TOC entry)
    # Matches: \item[icon]{...} followed by \addcontentsline on next line
    # Does NOT match: \item[--] or \itemLL (items inside itemizeLL)
    SKILL_CATEGORY_HEADER: str = (
        r"\\item\[.*?\][^\n]*(?=\n[^\n]*\\addcontentsline\{toc\}\{section\})"
    )

    # Skill lists
    BEGIN_ITEMIZE_LL: str = r"\\begin\{itemizeLL\}"
    END_ITEMIZE_LL: str = r"\\end\{itemizeLL\}"
    ITEM_LL: str = r"\\itemLL"

    BEGIN_ITEMIZE_MAIN: str = r"\\begin\{itemizeMain\}"
    END_ITEMIZE_MAIN: str = r"\\end\{itemizeMain\}"

    # Catch-all pattern for any itemize variant (used for simple_list fallback type detection)
    BEGIN_ITEMIZE_ANY: str = r"\\begin\{itemize[A-z]*\}"
    ITEM_ANY: str = r"\\(?P<marker>item[^ {}]+)"

    # Vanilla \item only (followed by [ or whitespace, NOT itemi/itemii/itemLL)
    # Used by custom_itemize to avoid splitting on \itemii inside nested environments
    ITEM_VANILLA: str = r"\\item(?=\[|\s)"

    # Absolutely positioned textblock (bottom bar)
    BEGIN_TEXTBLOCK_STAR: str = r"\\begin\{textblock\*\}"
    END_TEXTBLOCK_STAR: str = r"\\end\{textblock\*\}"
    # Textblock with arguments: \begin{textblock*}{width}(x, y)
    TEXTBLOCK_WITH_ARGS: str = r"\\begin\{textblock\*\}(\{[^}]+\})(\([^)]+\))"


@dataclass(frozen=True)
class MetadataPatterns:
    """
    Preamble metadata field patterns.

    Used for extracting and generating document metadata (name, brand, colors, etc.).
    """

    # Command patterns
    RENEWCOMMAND: str = r"\renewcommand"
    SETUPHYPERANDMETA: str = r"\setuphyperandmeta"
    SETHLCOLOR: str = r"\sethlcolor"
    DEF_NLINESPP: str = r"\def\nlinesPP"

    # Field names (for \renewcommand extraction)
    MYNAME: str = "myname"
    MYDATE: str = "mydate"
    BRAND: str = "brand"
    PROFESSIONAL_PROFILE: str = "ProfessionalProfile"
    PDFKEYWORDS: str = "pdfkeywords"


@dataclass(frozen=True)
class ColorFields:
    """
    Known color field names for resume theming.

    These are extracted separately from general metadata fields.
    """

    EMPHCOLOR: str = "emphcolor"
    TOPBARCOLOR: str = "topbarcolor"
    LEFTBARCOLOR: str = "leftbarcolor"
    BRANDCOLOR: str = "brandcolor"
    NAMECOLOR: str = "namecolor"

    @classmethod
    def all(cls) -> List[str]:
        """Return list of all color field names."""
        return [
            cls.EMPHCOLOR,
            cls.TOPBARCOLOR,
            cls.LEFTBARCOLOR,
            cls.BRANDCOLOR,
            cls.NAMECOLOR,
        ]


@dataclass(frozen=True)
class FormattingPatterns:
    """
    LaTeX formatting command patterns (literal strings).

    Used for generating formatted content.
    """

    TEXTBF: str = r"\textbf"
    CENTERING: str = r"\centering"
    PAR: str = r"\par"
    SCSHAPE: str = r"\scshape"
    SETLENGTH: str = r"\setlength"
    BASELINESKIP: str = r"\baselineskip"
    PARSKIP: str = r"\parskip"
    TEXTTT: str = r"\texttt"
    COLOREMPH: str = r"\coloremph"


@dataclass(frozen=True)
class MetadataRegex:
    """
    Regex patterns for parsing metadata from preamble.

    For parsing, use directly: re.search(MetadataRegex.RENEWCOMMAND_START, text)
    """

    # Composed patterns for finding \renewcommand structures
    RENEWCOMMAND_START: str = r"\\renewcommand\{\\"  # Start of \renewcommand{\ pattern
    RENEWCOMMAND_FIELD: str = r"\\renewcommand\{\\([^}]+)\}"  # Captures field name

    # Spacing and layout parameters
    SETLENGTH: str = r"\\setlength\{\\([^}]+)\}\{([^}]+)\}"  # Captures param name and value
    DEFLEN: str = r"\\deflen\{([^}]+)\}\{([^}]+)\}"  # Captures param name and value

    # Professional profile line count
    NLINESPP: str = r"\\def\\nlinesPP\{([^}]+)\}"  # Captures number of PP lines

    # Toggle for listing title after name (PhD display)
    LIST_TITLE_AFTER_NAME: str = (
        r"\\toggle(true|false)\{list_title_after_name\}"  # Captures true/false
    )

    # Highlight color
    SETHLCOLOR: str = r"\\sethlcolor\{([^}]+)\}"  # Captures color name

    # Custom package declarations (e.g., fontspec + custom fonts)
    USEPACKAGE: str = r"\\usepackage(?:\[[^\]]*\])?\{[^}]+\}"  # Matches \usepackage{name} or \usepackage[options]{name}
    NEWFONTFAMILY: str = r"\\newfontfamily\{[^}]+\}(?:\[[^\]]*\])?\{[^}]+\}"  # Matches \newfontfamily{\cmd}[options]{font}


@dataclass(frozen=True)
class PreamblePatterns:
    """
    Standard preamble packages that are part of the template.

    These are generated by the template and should NOT be extracted as custom packages.
    Only packages NOT in this list should be considered custom.
    """

    GEOMETRY: str = "geometry"  # Generated from setlengths in template

    @classmethod
    def all(cls) -> List[str]:
        """Return list of all standard package names."""
        return [
            cls.GEOMETRY,
        ]


@dataclass(frozen=True)
class FormattingRegex:
    """
    Regex patterns for parsing/cleaning formatting commands.

    For parsing, use directly: re.search(FormattingRegex.TEXTBF_WITH_CONTENT, text)
    """

    TEXTBF_WITH_CONTENT: str = r"\\textbf\{([^}]+)\}"  # Captures content inside \textbf{}
    CENTERING_WITH_WHITESPACE: str = r"\\centering\s*"  # \centering with optional whitespace
    PAR_AT_END: str = r"\\par\s*$"  # \par at end of string with optional whitespace


@dataclass(frozen=True)
class ContentPatterns:
    """
    Content-specific strings for section type detection.

    These are literal strings (not regex) used to identify section types.
    """

    EDUCATION_UNIVERSITY: str = (
        "Bachelor of Arts in Physics"  # All Education sections contain this degree
    )


class ContactFieldPatterns:
    """
    Contact field patterns for header generation.

    Maps contact field types to their FontAwesome icons and link prefixes.
    """

    IMPLEMENTED_FIELDS = ["phone", "location", "email", "github", "linkedin", "website"]

    ICONS = {
        "phone": r"\faPhone",
        "location": r"\faMapMarker*",
        "email": r"\faInbox",
        "github": r"\faGithub",
        "linkedin": r"\faLinkedin",
        "website": r"\faGlobe",
    }

    LINK_PREFIXES = {
        "phone": None,
        "location": None,
        "email": "mailto:",
        "github": "https://www.",
        "linkedin": "https://www.",
        "website": "https://www.",
    }
