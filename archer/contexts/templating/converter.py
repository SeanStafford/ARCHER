"""
LaTeX <-> YAML Converter

Handles bidirectional conversion between structured YAML and LaTeX resume format.
Uses type definitions from data/resume_archive/structured/types/ to guide conversion.
"""

import os
from pathlib import Path
from typing import Any, Dict, List

from omegaconf import OmegaConf
from dotenv import load_dotenv

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


class LaTeXToYAMLConverter:
    """Converts LaTeX to structured YAML format."""

    def __init__(self, type_registry: TypeRegistry = None):
        self.registry = type_registry or TypeRegistry()

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
        begin_pattern = r'\\begin\{itemizeAcademic\}'
        begin_match = re.search(begin_pattern, latex_str)
        if not begin_match:
            raise ValueError("No \\begin{itemizeAcademic} environment found")

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
        end_pattern = r'\\end\{itemizeAcademic\}'
        end_match = re.search(end_pattern, latex_str)
        if not end_match:
            raise ValueError("No matching \\end{itemizeAcademic} found")

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
