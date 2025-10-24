"""
LaTeX <-> YAML Converter

Handles bidirectional conversion between structured YAML and LaTeX resume format.
Uses type definitions from data/resume_archive/structured/types/ to guide conversion.
"""

import re
import os
from pathlib import Path
from typing import Any, Dict, List

from omegaconf import OmegaConf
from dotenv import load_dotenv

from archer.contexts.templating.latex_patterns import (
    DocumentPatterns,
    PagePatterns,
    SectionPatterns,
    EnvironmentPatterns,
    MetadataPatterns,
    ColorFields,
    FormattingPatterns,
)

load_dotenv()
TYPES_PATH = Path(os.getenv("RESUME_ARCHIVE_PATH")) / "structured/types"


class TypeRegistry:
    """Loads and caches type definitions from YAML files."""

    def __init__(self, types_dir: Path = TYPES_PATH):
        self.types_dir = types_dir
        self._types: Dict[str, Any] = {}

    def load_type(self, type_name: str) -> Dict[str, Any]:
        """Load a type definition from YAML file."""
        if type_name in self._types:
            return self._types[type_name]

        type_file = self.types_dir / f"{type_name}.yaml"
        if not type_file.exists():
            raise ValueError(f"Type definition not found: {type_name} at {type_file}")

        type_def = OmegaConf.load(type_file)
        self._types[type_name] = OmegaConf.to_container(type_def, resolve=True)
        return self._types[type_name]


