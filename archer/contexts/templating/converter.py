"""LaTeX <-> YAML converter"""

import os
from pathlib import Path
from typing import Any, Dict

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
        """Convert work_experience subsection to LaTeX itemizeAcademic environment."""
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
        """Convert project subsection to LaTeX itemizeAProject environment."""
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
        """Convert skill_list_caps to LaTeX braced format with small caps."""
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

