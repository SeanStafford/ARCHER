"""
Templating Registries

Centralized registries for loading and caching templates and parsing configs.
"""

import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, StrictUndefined, Template, TemplateNotFound
from omegaconf import OmegaConf

load_dotenv()
TYPES_PATH = Path(os.getenv("RESUME_COMPONENT_TYPES_PATH"))


class TemplateRegistry:
    """
    Registry for loading and caching Jinja2 templates for LaTeX generation.

    Templates are stored in archer/contexts/templating/template/types/{type_name}/template.tex.jinja
    and use custom delimiters to avoid conflicts with LaTeX syntax:
    - Variable: <<< var >>>
    - Block: <%% block %%> / <% endblock %>
    """

    def __init__(self, types_base_path: Path = None):
        """
        Initialize the template registry.

        Args:
            types_base_path: Base path for type directories. Defaults to
                           RESUME_COMPONENT_TYPES_PATH from environment
        """
        if types_base_path is None:
            types_base_path = TYPES_PATH

        self.types_base_path = types_base_path
        self._cache: Dict[str, Template] = {}

        # Create Jinja2 environment with custom delimiters to avoid LaTeX conflicts
        self.env = Environment(
            loader=FileSystemLoader(str(types_base_path)),
            # Catches silent failures
            undefined=StrictUndefined,
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

    def get_template_source(self, type_name: str) -> str:
        """
        Get the raw template source code for a type.

        Useful for showing expected patterns in error messages.

        Args:
            type_name: Name of the type

        Returns:
            Raw template source as string
        """
        template_path = self.get_template_path(type_name)

        if not template_path.exists():
            return f"Template not found: {template_path}"

        return template_path.read_text()

    def get_expected_pattern_preview(self, type_name: str, max_lines: int = 5) -> str:
        """
        Get a preview of the expected LaTeX pattern from template.

        Args:
            type_name: Name of the type
            max_lines: Maximum number of lines to show

        Returns:
            Preview of template showing expected pattern
        """
        source = self.get_template_source(type_name)
        lines = source.split("\n")

        if len(lines) <= max_lines:
            return source

        # Show first few lines with ellipsis
        preview_lines = lines[:max_lines]
        return "\n".join(preview_lines) + "\n..."


class ParseConfigRegistry:
    """
    Registry for loading and caching parsing configurations.

    Parsing configs are stored in archer/contexts/templating/types/{type_name}/parse_config.yaml
    and define regex patterns and extraction rules for converting LaTeX to YAML.
    """

    def __init__(self, types_base_path: Path = None):
        """
        Initialize the parse config registry.

        Args:
            types_base_path: Base path for type directories. Defaults to
                           RESUME_COMPONENT_TYPES_PATH from environment
        """
        if types_base_path is None:
            types_base_path = TYPES_PATH

        self.types_base_path = types_base_path
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_config(self, type_name: str) -> Dict[str, Any]:
        """
        Get a parsing config by type name, loading and caching it if necessary.

        Args:
            type_name: Name of the type (e.g., 'skill_list_pipes')

        Returns:
            Dict containing parsing configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        if type_name in self._cache:
            return self._cache[type_name]

        config_path = self.get_config_path(type_name)

        if not config_path.exists():
            raise FileNotFoundError(
                f"Parse config not found for type '{type_name}' at {config_path}"
            )

        config = OmegaConf.load(config_path)
        config_dict = OmegaConf.to_container(config, resolve=True)

        self._cache[type_name] = config_dict
        return config_dict

    def get_config_path(self, type_name: str) -> Path:
        """
        Get the file path for a type's parsing config.

        Args:
            type_name: Name of the type (e.g., 'skill_list_pipes')

        Returns:
            Path to parse_config.yaml file
        """
        return self.types_base_path / type_name / "parse_config.yaml"

    def clear_cache(self):
        """Clear the parsing config cache."""
        self._cache.clear()

    def is_cached(self, type_name: str) -> bool:
        """
        Check if a parsing config is in the cache.

        Args:
            type_name: Name of the type

        Returns:
            True if cached, False otherwise
        """
        return type_name in self._cache