class YAMLToLaTeXConverter:
    """Converts structured YAML to LaTeX format."""

    def __init__(self, type_registry: TypeRegistry = None):
        self.registry = type_registry or TypeRegistry()

    def generate_preamble(self, metadata: Dict[str, Any]) -> str:
        """
        Generate LaTeX preamble from document metadata.

        Args:
            metadata: Dictionary with metadata fields (name, date, brand, colors, etc.)

        Returns:
            LaTeX preamble string (\\renewcommand statements)
        """
        lines = []

        # Add pdfkeywords if in fields
        if 'fields' in metadata and MetadataPatterns.PDFKEYWORDS in metadata['fields']:
            lines.append(f"{MetadataPatterns.RENEWCOMMAND}{{\\{MetadataPatterns.PDFKEYWORDS}}}{{{metadata['fields'][MetadataPatterns.PDFKEYWORDS]}}}")

        # Add name (with \textbf)
        name = metadata.get('name', '')
        lines.append(f"{MetadataPatterns.RENEWCOMMAND}{{\\{MetadataPatterns.MYNAME}}}{{{FormattingPatterns.TEXTBF}{{{name}}}}}")

        # Add date
        date = metadata.get('date', '')
        lines.append(f"{MetadataPatterns.RENEWCOMMAND}{{\\{MetadataPatterns.MYDATE}}}{{{date}}}")

        # Add setuphyperandmeta call
        lines.append(f"{MetadataPatterns.SETUPHYPERANDMETA}{{\\{MetadataPatterns.MYNAME}}}{{\\{MetadataPatterns.MYDATE}}}{{\\{MetadataPatterns.PDFKEYWORDS}}}")
        lines.append("")

        # Add color commands
        lines.append(f"{MetadataPatterns.SETHLCOLOR}{{red}}")
        colors = metadata.get('colors', {})
        for color_key in ColorFields.all():
            if color_key in colors:
                lines.append(f"{MetadataPatterns.RENEWCOMMAND}{{\\{color_key}}}{{{colors[color_key]}}}")

        lines.append("")

        # Add brand
        brand = metadata.get('brand', '')
        lines.append(f"{MetadataPatterns.RENEWCOMMAND}{{\\{MetadataPatterns.BRAND}}}{{{brand}}}")

        # Add professional profile if present
        if metadata.get('professional_profile'):
            profile = metadata['professional_profile']
            lines.append(f"{MetadataPatterns.DEF_NLINESPP}{{1}}")
            lines.append(f"{MetadataPatterns.RENEWCOMMAND}{{\\{MetadataPatterns.PROFESSIONAL_PROFILE}}}{{{FormattingPatterns.CENTERING} {FormattingPatterns.TEXTBF}{{{profile}}}{FormattingPatterns.PAR}}}")

        return "\n".join(lines)

    def convert_work_experience(self, subsection: Dict[str, Any]) -> str:
        """
        Convert work_experience subsection to LaTeX.

        Args:
            subsection: Dict with type, metadata, and content

        Returns:
            LaTeX string for itemizeAcademic environment
        """
        type_def = self.registry.load_type(subsection["type"])
        metadata = subsection["metadata"]
        content = subsection["content"]

        # Build opening line
        company = metadata["company"]
        title = metadata["title"]
        if "subtitle" in metadata and metadata["subtitle"]:
            # Append subtitle to title
            title = f"{title}\\\\{metadata['subtitle']}"
        location = metadata["location"]
        dates = metadata["dates"]

        lines = []
        lines.append(
            f"    \\begin{{{type_def['latex_environment']}}}{{{company}}}{{{title}}}{{{location}}}{{{dates}}}"
        )
        lines.append("")

        # Add bullets
        for bullet in content.get("bullets", []):
            bullet_type = bullet.get("type", type_def["default_bullet_type"])
            text = bullet["text"]
            lines.append(f"        \\{bullet_type} {text}")
            lines.append("")

        # Add projects
        for project in content.get("projects", []):
            project_latex = self.convert_project(project, indent="        ")
            lines.append(project_latex)
            lines.append("")

        lines.append(f"    \\end{{{type_def['latex_environment']}}}")

        return "\n".join(lines)

    def convert_project(self, project: Dict[str, Any], indent: str = "") -> str:
        """
        Convert project subsection to LaTeX.

        Args:
            project: Dict with type, metadata, and bullets
            indent: Indentation string to prepend to each line

        Returns:
            LaTeX string for itemizeAProject environment
        """
        type_def = self.registry.load_type(project["type"])
        metadata = project["metadata"]

        bullet_symbol = metadata.get("bullet_symbol", "{{\\large $\\bullet$}}")
        name = metadata["name"]
        dates = metadata.get("dates", "")

        lines = []
        lines.append(
            f"{indent}\\begin{{{type_def['latex_environment']}}}{{{bullet_symbol}}}{{{name}}}{{{dates}}}"
        )

        # Add project bullets
        for bullet in project["bullets"]:
            bullet_type = bullet.get("type", type_def["default_bullet_type"])
            text = bullet["text"]
            lines.append(f"{indent}    \\{bullet_type} {text}")

        lines.append(f"{indent}\\end{{{type_def['latex_environment']}}}")

        return "\n".join(lines)

    def convert_skill_list_caps(self, section: Dict[str, Any]) -> str:
        """
        Convert skill_list_caps section to LaTeX.

        Args:
            section: Dict with type and content (list of items)

        Returns:
            LaTeX string for skill list in braced format with small caps
        """
        content = section["content"]
        items = content["list"]

        lines = []
        lines.append("   { \\setlength{\\baselineskip}{10pt} \\setlength{\\parskip}{7.5pt} \\scshape")
        lines.append("")

        # Add each item with blank line separator
        for item in items:
            lines.append(f"    {item}")
            lines.append("")

        lines.append("   }")

        return "\n".join(lines)

    def convert_skill_list_pipes(self, section: Dict[str, Any]) -> str:
        """
        Convert skill_list_pipes section to LaTeX.

        Args:
            section: Dict with type and content (list of items)

        Returns:
            LaTeX string for pipe-separated list with \\texttt{} wrapping
        """
        content = section["content"]
        items = content["list"]

        # Wrap each item in \texttt{} and join with ' | '
        wrapped_items = [f"\\texttt{{{item}}}" for item in items]
        latex_line = " | ".join(wrapped_items)

        # Format with indentation
        return f"    {latex_line}"

    def convert_skill_category(self, subsection: Dict[str, Any]) -> str:
        """
        Convert skill_category subsection to LaTeX.

        Args:
            subsection: Dict with type, metadata, and content

        Returns:
            LaTeX string for single category with icon and itemizeLL
        """
        metadata = subsection["metadata"]
        content = subsection["content"]

        name = metadata["name"]
        icon = metadata.get("icon", "")
        items = content["list"]

        lines = []

        # Add \item[icon] {\scshape name}
        lines.append(f"\\item[{icon}] {{\\scshape {name}}}")

        # Add itemizeLL environment
        lines.append("\\begin{itemizeLL}")
        for item in items:
            lines.append(f"    \\itemLL {{{item}}}")
        lines.append("\\end{itemizeLL}")

        return "\n".join(lines)

    def convert_skill_categories(self, section: Dict[str, Any]) -> str:
        """
        Convert skill_categories section to LaTeX.

        Args:
            section: Dict with type and subsections

        Returns:
            LaTeX string for itemize with multiple categories
        """
        subsections = section["subsections"]

        lines = []

        # Begin itemize with parameters
        lines.append("\\begin{itemize}[leftmargin=\\firstlistindent, labelsep = 0pt, align=center, labelwidth=\\firstlistlabelsep, itemsep = 8pt]")
        lines.append("")

        # Add each category
        for subsection in subsections:
            category_latex = self.convert_skill_category(subsection)
            lines.append(category_latex)
            lines.append("")

        lines.append("\\end{itemize}")

        return "\n".join(lines)

    def generate_page(self, page_data: Dict[str, Any]) -> str:
        """
        Generate complete page with paracol structure.

        Args:
            page_data: Dict with regions (top, left_column, main_column, bottom)

        Returns:
            LaTeX string for complete page
        """
        lines = []

        # Start paracol
        lines.append(PagePatterns.BEGIN_PARACOL)
        lines.append("")

        # Generate left column
        if page_data.get("left_column"):
            left_column = page_data["left_column"]
            for section_data in left_column.get("sections", []):
                section_latex = self._generate_section(section_data)
                lines.append(section_latex)
                lines.append("")

        # Switch to main column
        lines.append(PagePatterns.SWITCHCOLUMN)
        lines.append("")

        # Generate main column
        if page_data.get("main_column"):
            main_column = page_data["main_column"]
            for section_data in main_column.get("sections", []):
                section_latex = self._generate_section(section_data)
                lines.append(section_latex)
                lines.append("")

        # End paracol
        lines.append(PagePatterns.END_PARACOL)

        return "\n".join(lines)

    def _generate_section(self, section_data: Dict[str, Any]) -> str:
        """
        Generate LaTeX for a single section.

        Args:
            section_data: Dict with name, type, and content/subsections

        Returns:
            LaTeX string for section
        """
        lines = []

        # Section header
        section_name = section_data["name"]
        lines.append(f"{SectionPatterns.SECTION_STAR}{{{section_name}}}")
        lines.append("")

        # Generate content based on type
        section_type = section_data["type"]

        if section_type == "skill_list_caps":
            content_latex = self.convert_skill_list_caps({"content": section_data["content"]})
            lines.append(content_latex)

        elif section_type == "skill_list_pipes":
            content_latex = self.convert_skill_list_pipes({"content": section_data["content"]})
            lines.append(content_latex)

        elif section_type == "skill_categories":
            content_latex = self.convert_skill_categories({"subsections": section_data["subsections"]})
            lines.append(content_latex)

        elif section_type == "work_history":
            # Generate all work experience subsections
            for subsection in section_data.get("subsections", []):
                subsection_latex = self.convert_work_experience(subsection)
                lines.append(subsection_latex)
                lines.append("")

        else:
            # Unknown type - skip or add placeholder
            lines.append(f"% Unknown section type: {section_type}")

        return "\n".join(lines)


