"""Custom exceptions for templating context with template references."""

from pathlib import Path
from typing import Optional


class TemplateParsingError(Exception):
    """
    Exception raised when LaTeX parsing fails with reference to expected template.

    Attributes:
        message: Error description
        type_name: Name of the type being parsed (e.g., 'skill_list_caps')
        template_path: Path to the template file that defines expected pattern
        latex_snippet: The LaTeX content that failed to parse
    """

    def __init__(
        self,
        message: str,
        type_name: Optional[str] = None,
        template_path: Optional[Path] = None,
        latex_snippet: Optional[str] = None,
    ):
        self.message = message
        self.type_name = type_name
        self.template_path = template_path
        self.latex_snippet = latex_snippet

        # Build enhanced error message
        parts = [message]

        if type_name and template_path:
            parts.append(f"\nExpected pattern from: {template_path}")
            parts.append(f"Type: {type_name}")

        if latex_snippet:
            # Truncate snippet if too long
            snippet = latex_snippet[:200] + "..." if len(latex_snippet) > 200 else latex_snippet
            parts.append(f"\nActual LaTeX:\n{snippet}")

        super().__init__("\n".join(parts))


class TemplateRenderError(Exception):
    """
    Exception raised when template rendering fails.

    Attributes:
        message: Error description
        type_name: Name of the type being rendered
        template_path: Path to the template file
        original_error: The original Jinja2 error
    """

    def __init__(
        self,
        message: str,
        type_name: Optional[str] = None,
        template_path: Optional[Path] = None,
        original_error: Optional[Exception] = None,
    ):
        self.message = message
        self.type_name = type_name
        self.template_path = template_path
        self.original_error = original_error

        # Build enhanced error message
        parts = [message]

        if type_name and template_path:
            parts.append(f"\nTemplate: {template_path}")
            parts.append(f"Type: {type_name}")

        if original_error:
            parts.append(f"\nOriginal error: {str(original_error)}")

        super().__init__("\n".join(parts))


class InvalidYAMLStructureError(ValueError):
    """
    Exception raised when YAML resume structure is invalid or missing required fields.

    This is raised when the YAML file doesn't conform to the expected resume document
    schema or is missing fields required for LaTeX generation.
    """

    @classmethod
    def incomplete_yaml(cls, original_error: Optional[Exception] = None) -> "InvalidYAMLStructureError":
        """
        Create exception for incomplete YAML that needs normalization.

        Used when YAML is missing fields that normalize_yaml() would add
        (e.g., colors, setlengths, plaintext/latex_raw pairs).

        Args:
            original_error: The underlying error that triggered this

        Returns:
            InvalidYAMLStructureError with helpful normalization instructions
        """
        message = (
            "This YAML file appears to be incomplete or missing required fields.\n\n"
            "Try normalizing it:\n"
            "    from archer.contexts.templating import normalize_yaml\n"
            "    yaml_dict = normalize_yaml(yaml_dict)\n"
            "    yaml_to_latex(yaml_path, output_path)\n\n"
            "Or use the CLI:\n"
            "    python scripts/convert_template.py clean <yaml_file>"
        )

        if original_error:
            message += f"\n\nOriginal error: {str(original_error)}"

        return cls(message)
