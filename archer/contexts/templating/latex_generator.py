"""
LaTeX Generator

Converts structured YAML to LaTeX format.
"""

import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from omegaconf import OmegaConf

from archer.contexts.templating.latex_patterns import (
    ContactFieldPatterns,
    EnvironmentPatterns,
    PageRegex,
    regex_to_literal,
)
from archer.contexts.templating.registries import ParseConfigRegistry, TemplateRegistry
from archer.utils.latex_parsing_tools import format_latex_environment
from archer.utils.text_processing import prepend_without_overlap, set_max_consecutive_blank_lines

load_dotenv()
TEMPLATING_CONTEXT_PATH = Path(os.getenv("TEMPLATING_CONTEXT_PATH"))
USER_PROFILE_PATH = Path(os.getenv("USER_PROFILE_PATH"))


class YAMLToLaTeXConverter:
    """Converts structured YAML to LaTeX format."""

    def __init__(
        self,
        template_registry: TemplateRegistry = None,
        parse_config_registry: ParseConfigRegistry = None,
        profile_path: Path = USER_PROFILE_PATH,
    ):
        self.template_registry = template_registry or TemplateRegistry()
        self.parse_config_registry = parse_config_registry or ParseConfigRegistry()

        # Load user profile for contact info
        self.user_profile = OmegaConf.load(profile_path)

    def _generate_contact_info(self, metadata: Dict[str, Any]) -> str:
        """
        Generate LaTeX table rows for contact info header.

        Args:
            metadata: Resume metadata (may contain custom_contact_info override)

        Returns:
            LaTeX string with table rows for contact info
        """
        # Start with defaults from user profile
        contact_selection = list(self.user_profile.contact_selection)
        contact_registry = dict(self.user_profile.contact_registry)

        # Apply custom overrides from resume metadata if present
        custom = metadata.get("custom_contact_info", None)
        if custom is not None:
            if custom.get("selection") is not None:
                contact_selection = list(custom["selection"])
            if custom.get("registry") is not None:
                contact_registry.update(custom["registry"])

        # Load contact row template
        template_path = TEMPLATING_CONTEXT_PATH / "template/structure/contact_row.tex.jinja"
        template_content = template_path.read_text(encoding="utf-8")
        template = self.template_registry.env.from_string(template_content)

        rows = []
        for field in contact_selection:
            if field not in ContactFieldPatterns.IMPLEMENTED_FIELDS:
                raise ValueError(
                    f"Contact field '{field}' is not implemented. "
                    f"Valid fields: {ContactFieldPatterns.IMPLEMENTED_FIELDS}"
                )
            if field not in contact_registry:
                raise ValueError(
                    f"Contact field '{field}' not found in contact registry."
                )
            value = contact_registry[field]

            icon = ContactFieldPatterns.ICONS.get(field)
            link_prefix = ContactFieldPatterns.LINK_PREFIXES.get(field)

            # Build link if this field type has one
            has_link = link_prefix is not None
            link = prepend_without_overlap(link_prefix, value) if has_link else None

            row = template.render(value=value, icon=icon, has_link=has_link, link=link)
            rows.append(row.strip())

        return "\n".join(rows)

    def generate_preamble(self, metadata: Dict[str, Any]) -> str:
        """
        Generate complete LaTeX preamble from template.

        Args:
            metadata: Dictionary with metadata fields (name, date, brand, colors, etc.)

        Returns:
            Complete LaTeX preamble string
        """
        # Generate contact info rows
        contact_info = self._generate_contact_info(metadata)

        # Load preamble template directly (at root of templating directory)
        preamble_path = TEMPLATING_CONTEXT_PATH / "template/structure/preamble.tex.jinja"
        preamble_content = preamble_path.read_text(encoding="utf-8")
        template = self.template_registry.env.from_string(preamble_content)
        return template.render(metadata=metadata, contact_info_rows=contact_info)

    def generate_document(self, doc: Dict[str, Any]) -> str:
        """
        Generate complete LaTeX document from structured format.

        Args:
            doc: Dict with "document" key containing metadata and pages

        Returns:
            Complete LaTeX document string
        """
        document = doc["document"]
        metadata = document["metadata"]
        pages = document["pages"]

        # Generate preamble
        preamble = self.generate_preamble(metadata)

        # Pre-render all sections for each page
        pages_with_rendered_sections = []
        for page in pages:
            rendered_page = {
                "regions": {
                    "top": page["regions"].get("top", {}),
                    "left_column": {"sections": []},
                    "main_column": {"sections": []},
                    "textblock_literal": None,
                    "decorations": page["regions"].get("decorations"),
                },
                "has_clearpage_after": page.get("has_clearpage_after", False),
            }

            # Render left column sections
            if page["regions"].get("left_column"):
                for section_data in page["regions"]["left_column"]["sections"]:
                    section_latex = self._generate_section(section_data)
                    rendered_page["regions"]["left_column"]["sections"].append(section_latex)

            # Render main column sections
            if page["regions"].get("main_column"):
                for section_data in page["regions"]["main_column"]["sections"]:
                    section_latex = self._generate_section(section_data)
                    rendered_page["regions"]["main_column"]["sections"].append(section_latex)

            # Render textblock literal if present (just pass through verbatim)
            if page["regions"].get("textblock_literal"):
                rendered_page["regions"]["textblock_literal"] = self.generate_textblock_literal(
                    page["regions"]["textblock_literal"]
                )

            # Render decorations if present
            if page["regions"].get("decorations"):
                rendered_decorations = []
                for decoration in page["regions"]["decorations"]:
                    decoration_latex = self._generate_decoration(
                        decoration, page["regions"].get("textblock_literal")
                    )
                    if decoration_latex:
                        rendered_decorations.append(decoration_latex)
                rendered_page["regions"]["decorations"] = (
                    rendered_decorations if rendered_decorations else None
                )

            pages_with_rendered_sections.append(rendered_page)

        # Load and render document template
        document_template_path = TEMPLATING_CONTEXT_PATH / "template/structure/document.tex.jinja"
        document_template_content = document_template_path.read_text(encoding="utf-8")
        document_template = self.template_registry.env.from_string(document_template_content)

        generated_latex = document_template.render(
            preamble=preamble, pages=pages_with_rendered_sections
        )

        # Ensure generated output follows normalization rules (max 1 blank line)
        # This aligns generation with normalization to produce consistent output
        return set_max_consecutive_blank_lines(generated_latex, max_consecutive=1)

    def convert_work_experience(self, subsection: Dict[str, Any]) -> str:
        """
        Convert work_experience subsection to LaTeX.

        Args:
            subsection: Dict with type, metadata, and content

        Returns:
            LaTeX string for itemizeAcademic environment
        """
        # Get environment name from parse config
        config = self.parse_config_registry.get_config("work_experience")
        latex_environment = config["operations"]["environment"]["env_name"]

        metadata = subsection["metadata"]
        content = subsection["content"]

        # Build title with optional subtitle
        title = metadata["title"]
        if "subtitle" in metadata and metadata["subtitle"]:
            title = f"{title}\\\\{metadata['subtitle']}"

        # Bullets now have marker and latex_raw from parser - pass through directly
        bullets = content.get("bullets", [])

        # Render projects
        rendered_projects = [
            self.convert_project(project, indent="        ")
            for project in content.get("projects", [])
        ]

        # Render template
        template = self.template_registry.get_template("work_experience")
        return template.render(
            latex_environment=latex_environment,
            metadata=metadata,
            title=title,
            bullets=bullets,
            rendered_projects=rendered_projects,
        )

    def convert_project(self, project: Dict[str, Any], indent: str = "") -> str:
        """
        Convert project subsection to LaTeX.

        Args:
            project: Dict with type, metadata, and content (with bullets)
            indent: Indentation string to prepend to each line

        Returns:
            LaTeX string for itemizeAProject environment
        """
        # Extract content structure
        content = project.get("content", {})

        # Prepare metadata with defaults
        metadata = project["metadata"].copy()
        if "bullet_symbol" not in metadata:
            metadata["bullet_symbol"] = "{{\\large $\\bullet$}}"
        if "dates" not in metadata:
            metadata["dates"] = ""

        # Use environment_type from metadata (set by parser), with hardcoded fallback
        # Parser always sets environment_type, so fallback is rarely used
        latex_environment = metadata.get("environment_type", "itemizeAProject")
        template = self.template_registry.get_template("project")
        return template.render(
            latex_environment=latex_environment, metadata=metadata, content=content, indent=indent
        )

    def convert_skill_list_caps(self, section: Dict[str, Any]) -> str:
        """
        Convert skill_list_caps section to LaTeX.

        Args:
            section: Dict with type and content (list of items)

        Returns:
            LaTeX string for skill list in braced format with small caps
        """
        template = self.template_registry.get_template("skill_list_caps")
        return template.render(section)

    def convert_skill_list_pipes(self, section: Dict[str, Any]) -> str:
        """
        Convert skill_list_pipes section to LaTeX.

        Args:
            section: Dict with type and content (list of items)

        Returns:
            LaTeX string for pipe-separated list with \\texttt{} wrapping
        """
        template = self.template_registry.get_template("skill_list_pipes")
        return template.render(section)

    def convert_skill_category(self, subsection: Dict[str, Any]) -> str:
        """
        Convert skill_category subsection to LaTeX.

        Args:
            subsection: Dict with type, metadata, and content

        Returns:
            LaTeX string for single category with icon and itemizeLL
        """
        template = self.template_registry.get_template("skill_category")
        return template.render(subsection)

    def convert_skill_categories(self, section: Dict[str, Any]) -> str:
        """
        Convert skill_categories section to LaTeX.

        Args:
            section: Dict with type and subsections

        Returns:
            LaTeX string for itemize with multiple categories
        """
        subsections = section["subsections"]

        # Render each category subsection
        rendered_categories = [
            self.convert_skill_category(subsection) for subsection in subsections
        ]

        # Render the main template with categories
        template = self.template_registry.get_template("skill_categories")
        return template.render(rendered_categories=rendered_categories)

    def convert_education(self, section: Dict[str, Any]) -> str:
        """
        Convert education section to LaTeX.

        Education content is static. Template uses metadata toggles to include/exclude
        optional dissertation and minor fields.

        Args:
            section: Dict with type and metadata (include_dissertation, include_minor)

        Returns:
            LaTeX string for education section
        """
        template = self.template_registry.get_template("education")
        return template.render(section)

    def convert_personality_alias_array(self, section: Dict[str, Any]) -> str:
        """
        Convert personality_alias_array section to LaTeX.

        Args:
            section: Dict with type and content (items list)

        Returns:
            LaTeX string for personality section with itemizeMain environment
        """
        template = self.template_registry.get_template("personality_alias_array")
        return template.render(section)

    def generate_textblock_literal(self, literal_data: Dict[str, Any]) -> str:
        """
        Generate LaTeX literal content for textblock.

        Textblock content is stored verbatim and regenerated as-is.
        Currently used for bottom bar "Two Truths and a Lie" section.

        Args:
            literal_data: Dict with content_latex (raw LaTeX string)

        Returns:
            LaTeX string (literal content, no template)
        """
        return literal_data.get("content_latex", "")

    def _generate_decoration(
        self, decoration: Dict[str, Any], textblock_content: Dict[str, Any] = None
    ) -> str:
        """
        Generate LaTeX for a single page decoration command.

        Args:
            decoration: Dict with command name and args
            textblock_content: Optional literal LaTeX content (for textblock wrapper)

        Returns:
            LaTeX command string
        """
        command = decoration["command"]
        args = decoration["args"]

        if command == "textblock":
            # Special handling: wrap LaTeX literal in textblock
            if textblock_content:
                inner_content = self.generate_textblock_literal(textblock_content)
                return format_latex_environment(
                    "textblock*", inner_content, mandatory_args=[args[0]], special_paren_arg=args[1]
                )
            return None
        else:
            # Simple commands: just render with args
            args_str = "".join(f"{{{arg}}}" for arg in args)
            return f"\\{command}{args_str}"

    def generate_page(self, page_data: Dict[str, Any]) -> str:
        """
        Generate complete page with paracol structure.

        Args:
            page_data: Dict with regions (top, left_column, main_column, bottom, decorations)

        Returns:
            LaTeX string for complete page
        """
        lines = []

        # Start paracol
        lines.append(regex_to_literal(PageRegex.BEGIN_PARACOL))
        lines.append("")

        # Generate page decorations (which have absolute positioning)
        # Render textblock + grad/bar commands at top of page
        if page_data.get("decorations"):
            for decoration in page_data["decorations"]:
                decoration_latex = self._generate_decoration(decoration, page_data.get("bottom"))
                if decoration_latex:
                    lines.append(decoration_latex)
            lines.append("")

        # Generate left column
        if page_data.get("left_column"):
            left_column = page_data["left_column"]
            for section_data in left_column.get("sections", []):
                section_latex = self._generate_section(section_data)
                lines.append(section_latex)
                lines.append("")

        # Switch to main column
        lines.append(regex_to_literal(PageRegex.SWITCHCOLUMN))
        lines.append("")

        # Generate main column
        if page_data.get("main_column"):
            main_column = page_data["main_column"]
            for section_data in main_column.get("sections", []):
                section_latex = self._generate_section(section_data)
                lines.append(section_latex)
                lines.append("")

        # End paracol
        lines.append(regex_to_literal(PageRegex.END_PARACOL))

        return "\n".join(lines)

    def _generate_section(self, section_data: Dict[str, Any]) -> str:
        """
        Generate LaTeX for a single section.

        Args:
            section_data: Dict with type, metadata (with name, name_plaintext, spacing_after), and content/subsections

        Returns:
            LaTeX string for section
        """
        # Generate type-specific content
        section_type = section_data["type"]

        if section_type == "skill_list_caps":
            content_latex = self.convert_skill_list_caps({"content": section_data["content"]})

        elif section_type == "skill_list_pipes":
            content_latex = self.convert_skill_list_pipes({"content": section_data["content"]})

        elif section_type == "skill_categories":
            content_latex = self.convert_skill_categories(
                {"subsections": section_data["subsections"]}
            )

        elif section_type == "education":
            content_latex = self.convert_education({"metadata": section_data["metadata"]})

        elif section_type == "personality_alias_array":
            content_latex = self.convert_personality_alias_array(
                {"content": section_data["content"], "metadata": section_data.get("metadata", {})}
            )

        elif section_type == "work_history":
            # Generate all work experience subsections
            subsections = []
            for subsection in section_data.get("subsections", []):
                subsection_latex = self.convert_work_experience(subsection)
                subsections.append(subsection_latex)

            # Wrap in outer itemize environment
            wrapper_path = (
                TEMPLATING_CONTEXT_PATH / "template/wrappers/work_history_wrapper.tex.jinja"
            )
            wrapper_content = wrapper_path.read_text(encoding="utf-8")
            wrapper_template = self.template_registry.env.from_string(wrapper_content)
            content_latex = wrapper_template.render(content="\n\n".join(subsections))

        elif section_type == "projects":
            # Standalone projects section (wrapped in itemizeProjMain)
            projects = []
            for project in section_data.get("subsections", []):
                project_latex = self.convert_project(project, indent="    ")
                projects.append(project_latex)

            # Wrap in itemizeProjMain environment
            content_latex = f"{regex_to_literal(EnvironmentPatterns.BEGIN_ITEMIZE_PROJ_MAIN)}\n\n"
            content_latex += "\n\n".join(projects)
            content_latex += f"\n\n{regex_to_literal(EnvironmentPatterns.END_ITEMIZE_PROJ_MAIN)}"

        elif section_type == "custom_itemize":
            # Vanilla itemize with optional params and custom markers
            template = self.template_registry.get_template("custom_itemize")
            content_latex = template.render(section_data)

        elif section_type == "simple_list":
            # Generic fallback type - use template-based generation
            template = self.template_registry.get_template("simple_list")
            content_latex = template.render(section_data)

        else:
            # Unknown type - output raw content if present
            if "content" in section_data and "raw" in section_data["content"]:
                content_latex = section_data["content"]["raw"]
            else:
                content_latex = f"% Unknown section type: {section_type}"

        # Wrap with section header and spacing using template
        section_wrapper_path = (
            TEMPLATING_CONTEXT_PATH / "template/wrappers/section_wrapper.tex.jinja"
        )
        section_wrapper_content = section_wrapper_path.read_text(encoding="utf-8")
        wrapper_template = self.template_registry.env.from_string(section_wrapper_content)

        # Extract metadata fields (metadata is required, name is required within it)
        metadata = section_data["metadata"]

        return wrapper_template.render(
            name=metadata["name"],
            content=content_latex,
            spacing_after=metadata.get("spacing_after"),  # spacing_after is optional
        )