class LaTeXToYAMLConverter:
    """Converts LaTeX to structured YAML format."""

    def __init__(self, type_registry: TypeRegistry = None):
        self.registry = type_registry or TypeRegistry()

    def extract_document_metadata(self, latex_str: str) -> Dict[str, Any]:
        """
        Extract document metadata from preamble (before \\begin{document}).

        Parses \\renewcommand fields and color definitions.

        Args:
            latex_str: Full LaTeX document source

        Returns:
            Dictionary with metadata fields:
            - name: Full name (from \\myname)
            - date: Date (from \\mydate)
            - brand: Professional brand/title (from \\brand)
            - professional_profile: Profile text (from \\ProfessionalProfile, optional)
            - colors: Dict of color definitions
            - fields: Dict of all other \\renewcommand fields
        """
        import re

        # Find preamble (everything before \begin{document})
        doc_match = re.search(re.escape(DocumentPatterns.BEGIN_DOCUMENT), latex_str)
        if not doc_match:
            raise ValueError(f"No {DocumentPatterns.BEGIN_DOCUMENT} found")

        preamble = latex_str[:doc_match.start()]

        # Extract all \renewcommand fields (handle nested braces)
        renewcommands = {}
        renewcommand_pattern = re.escape(MetadataPatterns.RENEWCOMMAND) + r'\{\\'
        renewcommand_starts = [m.start() for m in re.finditer(renewcommand_pattern, preamble)]

        for start_pos in renewcommand_starts:
            # Extract field name (first {...})
            field_name_pattern = re.escape(MetadataPatterns.RENEWCOMMAND) + r'\{\\([^}]+)\}'
            field_name_match = re.match(field_name_pattern, preamble[start_pos:])
            if not field_name_match:
                continue
            field_name = field_name_match.group(1)

            # Find start of value (second {...})
            value_start = start_pos + field_name_match.end()
            if value_start >= len(preamble) or preamble[value_start] != '{':
                continue

            # Extract value with proper brace counting
            brace_count = 0
            pos = value_start
            while pos < len(preamble):
                if preamble[pos] == '\\':
                    pos += 2  # Skip escaped character
                    continue
                elif preamble[pos] == '{':
                    brace_count += 1
                elif preamble[pos] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        field_value = preamble[value_start + 1:pos]
                        renewcommands[field_name] = field_value
                        break
                pos += 1

        # Color fields
        colors = {k: renewcommands.pop(k) for k in ColorFields.all() if k in renewcommands}

        # Known metadata fields
        name = renewcommands.pop(MetadataPatterns.MYNAME, '')
        date = renewcommands.pop(MetadataPatterns.MYDATE, '')
        brand = renewcommands.pop(MetadataPatterns.BRAND, '')
        professional_profile = renewcommands.pop(MetadataPatterns.PROFESSIONAL_PROFILE, None)

        # Clean up name (remove \textbf{...})
        textbf_pattern = re.escape(FormattingPatterns.TEXTBF) + r'\{([^}]+)\}'
        name_match = re.search(textbf_pattern, name)
        if name_match:
            name = name_match.group(1)

        # Clean up professional profile (remove \centering, \textbf, \par)
        if professional_profile:
            professional_profile = re.sub(re.escape(FormattingPatterns.CENTERING) + r'\s*', '', professional_profile)
            professional_profile = re.sub(textbf_pattern, r'\1', professional_profile)
            professional_profile = re.sub(re.escape(FormattingPatterns.PAR) + r'\s*$', '', professional_profile)
            professional_profile = professional_profile.strip()

        return {
            'name': name,
            'date': date,
            'brand': brand,
            'professional_profile': professional_profile,
            'colors': colors,
            'fields': renewcommands  # All other fields
        }

    def _extract_braced_params(self, latex_str: str, start_pos: int, num_params: int) -> List[str]:
        """
        Extract N brace-delimited parameters starting from position.

        Args:
            latex_str: LaTeX source
            start_pos: Position to start searching
            num_params: Number of {...} parameters to extract

        Returns:
            List of extracted parameter values
        """
        params = []
        pos = start_pos

        for _ in range(num_params):
            # Find opening brace
            while pos < len(latex_str) and latex_str[pos] != '{':
                pos += 1

            if pos >= len(latex_str):
                break

            # Count braces to find matching close
            pos += 1  # Skip opening brace
            brace_count = 1
            param_start = pos

            while pos < len(latex_str) and brace_count > 0:
                if latex_str[pos] == '\\':
                    pos += 2  # Skip escaped char
                    continue
                elif latex_str[pos] == '{':
                    brace_count += 1
                elif latex_str[pos] == '}':
                    brace_count -= 1
                pos += 1

            if brace_count == 0:
                param_value = latex_str[param_start:pos-1]
                params.append(param_value)

        return params

    def parse_work_experience(self, latex_str: str) -> Dict[str, Any]:
        """
        Parse LaTeX itemizeAcademic environment to structured YAML.

        Args:
            latex_str: LaTeX source for work experience subsection

        Returns:
            Dict matching YAML structure
        """
        import re

        # Find \begin{itemizeAcademic}{...}{...}{...}{...}
        begin_pattern = re.escape(EnvironmentPatterns.BEGIN_ITEMIZE_ACADEMIC)
        begin_match = re.search(begin_pattern, latex_str)
        if not begin_match:
            raise ValueError(f"No {EnvironmentPatterns.BEGIN_ITEMIZE_ACADEMIC} environment found")

        # Extract 4 parameters: company, title, location, dates
        params = self._extract_braced_params(latex_str, begin_match.end(), 4)
        if len(params) < 4:
            raise ValueError(f"Expected 4 parameters, found {len(params)}")

        company, title, location, dates = params

        # Check if title has subtitle (contains \\)
        subtitle = None
        if '\\\\' in title:
            parts = title.split('\\\\', 1)
            title = parts[0]
            subtitle = parts[1] if len(parts) > 1 else None

        # Find end of environment
        end_pattern = re.escape(EnvironmentPatterns.END_ITEMIZE_ACADEMIC)
        end_match = re.search(end_pattern, latex_str)
        if not end_match:
            raise ValueError(f"No matching {EnvironmentPatterns.END_ITEMIZE_ACADEMIC} found")

        content_section = latex_str[begin_match.end():end_match.start()]

        # Extract bullets and projects
        bullets = []
        projects = []

        # Find all \itemi bullets (not inside nested environments)
        # and all nested itemizeAProject environments
        pos = 0
        while pos < len(content_section):
            # Check for \itemi
            itemi_match = re.search(r'\\itemi\s+', content_section[pos:])
            project_match = re.search(r'\\begin\{itemizeAProject\}', content_section[pos:])

            # Determine which comes first
            itemi_pos = itemi_match.start() + pos if itemi_match else float('inf')
            project_pos = project_match.start() + pos if project_match else float('inf')

            if itemi_pos < project_pos:
                # Found bullet first
                bullet_start = itemi_pos + len('\\itemi')

                # Find where bullet ends (next \itemi, \begin, or \end)
                next_item = re.search(
                    r'\\(itemi|begin\{itemizeAProject\}|end\{itemizeAcademic\})',
                    content_section[bullet_start:]
                )

                if next_item:
                    bullet_text = content_section[bullet_start:bullet_start + next_item.start()].strip()
                else:
                    bullet_text = content_section[bullet_start:].strip()

                bullets.append({"text": bullet_text})
                pos = bullet_start + (next_item.start() if next_item else len(content_section[bullet_start:]))

            elif project_pos < float('inf'):
                # Found project first
                project_data = self._parse_project(content_section[project_pos:])
                projects.append(project_data)

                # Find end of this project
                project_end = re.search(r'\\end\{itemizeAProject\}', content_section[project_pos:])
                if project_end:
                    pos = project_pos + project_end.end()
                else:
                    break
            else:
                # No more items
                break

        # Build result
        result = {
            "type": "work_experience",
            "metadata": {
                "company": company,
                "title": title,
                "location": location,
                "dates": dates,
            },
            "content": {
                "bullets": bullets,
            }
        }

        if subtitle:
            result["metadata"]["subtitle"] = subtitle

        if projects:
            result["content"]["projects"] = projects

        return result

    def _parse_project(self, latex_str: str) -> Dict[str, Any]:
        """Parse itemizeAProject environment."""
        import re

        begin_match = re.search(r'\\begin\{itemizeAProject\}', latex_str)
        if not begin_match:
            raise ValueError("No itemizeAProject environment found")

        # Extract 3 parameters: bullet_symbol, name, dates
        params = self._extract_braced_params(latex_str, begin_match.end(), 3)
        if len(params) < 3:
            raise ValueError(f"Expected 3 parameters for project, found {len(params)}")

        bullet_symbol, name, dates = params

        # Find end
        end_match = re.search(r'\\end\{itemizeAProject\}', latex_str)
        if not end_match:
            raise ValueError("No matching \\end{itemizeAProject} found")

        content = latex_str[begin_match.end():end_match.start()]

        # Extract \itemii bullets - find each \itemii and capture until next \itemii or end
        bullets = []
        pos = 0
        while True:
            itemii_match = re.search(r'\\itemii\s+', content[pos:])
            if not itemii_match:
                break

            bullet_start = pos + itemii_match.end()

            # Find next \itemii or end of content
            next_itemii = re.search(r'\\itemii\s+', content[bullet_start:])
            if next_itemii:
                bullet_end = bullet_start + next_itemii.start()
            else:
                bullet_end = len(content)

            bullet_text = content[bullet_start:bullet_end].strip()
            bullets.append({"text": bullet_text})

            pos = bullet_start

        return {
            "type": "project",
            "metadata": {
                "name": name,
                "bullet_symbol": bullet_symbol,
                "dates": dates,
            },
            "bullets": bullets,
        }

    def parse_skill_list_caps(self, latex_str: str) -> Dict[str, Any]:
        """
        Parse skill_list_caps section (e.g., Core Skills).

        Format: { \setlength{...} \scshape
                  Item 1

                  Item 2\\With Line Break

                  Item 3
                }

        Args:
            latex_str: LaTeX source for skill list section

        Returns:
            Dict matching YAML structure
        """
        import re

        # Find opening brace with spacing commands and \scshape
        pattern = r'\{\s*\\setlength\{\\baselineskip\}.*?\\scshape\s*'
        match = re.search(pattern, latex_str, re.DOTALL)

        if not match:
            raise ValueError("No skill_list_caps pattern found")

        content_start = match.end()

        # Find matching closing brace
        brace_count = 1  # Already inside the opening brace
        pos = content_start

        while pos < len(latex_str) and brace_count > 0:
            if latex_str[pos] == '\\':
                pos += 2
                continue
            elif latex_str[pos] == '{':
                brace_count += 1
            elif latex_str[pos] == '}':
                brace_count -= 1
            pos += 1

        if brace_count != 0:
            raise ValueError("Unmatched braces in skill_list_caps")

        content = latex_str[content_start:pos-1]

        # Split on blank lines or \par to get individual items
        # Items can contain \\ for line breaks
        items = []
        for item in re.split(r'\n\s*\n|\\par\s*', content):
            item = item.strip()
            if item:
                items.append(item)

        return {
            "type": "skill_list_caps",
            "content": {
                "list": items
            }
        }

    def parse_skill_list_pipes(self, latex_str: str) -> Dict[str, Any]:
        """
        Parse skill_list_pipes section (e.g., Languages, Hardware).

        Format: \texttt{Python} | \texttt{Bash} | \texttt{C++} \\
                \texttt{MATLAB} | \texttt{Mathematica}

        Args:
            latex_str: LaTeX source for pipe-separated skill list

        Returns:
            Dict matching YAML structure
        """
        import re

        # Find all \texttt{...} instances
        items = []
        pattern = r'\\texttt\{([^}]+)\}'

        for match in re.finditer(pattern, latex_str):
            item = match.group(1)
            items.append(item)

        if not items:
            raise ValueError("No \\texttt{} items found in skill_list_pipes")

        return {
            "type": "skill_list_pipes",
            "content": {
                "list": items
            }
        }

    def _parse_skill_category(self, latex_str: str) -> Dict[str, Any]:
        """
        Parse individual skill_category (child element).

        Format: \item[\faIcon] {\scshape Category Name}
                \begin{itemizeLL}
                    \itemLL {Item 1}
                    \itemLL {Item 2}
                \end{itemizeLL}

        Args:
            latex_str: LaTeX source for single category

        Returns:
            Dict matching YAML structure
        """
        import re

        # Extract icon and name from \item[icon] {\scshape name}
        item_pattern = r'\\item\[([^\]]*)\]\s*\{\\scshape\s+([^}]+)\}'
        item_match = re.search(item_pattern, latex_str)

        if not item_match:
            raise ValueError("No \\item[icon] {\\scshape name} pattern found")

        icon = item_match.group(1).strip()
        name = item_match.group(2).strip()

        # Find itemizeLL environment
        begin_match = re.search(r'\\begin\{itemizeLL\}', latex_str)
        end_match = re.search(r'\\end\{itemizeLL\}', latex_str)

        if not begin_match or not end_match:
            raise ValueError("No itemizeLL environment found")

        itemize_content = latex_str[begin_match.end():end_match.start()]

        # Extract \itemLL items
        items = []
        itemll_pattern = r'\\itemLL\s*\{([^}]+)\}'
        for match in re.finditer(itemll_pattern, itemize_content):
            items.append(match.group(1).strip())

        result = {
            "type": "skill_category",
            "metadata": {
                "name": name,
            },
            "content": {
                "list": items
            }
        }

        if icon:
            result["metadata"]["icon"] = icon

        return result

    def parse_skill_categories(self, latex_str: str) -> Dict[str, Any]:
        """
        Parse skill_categories section (parent with multiple categories).

        Format: \begin{itemize}[params]
                    \item[icon1] {\scshape Category 1}
                    \begin{itemizeLL}...

                    \item[icon2] {\scshape Category 2}
                    \begin{itemizeLL}...
                \end{itemize}

        Args:
            latex_str: LaTeX source for skill categories section

        Returns:
            Dict matching YAML structure
        """
        import re

        # Find outermost itemize environment
        begin_match = re.search(r'\\begin\{itemize\}', latex_str)
        if not begin_match:
            raise ValueError("No \\begin{itemize} found")

        # Find matching \end{itemize}
        # Need to handle nested itemizeLL environments
        pos = begin_match.end()
        depth = 1
        end_pos = pos

        while pos < len(latex_str) and depth > 0:
            begin_nested = re.search(r'\\begin\{itemize', latex_str[pos:])
            end_nested = re.search(r'\\end\{itemize', latex_str[pos:])

            if end_nested:
                if begin_nested and begin_nested.start() < end_nested.start():
                    depth += 1
                    pos += begin_nested.end()
                else:
                    depth -= 1
                    if depth == 0:
                        end_pos = pos + end_nested.start()
                    pos += end_nested.end()
            else:
                break

        if depth != 0:
            raise ValueError("Unmatched \\begin{itemize}")

        itemize_content = latex_str[begin_match.end():end_pos]

        # Split on \item[ to find individual categories
        # Each category starts with \item[icon]
        categories = []
        item_positions = []

        for match in re.finditer(r'\\item\[', itemize_content):
            item_positions.append(match.start())

        # Extract each category block
        for i, start_pos in enumerate(item_positions):
            if i + 1 < len(item_positions):
                end_pos = item_positions[i + 1]
            else:
                end_pos = len(itemize_content)

            category_block = itemize_content[start_pos:end_pos]
            category = self._parse_skill_category(category_block)
            categories.append(category)

        return {
            "type": "skill_categories",
            "subsections": categories
        }

    def extract_pages(self, latex_str: str) -> List[Dict[str, Any]]:
        """
        Extract all pages from LaTeX document content (between \\begin{document} and \\end{document}).

        Splits on \\clearpage markers to get individual pages.
        Handles paracol environments that span multiple pages.

        Args:
            latex_str: Full LaTeX document source

        Returns:
            List of page dicts, each with page_number and regions
        """
        import re

        # Find document content (between \begin{document} and \end{document})
        doc_start_pattern = re.escape(DocumentPatterns.BEGIN_DOCUMENT)
        doc_end_pattern = re.escape(DocumentPatterns.END_DOCUMENT)
        doc_start = re.search(doc_start_pattern, latex_str)
        doc_end = re.search(doc_end_pattern, latex_str)

        if not doc_start or not doc_end:
            raise ValueError("Document markers not found")

        document_content = latex_str[doc_start.end():doc_end.start()]

        # Find paracol environment boundaries
        paracol_start_pattern = re.escape(PagePatterns.BEGIN_PARACOL)
        paracol_end_pattern = re.escape(PagePatterns.END_PARACOL)
        paracol_start_match = re.search(paracol_start_pattern, document_content)
        paracol_end_match = re.search(paracol_end_pattern, document_content)

        if not paracol_start_match or not paracol_end_match:
            raise ValueError("No paracol environment found")

        # Extract content within paracol (this is what we'll split on \clearpage)
        paracol_content = document_content[paracol_start_match.end():paracol_end_match.start()]

        # Split on \clearpage to get pages
        clearpage_pattern = re.escape(DocumentPatterns.CLEARPAGE) + r'\s*'
        page_segments = re.split(clearpage_pattern, paracol_content)

        pages = []
        for page_num, page_content in enumerate(page_segments, start=1):
            if not page_content.strip():
                continue

            # Wrap segment in paracol for extract_page_regions() to work
            wrapped_content = f"{PagePatterns.BEGIN_PARACOL}\n{page_content}\n{PagePatterns.END_PARACOL}"

            try:
                # Extract regions for this page
                page_regions = self.extract_page_regions(wrapped_content, page_number=page_num)
                pages.append({
                    "page_number": page_num,
                    "regions": page_regions
                })
            except ValueError as e:
                # Page doesn't have valid structure
                continue

        return pages

    def extract_page_regions(self, latex_str: str, page_number: int = 1) -> Dict[str, Any]:
        """
        Extract page regions from LaTeX content (paracol structure).

        Finds \begin{paracol}{2}...\end{paracol} and splits on \switchcolumn.

        Args:
            latex_str: LaTeX source for single page
            page_number: Page number (1-indexed)

        Returns:
            Dict with top, left_column, main_column, bottom regions
        """
        import re

        # Find paracol environment
        paracol_pattern = re.escape(PagePatterns.BEGIN_PARACOL)
        paracol_match = re.search(paracol_pattern, latex_str)
        if not paracol_match:
            raise ValueError(f"No {PagePatterns.BEGIN_PARACOL} found")

        paracol_start = paracol_match.end()

        # Find \end{paracol}
        end_pattern = re.escape(PagePatterns.END_PARACOL)
        end_match = re.search(end_pattern, latex_str[paracol_start:])
        if not end_match:
            raise ValueError(f"No matching {PagePatterns.END_PARACOL} found")

        paracol_content = latex_str[paracol_start:paracol_start + end_match.start()]

        # Find \switchcolumn (optional for continuation pages)
        switch_pattern = re.escape(PagePatterns.SWITCHCOLUMN)
        switch_match = re.search(switch_pattern, paracol_content)

        if switch_match:
            # Has both columns
            left_content = paracol_content[:switch_match.start()].strip()
            main_content = paracol_content[switch_match.end():].strip()

            left_sections = self._extract_sections_from_column(left_content)
            main_sections = self._extract_sections_from_column(main_content)
        else:
            # No switchcolumn - all content is in main column (continuation page)
            left_sections = []
            main_sections = self._extract_sections_from_column(paracol_content.strip())

        return {
            "top": {
                "show_professional_profile": (page_number == 1)
            },
            "left_column": {
                "sections": left_sections
            } if left_sections else None,
            "main_column": {
                "sections": main_sections
            } if main_sections else None,
            "bottom": None  # TODO: Implement bottom bar extraction
        }

    def _extract_sections_from_column(self, column_content: str) -> List[Dict[str, Any]]:
        """
        Extract all sections from column content.

        Args:
            column_content: LaTeX content for a single column

        Returns:
            List of section dicts
        """
        import re

        sections = []

        # Find all \section* markers
        section_pattern = r'\\section\*?\{([^}]+)\}'
        section_matches = list(re.finditer(section_pattern, column_content))

        if not section_matches:
            return sections

        for i, match in enumerate(section_matches):
            section_name = match.group(1).strip()

            # Get content from after this section to before next section
            content_start = match.end()
            if i + 1 < len(section_matches):
                content_end = section_matches[i + 1].start()
            else:
                content_end = len(column_content)

            section_content = column_content[content_start:content_end].strip()

            # Infer type and parse section
            section_dict = self._parse_section_by_inference(section_name, section_content)
            sections.append(section_dict)

        return sections

    def _parse_section_by_inference(self, section_name: str, content: str) -> Dict[str, Any]:
        """
        Infer section type from content and parse accordingly.

        Args:
            section_name: Section name (e.g., "Core Skills")
            content: Section content LaTeX

        Returns:
            Section dict with type, name, and parsed content
        """
        import re

        # Try to infer type from content structure
        if EnvironmentPatterns.BEGIN_ITEMIZE_ACADEMIC in content:
            # Work experience section
            # Parse all work experience subsections
            subsections = []
            begin_pattern = re.escape(EnvironmentPatterns.BEGIN_ITEMIZE_ACADEMIC)
            for match in re.finditer(begin_pattern, content):
                # Find corresponding \end{itemizeAcademic}
                start = match.start()
                end_pattern = re.escape(EnvironmentPatterns.END_ITEMIZE_ACADEMIC)
                end_match = re.search(end_pattern, content[start:])
                if end_match:
                    subsection_latex = content[start:start + end_match.end()]
                    subsection = self.parse_work_experience(subsection_latex)
                    subsections.append(subsection)

            return {
                "name": section_name,
                "type": "work_history",
                "subsections": subsections
            }

        elif r'\begin{itemize}' in content and r'\item[' in content and FormattingPatterns.SCSHAPE in content:
            # skill_categories
            parsed = self.parse_skill_categories(content)
            return {
                "name": section_name,
                "type": "skill_categories",
                "subsections": parsed["subsections"]
            }

        elif FormattingPatterns.SETLENGTH in content and FormattingPatterns.BASELINESKIP in content and FormattingPatterns.SCSHAPE in content:
            # skill_list_caps
            parsed = self.parse_skill_list_caps(content)
            return {
                "name": section_name,
                "type": "skill_list_caps",
                "content": parsed["content"]
            }

        elif FormattingPatterns.TEXTTT in content and '|' in content:
            # skill_list_pipes
            parsed = self.parse_skill_list_pipes(content)
            return {
                "name": section_name,
                "type": "skill_list_pipes",
                "content": parsed["content"]
            }

        else:
            # Unknown type - store as raw
            return {
                "name": section_name,
                "type": "unknown",
                "content": {"raw": content}
            }


