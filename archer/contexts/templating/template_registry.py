import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound

load_dotenv()
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT"))


class TemplateRegistry:
    """
    Registry for loading and caching Jinja2 templates for LaTeX generation.

    Templates are stored in archer/contexts/templating/types/{type_name}/template.tex.jinja
    and use custom delimiters to avoid conflicts with LaTeX syntax:
    - Variable: <<< var >>>
    - Block: <%% block %%> / <% endblock %>
    """

    def __init__(self, types_base_path: Path = None):
        """
        Initialize the template registry.

        Args:
            types_base_path: Base path for type directories. Defaults to
                           archer/contexts/templating/types/
        """
        if types_base_path is None:
            types_base_path = PROJECT_ROOT / "archer" / "contexts" / "templating" / "types"

        self.types_base_path = types_base_path
        self._cache: Dict[str, Template] = {}

        # Create Jinja2 environment with custom delimiters to avoid LaTeX conflicts
        self.env = Environment(
            loader=FileSystemLoader(str(types_base_path)),
            # Custom delimiters to avoid LaTeX brace conflicts
            variable_start_string="<<<",
            variable_end_string=">>>",
            block_start_string="<%%",
            block_end_string="%%>",
            comment_start_string="<#",
            comment_end_string="#>",
            # Preserve whitespace (important for LaTeX)
            trim_blocks=False,
            lstrip_blocks=False,
            keep_trailing_newline=True,
        )

    def get_template(self, type_name: str) -> Template:
        """
        Get a template by type name, loading and caching it if necessary.

        Args:
            type_name: Name of the type (e.g., 'skill_list_caps')

        Returns:
            Jinja2 Template object

        Raises:
            TemplateNotFound: If template file doesn't exist
            TemplateSyntaxError: If template has Jinja2 syntax errors
        """
        # Check cache first
        if type_name in self._cache:
            return self._cache[type_name]

        # Load template from file
        template_path = f"{type_name}/template.tex.jinja"

        try:
            template = self.env.get_template(template_path)
        except TemplateNotFound as e:
            raise TemplateNotFound(
                f"Template not found for type '{type_name}' at {self.types_base_path / template_path}"
            ) from e

        # Cache and return
        self._cache[type_name] = template
        return template

    def get_template_path(self, type_name: str) -> Path:
        """
        Get the file path for a type's template.

        Args:
            type_name: Name of the type (e.g., 'skill_list_caps')

        Returns:
            Path to template file
        """
        return self.types_base_path / type_name / "template.tex.jinja"

    def clear_cache(self):
        """Clear the template cache."""
        self._cache.clear()

    def is_cached(self, type_name: str) -> bool:
        """
        Check if a template is in the cache.

        Args:
            type_name: Name of the type

        Returns:
            True if cached, False otherwise
        """
        return type_name in self._cache