def yaml_to_latex(yaml_path: Path, output_path: Path = None) -> str:
    """
    Convert YAML resume structure to LaTeX.

    Args:
        yaml_path: Path to YAML file
        output_path: Optional path to write LaTeX output

    Returns:
        Generated LaTeX string
    """
    yaml_data = OmegaConf.load(yaml_path)
    yaml_dict = OmegaConf.to_container(yaml_data, resolve=True)

    converter = YAMLToLaTeXConverter()

    # Handle different YAML structures
    if "subsection" in yaml_dict:
        # Minimal test case
        latex = converter.convert_work_experience(yaml_dict["subsection"])
    else:
        raise NotImplementedError("Full resume conversion not yet implemented")

    if output_path:
        output_path.write_text(latex, encoding="utf-8")

    return latex


def latex_to_yaml(latex_path: Path, output_path: Path = None) -> Dict[str, Any]:
    """
    Convert LaTeX resume to YAML structure.

    Args:
        latex_path: Path to LaTeX file
        output_path: Optional path to write YAML output

    Returns:
        Parsed YAML structure as dict
    """
    latex_str = latex_path.read_text(encoding="utf-8")

    converter = LaTeXToYAMLConverter()

    # Parse work experience subsection
    result = converter.parse_work_experience(latex_str)

    # Wrap in subsection key for consistency with test YAML
    yaml_dict = {"subsection": result}

    if output_path:
        conf = OmegaConf.create(yaml_dict)
        OmegaConf.save(conf, output_path)

    return yaml_dict
