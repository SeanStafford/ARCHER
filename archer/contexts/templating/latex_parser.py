"""
LaTeX Parser

Converts LaTeX to structured YAML format.
"""

import re
import os
import copy
import warnings
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv

from archer.contexts.templating.latex_patterns import (
    regex_to_literal,
    DocumentRegex,
    PageRegex,
    SectionRegex,
    EnvironmentPatterns,
    MetadataPatterns,
    MetadataRegex,
    ColorFields,
    PreamblePatterns,
    FormattingPatterns,
    ContentPatterns,
)
from archer.contexts.templating.registries import TemplateRegistry, ParseConfigRegistry
from archer.contexts.templating.exceptions import TemplateParsingError
from archer.utils.text_processing import (
    extract_balanced_delimiters,
    set_max_consecutive_blank_lines,
    extract_regex_matches,
)
from archer.utils.latex_parsing_tools import (
    extract_brace_arguments,
    extract_environment_content,
    extract_environment,
    extract_all_environments,
    parse_itemize_content,
    parse_itemize_with_complex_markers,
    to_plaintext,
    skip_latex_arguments,
)

load_dotenv()
TYPES_PATH = Path(os.getenv("RESUME_COMPONENT_TYPES_PATH"))
TEMPLATING_CONTEXT_PATH = Path(os.getenv("TEMPLATING_CONTEXT_PATH"))


def get_nested_field(data: Dict, field_path: str) -> Any:
    """
    Helper to get nested fields using dot notation (e.g., 'content.list').

    Args:
        data: Dictionary to read from
        field_path: Dot-separated path (e.g., 'content.list')

    Returns:
        Value at the specified path, or None if path doesn't exist
    """
    keys = field_path.split('.')
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current

def get_content_to_parse(config, context, result, latex_str):
    """Get source content from context, result path, or default to latex_str."""
    source = config.get('source')
    source_path = config.get('source_path')

    if source:
        return context.get(source, latex_str)
    elif source_path:
        return get_nested_field(result, source_path)  # Already have this function!
    else:
        return latex_str

def set_nested_field(data: Dict, field_path: str, value: Any):
    """
    Helper to set nested fields using dot notation (e.g., 'content.list').

    Args:
        data: Dictionary to update
        field_path: Dot-separated path (e.g., 'content.list')
        value: Value to set at the path
    """
    keys = field_path.split('.')
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value

def set_output(value, config, context, result):
    """Store value in context and/or result based on config."""
    if config.get('output_context'):
        context[config['output_context']] = value
    elif config.get('output_paths'):
        # Map dict fields to multiple result paths
        output_paths = config['output_paths']
        if isinstance(value, dict):
            assert len(output_paths) == len(value.keys()), "the number of keys in value dict does not match number of output paths"
            # value is a dict, map each key to its output path
            for key, path in output_paths.items():
                if key in value:
                    set_nested_field(result, path, value[key])
        elif isinstance(value, list):
            # value is a list, assign each item to corresponding path
            # If list is shorter than output_paths, remaining paths get empty string
            # Example: work_experience splits title on \\ to get [title, subtitle]
            #          but some titles don't have \\, so we only get [title]
            #          In this case, subtitle should be "" not fail assertion
            for i, path in enumerate(output_paths):
                if i < len(value):
                    set_nested_field(result, path, value[i])
                else:
                    set_nested_field(result, path, "")
        else:
            raise ValueError(f"output_paths requires dict or list value, got {type(value)}")
    elif config.get('output_path'):
        set_nested_field(result, config['output_path'], value)
    else:
          raise ValueError(
              f"No output destination specified in pattern config. "
              f"Must provide one of: output_context, output_paths, or output_path"
          )

def get_patterns_to_parse(config):
    """
    Resolve all pattern constants referenced in config.

    Returns dict mapping 'key_without_suffix' -> resolved_pattern_value.
    Example: {'delimiter': '\\\\item\\[.*?\\]...', 'cleanup': '...'}

    For any key ending in '_pattern', looks up the constant from EnvironmentPatterns
    and returns it without the '_pattern' suffix.
    """
    resolved = {}
    for key, value in config.items():
        if key.endswith('_pattern'):
            # Get pattern constant from EnvironmentPatterns
            pattern_value = getattr(EnvironmentPatterns, value, None)
            if pattern_value is None:
                # Check if it looks like a constant name (ALL_CAPS_WITH_UNDERSCORES)
                if value.isupper() and '_' in value:
                    warnings.warn(f"Pattern constant '{value}' not found in EnvironmentPatterns, using as literal regex")
                pattern_value = value
            # Store without '_pattern' suffix (e.g., 'delimiter_pattern' -> 'delimiter')
            key_without_suffix = key[:-8]  # Remove '_pattern'
            resolved[key_without_suffix] = pattern_value
    return resolved

class LaTeXToYAMLConverter:
    """Converts LaTeX to structured YAML format."""

    def __init__(
        self,
        template_registry: TemplateRegistry = None,
        parse_config_registry: ParseConfigRegistry = None
    ):
        self.template_registry = template_registry or TemplateRegistry()
        self.parse_config_registry = parse_config_registry or ParseConfigRegistry()

    def _create_parsing_error(
        self,
        message: str,
        type_name: str,
        latex_snippet: str,
        show_template: bool = True
    ) -> TemplateParsingError:
        """
        Create an enhanced parsing error with template reference.

        Args:
            message: Error description
            type_name: Name of the type being parsed
            latex_snippet: The LaTeX that failed to parse
            show_template: Whether to include template path

        Returns:
            TemplateParsingError with enhanced context
        """
        template_path = self.template_registry.get_template_path(type_name) if show_template else None

        return TemplateParsingError(
            message=message,
            type_name=type_name,
            template_path=template_path,
            latex_snippet=latex_snippet
        )

    def parse_with_config(self, latex_str: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Operation-based parser using config to extract data from LaTeX.

        Supports 7 operations:
        1. set_literal - Set constant values
        2. extract_environment - Extract LaTeX environments with optional/mandatory params
        3. split - Split content with optional cleanup
        4. parse_itemize_content - Parse itemize list entries
        5. recursive_parse - Parse nested structures
        6. extract_braced_after_pattern - Find pattern, extract balanced braces
        7. extract_regex - Extract regex matches with named capture groups

        Args:
            latex_str: LaTeX source to parse
            config: Parsing configuration dict with operation definitions

        Returns:
            Parsed data structure matching the config's extraction rules
        """
        result = {}
        context = {}  # For intermediate results between operations

        for _, operation_config in config.get("operations", {}).items():
            operation = operation_config.get('operation')
            content_source = get_content_to_parse(operation_config, context, result, latex_str)
            patterns = get_patterns_to_parse(operation_config)  # Resolve all *_pattern constants
            value = None  # Will be set by each operation

            if operation == 'set_literal':
                # Set constant value
                value = operation_config['value']

            elif operation == 'extract_environment':
                # Extract environment content and parameters
                # env_name can be a single string or a list of strings
                env_names = operation_config['env_name']
                if isinstance(env_names, str):
                    env_names = [env_names]

                num_params = operation_config.get('num_params', 0)
                num_optional_params = operation_config.get('num_optional_params', 0)
                param_names = operation_config.get('param_names', [])
                capture_trailing = operation_config.get('capture_trailing_text', False)

                # Try each environment name until one succeeds
                last_error = None
                for env_name in env_names:
                    try:
                        env_params, env_content, _, end_start_pos = extract_environment(
                            content_source, env_name, num_params, num_optional_params
                        )
                        # Success - store the actual environment name found
                        actual_env_name = env_name
                        break
                    except Exception as e:
                        last_error = e
                        continue
                else:
                    # None of the environment names matched
                    raise ValueError(f"None of the environment names matched: {env_names}. Last error: {last_error}")

                # Store params in result if param_names specified
                if param_names:
                    assert len(param_names) == len(env_params), "len(param_names) must match the number of extracted parameters"
                    for i, param_name in enumerate(param_names):
                        set_nested_field(result, param_name, env_params[i])

                # Set value for output
                value = env_content

                # Store the actual environment name that matched (useful when env_name is a list)
                if isinstance(operation_config['env_name'], list):
                    set_nested_field(result, "metadata.environment_name", actual_env_name)

                # Capture trailing text after environment if requested
                if capture_trailing:
                    newline_pos = latex_str.find('\n', end_start_pos)
                    if newline_pos != -1:
                        trailing_text = latex_str[newline_pos + 1:].strip()
                        if trailing_text:
                            set_nested_field(result, "metadata.trailing_text", trailing_text)

            elif operation == 'split':
                # Generalized split operation

                delimiter = patterns.get('delimiter')
                # Wrap in lookahead if we want to keep the delimiter (not let it get consumed by regex matching)
                if operation_config.get('keep_delimiter', False):
                    delimiter = f'(?={delimiter})'

                # Split content
                parts = re.split(delimiter, content_source)

                # Clean up parts if cleanup_pattern provided
                cleanup_pattern = patterns.get('cleanup')
                if cleanup_pattern:
                    parts = [re.sub(cleanup_pattern, '', part) for part in parts]

                # Filter empty parts and set value
                value = [p.strip() for p in parts if p.strip()]

            elif operation == 'parse_itemize_content':
                # Parse itemize content using resolved marker pattern (with fallback)
                marker_pattern = patterns.get('marker', r'\\item\b')
                value = parse_itemize_content(content_source, marker_pattern)

            elif operation == 'recursive_parse':
                # Extract and recursively parse nested types
                output_path = operation_config['output_path']
                config_name = operation_config['config_name']

                # Check if input is already a list of chunks (from split operation)
                if isinstance(content_source, list):
                    # Input is already split chunks, parse each directly
                    chunks = content_source
                    nested_config = self.parse_config_registry.get_config(config_name)

                    nested_results = []
                    for chunk in chunks:
                        nested_result = self.parse_with_config(chunk, nested_config)
                        nested_results.append(nested_result)

                    if nested_results:
                        set_nested_field(result, output_path, nested_results)

                else:
                    # Extract all matching environments (with full LaTeX including begin/end)
                    environments = extract_all_environments(content_source, patterns.get('recursive'), include_env_command_in_positions=True)

                    if environments:
                        nested_config = self.parse_config_registry.get_config(config_name)
                        nested_results = []

                        # Clean input content by removing nested environments
                        cleaned_content = content_source
                        for env_name, _, _, begin_pos, end_pos in reversed(environments):
                            cleaned_content = cleaned_content[:begin_pos] + cleaned_content[end_pos:]

                        # Update context with cleaned content (for bullets extraction)
                        context['environment_content'] = cleaned_content

                        for env_name, _, _, begin_pos, end_pos in environments:
                            # Get full environment LaTeX (with begin/end tags)
                            nested_latex = content_source[begin_pos:end_pos]

                            # Substitute {{{PROJECT_ENVIRONMENT_NAME}}} if present in config
                            config_copy = copy.deepcopy(nested_config)
                            if 'operations' in config_copy and 'environment' in config_copy['operations']:
                                if config_copy['operations']['environment'].get('env_name') == '{{{PROJECT_ENVIRONMENT_NAME}}}':
                                    config_copy['operations']['environment']['env_name'] = env_name

                            # Parse recursively
                            nested_result = self.parse_with_config(nested_latex, config_copy)

                            # Add environment_type to metadata
                            if 'metadata' not in nested_result:
                                nested_result['metadata'] = {}
                            nested_result['metadata']['environment_type'] = env_name

                            nested_results.append(nested_result)

                        set_nested_field(result, output_path, nested_results)

            elif operation == 'extract_regex':
                # Extract all matches using regex with named capture groups
                matches = extract_regex_matches(content_source, patterns['regex'])

                # Determine output value based on match structure
                if operation_config.get('output_paths'):
                    # Mode: Single match, multiple named groups → dict
                    if matches:
                        value = matches[0]
                        # Validate all required capture groups are present
                        required_groups = set(operation_config['output_paths'].keys())
                        actual_groups = set(value.keys())
                        assert required_groups.issubset(actual_groups), \
                            f"Missing capture groups: {required_groups - actual_groups}"
                        
                elif matches and len(matches[0]) == 1:
                    # Single capture group per match → list of strings
                    field_name = list(matches[0].keys())[0]
                    value = [m[field_name] for m in matches]
                else:
                    # Multiple capture groups per match → list of dicts
                    value = matches

            elif operation == 'extract_braced_after_pattern':
                # Find pattern, then extract balanced braces after it
                pattern = patterns.get('search')
                match = re.search(patterns.get('search'), content_source)
                if not match:
                    raise ValueError(f"Pattern not found: {pattern}")

                value, _ = extract_balanced_delimiters( content_source, start_pos = match.end())

            elif operation == 'to_plaintext':
                # Convert LaTeX to plaintext
                # If source is a list, transform to list of dicts with {latex_raw, plaintext}
                # If source is a string, convert to plaintext string
                if isinstance(content_source, list):
                    value = [
                        {
                            "latex_raw": item,
                            "plaintext": to_plaintext(item)
                        }
                        for item in content_source
                    ]
                else:
                    value = to_plaintext(content_source)

            # Store output (unless it's recursive_parse which handles its own output)
            if operation != 'recursive_parse' and value is not None:
                set_output(value, operation_config, context, result)

        return result

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

        # Find preamble (everything before \begin{document})
        doc_match = re.search(DocumentRegex.BEGIN_DOCUMENT, latex_str)
        if not doc_match:
            raise ValueError(f"No \\begin{{document}} found")

        preamble = latex_str[:doc_match.start()]

        # Extract all \renewcommand fields (handle nested braces)
        renewcommands = {}
        renewcommand_starts = [m.start() for m in re.finditer(MetadataRegex.RENEWCOMMAND_START, preamble)]

        for start_pos in renewcommand_starts:
            # Extract field name (first {...})
            field_name_match = re.match(MetadataRegex.RENEWCOMMAND_FIELD, preamble[start_pos:])
            if not field_name_match:
                continue
            field_name = field_name_match.group(1)

            # Find start of value (second {...})
            value_start = start_pos + field_name_match.end()
            if value_start >= len(preamble) or preamble[value_start] != '{':
                continue

            # Extract value using balanced delimiter helper
            try:
                field_value, _ = extract_balanced_delimiters(preamble, value_start + 1)
                renewcommands[field_name] = field_value
            except ValueError:
                # Skip malformed \renewcommand
                continue

        # Extract \setlength parameters (same pattern as \renewcommand)
        setlengths = {}
        for match in re.finditer(MetadataRegex.SETLENGTH, preamble):
            param_name = match.group(1)
            param_value = match.group(2)
            setlengths[param_name] = param_value

        # Extract \deflen parameters
        deflens = {}
        for match in re.finditer(MetadataRegex.DEFLEN, preamble):
            param_name = match.group(1)
            param_value = match.group(2)
            deflens[param_name] = param_value

        # Extract \sethlcolor
        hlcolor = None
        hlcolor_match = re.search(MetadataRegex.SETHLCOLOR, preamble)
        if hlcolor_match:
            hlcolor = hlcolor_match.group(1)

        # Extract \def\nlinesPP{...}
        nlines_pp = None
        nlines_pp_match = re.search(MetadataRegex.NLINESPP, preamble)
        if nlines_pp_match:
            nlines_pp = int(nlines_pp_match.group(1))

        # Extract \toggletrue/false{list_title_after_name}
        list_title_after_name = True  # Default to true
        toggle_match = re.search(MetadataRegex.LIST_TITLE_AFTER_NAME, preamble)
        if toggle_match:
            list_title_after_name = (toggle_match.group(1) == 'true')

        # Extract custom package declarations (e.g., \usepackage{fontspec} + \newfontfamily)
        # Filter out standard packages that are generated by template
        standard_packages = PreamblePatterns.all()
        custom_packages = []
        for match in re.finditer(MetadataRegex.USEPACKAGE, preamble):
            package_line = match.group(0)
            # Check if this is a standard package (skip if it is)
            is_standard = any(f'{{{pkg}}}' in package_line for pkg in standard_packages)
            if not is_standard:
                custom_packages.append(package_line)
        for match in re.finditer(MetadataRegex.NEWFONTFAMILY, preamble):
            custom_packages.append(match.group(0))

        # Color fields
        colors = {k: renewcommands.pop(k) for k in ColorFields.all() if k in renewcommands}

        # Known metadata fields - store RAW (exact LaTeX)
        name_raw = renewcommands.pop(MetadataPatterns.MYNAME, '')
        date = renewcommands.pop(MetadataPatterns.MYDATE, '')
        brand_raw = renewcommands.pop(MetadataPatterns.BRAND, '')
        professional_profile_raw = renewcommands.pop(MetadataPatterns.PROFESSIONAL_PROFILE, None)

        # Apply minimal cleaning to professional_profile: limit consecutive blank lines
        if professional_profile_raw:
            professional_profile_raw = set_max_consecutive_blank_lines(professional_profile_raw, max_consecutive=0)

        # Create plaintext versions for fields that can contain LaTeX formatting
        # These will be used by Targeting context for decision-making
        name_plaintext = to_plaintext(name_raw) if name_raw else ''
        brand_plaintext = to_plaintext(brand_raw) if brand_raw else ''
        professional_profile_plaintext = to_plaintext(professional_profile_raw) if professional_profile_raw else None

        return {
            'name': name_raw,  # Raw LaTeX preserved for roundtrip
            'name_plaintext': name_plaintext,  # Plaintext for Targeting context
            'date': date,  # Already plaintext
            'brand': brand_raw,
            'brand_plaintext': brand_plaintext,
            'professional_profile': professional_profile_raw,
            'professional_profile_plaintext': professional_profile_plaintext,
            'nlines_pp': nlines_pp,  # Number of lines in professional profile
            'list_title_after_name': list_title_after_name,  # PhD display toggle
            'colors': colors,
            'hlcolor': hlcolor,
            'setlengths': setlengths,
            'deflens': deflens,
            'custom_packages': custom_packages if custom_packages else None,  # Custom \usepackage and font declarations
            'fields': renewcommands  # All other renewcommand fields
        }

    def parse_document(self, latex_str: str) -> Dict[str, Any]:
        """
        Parse complete LaTeX document to structured format.

        Args:
            latex_str: Full LaTeX document source

        Returns:
            Dict with document metadata and pages
        """
        # Extract document metadata from preamble
        metadata = self.extract_document_metadata(latex_str)

        # Extract all pages
        pages = self.extract_pages(latex_str)

        return {
            "document": {
                "metadata": metadata,
                "pages": pages
            }
        }

    def parse_work_experience(self, latex_str: str) -> Dict[str, Any]:
        return self.parse_section(latex_str, "work_experience")

    def parse_section(self, latex_str: str, section_type: str) -> Dict[str, Any]:
        """
        Generic section parser - loads config and delegates to parse_with_config().

        Use this for all standard section types. Only create specialized methods
        when custom post-processing logic is needed.

        Args:
            latex_str: LaTeX source for section
            section_type: Type name matching parse_config filename (e.g., "skill_list_caps")

        Returns:
            Parsed dict matching YAML structure defined in type's parse_config.yaml
        """
        config = self.parse_config_registry.get_config(section_type)
        return self.parse_with_config(latex_str, config)

    # Convenience aliases for common types (optional, can call parse_section directly)
    def parse_projects(self, latex_str: str) -> Dict[str, Any]:
        return self.parse_section(latex_str, "projects")

    def parse_skill_list_caps(self, latex_str: str) -> Dict[str, Any]:
        return self.parse_section(latex_str, "skill_list_caps")

    def parse_skill_list_pipes(self, latex_str: str) -> Dict[str, Any]:
        return self.parse_section(latex_str, "skill_list_pipes")

    def _parse_skill_category(self, latex_str: str) -> Dict[str, Any]:
        return self.parse_section(latex_str, "skill_category")

    def parse_skill_categories(self, latex_str: str) -> Dict[str, Any]:
        return self.parse_section(latex_str, "skill_categories")

    def parse_education(self, latex_str: str) -> Dict[str, Any]:
        """
        Parse education section.

        See: archer/contexts/templating/types/education/
             - type.yaml (schema with metadata toggles)
             - template.tex.jinja (static education content with conditionals)

        Education content is static across all resumes. Parser only detects
        presence of optional dissertation and minor fields, and bullet style.

        Args:
            latex_str: LaTeX source for education section

        Returns:
            Dict with type and metadata toggles (include_dissertation, include_minor, use_icon_bullets)
        """
        # Detect optional elements by their presence in LaTeX
        include_dissertation = "Dissertation" in latex_str
        include_minor = "Minor in Neuroscience" in latex_str

        # Detect bullet style: \item[\faUserGraduate] vs \itemi
        use_icon_bullets = bool(re.search(EnvironmentPatterns.EDUCATION_ICON_BULLET, latex_str))

        return {
            "type": "education",
            "metadata": {
                "include_dissertation": include_dissertation,
                "include_minor": include_minor,
                "use_icon_bullets": use_icon_bullets
            },
            "content": {}
        }

    def parse_personality_alias_array(self, latex_str: str) -> Dict[str, Any]:
        return self.parse_section(latex_str, "personality_alias_array")

    def _parse_as_custom_itemize(self, content: str) -> Dict[str, Any]:
        """
        Parse vanilla itemize environment with optional params and custom item markers.

        Handles standard \begin{itemize}[...] environments where optional parameters
        are specified in the document and each item can have a different custom marker.
        Used for sections like "HPC Highlights".

        Uses parse_itemize_with_complex_markers() utility to handle markers with
        nested braces like \item[\raisebox{-1pt}{>} 20,000].

        Args:
            content: Section content containing an itemize environment

        Returns:
            Dict with metadata (optional_params) and content (items list with per-item markers)

        Raises:
            ValueError: If itemize environment structure cannot be extracted
        """
        # Extract environment and optional params
        env_params, env_content, _, _ = extract_environment(
            content, "itemize", num_params=0, num_optional_params=1
        )

        # Parse items with balanced bracket matching for complex markers
        bullets = parse_itemize_with_complex_markers(env_content)

        result = {
            'type': 'custom_itemize',
            'metadata': {},
            'content': {'bullets': bullets}
        }

        # Add optional params if present
        if env_params and len(env_params) > 0:
            result['metadata']['optional_params'] = env_params[0]

        return result

    def _parse_as_simple_list(self, content: str) -> Dict[str, Any]:
        """
        Parse any itemize environment as a generic list (fallback type).

        This is a catch-all parser for itemize environments that don't match
        any known semantic type. All extraction patterns are defined in
        types/simple_list/parse_config.yaml.

        See: archer/contexts/templating/types/simple_list/
             - type.yaml (schema)
             - template.tex.jinja (generation template)
             - parse_config.yaml (parsing patterns)

        Args:
            content: Section content containing an itemize environment

        Returns:
            Dict with metadata (itemize_env, item_command) and content (items list)

        Raises:
            ValueError: If itemize environment structure cannot be extracted
        """
        config = self.parse_config_registry.get_config("simple_list")
        result = self.parse_with_config(content, config)

        # Validate extraction succeeded
        if "metadata" not in result or "itemize_env" not in result["metadata"]:
            raise ValueError(
                "Could not extract itemize environment structure. "
                "Check types/simple_list/parse_config.yaml patterns."
            )

        return result

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

        # Find document content (between \begin{document} and \end{document})
        doc_start = re.search(DocumentRegex.BEGIN_DOCUMENT, latex_str)
        doc_end = re.search(DocumentRegex.END_DOCUMENT, latex_str)

        if not doc_start or not doc_end:
            raise ValueError("Document markers not found")

        document_content = latex_str[doc_start.end():doc_end.start()]

        # Find paracol environment boundaries
        paracol_start_match = re.search(PageRegex.BEGIN_PARACOL, document_content)
        paracol_end_match = re.search(PageRegex.END_PARACOL, document_content)

        if not paracol_start_match or not paracol_end_match:
            raise ValueError("No paracol environment found")

        # Extract content within paracol (this is what we'll split on \clearpage)
        paracol_content = document_content[paracol_start_match.end():paracol_end_match.start()]

        # Count clearpage markers to determine which pages have clearpage after them
        clearpage_count = len(re.findall(DocumentRegex.CLEARPAGE_WITH_WHITESPACE, paracol_content))

        # Split on \clearpage to get pages
        page_segments = re.split(DocumentRegex.CLEARPAGE_WITH_WHITESPACE, paracol_content)

        pages = []
        for page_num, page_content in enumerate(page_segments, start=1):
            if not page_content.strip():
                continue

            # Wrap segment in paracol for extract_page_regions() to work
            wrapped_content = f"{regex_to_literal(PageRegex.BEGIN_PARACOL)}\n{page_content}\n{regex_to_literal(PageRegex.END_PARACOL)}"

            try:
                # Extract regions for this page
                page_regions = self.extract_page_regions(wrapped_content, page_number=page_num)

                # Determine if this page has clearpage after it
                # Pages 1 through clearpage_count have clearpage, remaining pages don't
                has_clearpage_after = (page_num <= clearpage_count)

                pages.append({
                    "page_number": page_num,
                    "regions": page_regions,
                    "has_clearpage_after": has_clearpage_after
                })
            except ValueError as e:
                # Page doesn't have valid structure
                continue

        return pages

    def _extract_and_remove_decorations(self, latex_str: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Extract page decorations (textblock + grad/bar commands) and remove from LaTeX.

        Decorations should be handled differerently than content.

        Args:
            latex_str: LaTeX source containing decorations

        Returns:
            Tuple of (cleaned_latex, decorations_list) where decorations is:
            [{"command": "textblock", "args": [...]}, {"command": "leftgrad", "args": [...]}, ...]
        """
        decorations = []

        # Extract textblock arguments if present
        textblock_match = re.search(EnvironmentPatterns.TEXTBLOCK_WITH_ARGS, latex_str)
        if textblock_match:
            # Group 1: {width}, Group 2: (x, y)
            width_arg = textblock_match.group(1).strip('{}')
            position_arg = textblock_match.group(2).strip('()')
            textblock_args = [width_arg, position_arg]

            decorations.append({
                "command": "textblock",
                "args": textblock_args
            })

            # Find textblock boundaries for removal
            textblock_start = textblock_match.start()
            try:
                _, _, end_start_pos = extract_environment_content(latex_str, "textblock*")
                end_match = re.search(EnvironmentPatterns.END_TEXTBLOCK_STAR, latex_str[end_start_pos:])
                if end_match:
                    textblock_end = end_start_pos + end_match.end()
                    # Remove textblock environment
                    latex_str = latex_str[:textblock_start] + latex_str[textblock_end:]
            except ValueError:
                pass

        # Extract leftgrad commands before removing
        for match in re.finditer(PageRegex.LEFTGRAD, latex_str):
            command_str = match.group(0)
            args = extract_brace_arguments(command_str)
            decorations.append({"command": "leftgrad", "args": args})

        # Extract bottombar commands before removing
        for match in re.finditer(PageRegex.BOTTOMBAR, latex_str):
            command_str = match.group(0)
            args = extract_brace_arguments(command_str)
            decorations.append({"command": "bottombar", "args": args})

        # Extract topgradtri commands before removing
        for match in re.finditer(PageRegex.TOPGRADTRI, latex_str):
            command_str = match.group(0)
            args = extract_brace_arguments(command_str)
            decorations.append({"command": "topgradtri", "args": args})

        # Remove decoration commands
        latex_str = re.sub(PageRegex.LEFTGRAD, '', latex_str)
        latex_str = re.sub(PageRegex.BOTTOMBAR, '', latex_str)
        latex_str = re.sub(PageRegex.TOPGRADTRI, '', latex_str)

        return latex_str, decorations

    def extract_textblock_literal(self, latex_str: str) -> Dict[str, Any] | None:
        """
        Extract literal LaTeX content from textblock environment.

        Textblock content is stored verbatim without parsing - it's treated as a
        LaTeX literal that gets copied and pasted. Currently used for bottom bar
        "Two Truths and a Lie" section, but could be generalized for other literals.

        Note: This extracts content WITHIN textblock. The textblock wrapper itself
        is handled separately as a page decoration.

        Future: If we have other latex literals not in textblocks, extract this
        to a more general `extract_latex_literal()` triggered by different patterns.

        Args:
            latex_str: Page LaTeX content

        Returns:
            Dict with content_latex (raw LaTeX string), or None if no textblock found
        """
        # Check if textblock exists using pattern from EnvironmentPatterns
        if not re.search(EnvironmentPatterns.BEGIN_TEXTBLOCK_STAR, latex_str):
            return None

        # Extract textblock environment content using helper
        # Store as literal LaTeX - content never changes, just copy/paste it
        try:
            textblock_content, _, _ = extract_environment_content(
                latex_str, "textblock*"
            )
        except ValueError:
            return None

        # Skip textblock* arguments: {width}(coordinates)
        # These are captured separately in decorations, don't duplicate in literal content
        textblock_content = skip_latex_arguments(
            textblock_content.strip(),
            mandatory=1,
            special_paren=True
        )

        # Store the inner content as-is (no parsing, no cleaning)
        # This preserves exact formatting: \mbox, \hspace, pipes, etc.
        return {
            "content_latex": textblock_content.strip()
        }

    def extract_page_regions(self, latex_str: str, page_number: int = 1) -> Dict[str, Any]:
        """
        Extract page regions from LaTeX content (paracol structure).

        Finds \begin{paracol}{2}...\end{paracol} and splits on \switchcolumn.

        Args:
            latex_str: LaTeX source for single page
            page_number: Page number (1-indexed)

        Returns:
            Dict with top, left_column, main_column, bottom, decorations regions
        """

        # Extract literal content from inside textblock FIRST
        # Must extract before removing textblock wrapper
        textblock_literal = self.extract_textblock_literal(latex_str)

        # Extract and remove decorations (textblock + grad/bar commands)
        # These are absolutely positioned and must be removed before section parsing
        latex_str, decorations = self._extract_and_remove_decorations(latex_str)

        # Find paracol environment
        paracol_match = re.search(PageRegex.BEGIN_PARACOL, latex_str)
        if not paracol_match:
            raise ValueError(f"No \\begin{{paracol}}{{2}} found")

        paracol_start = paracol_match.end()

        # Find \end{paracol}
        end_match = re.search(PageRegex.END_PARACOL, latex_str[paracol_start:])
        if not end_match:
            raise ValueError(f"No matching \\end{{paracol}} found")

        paracol_content = latex_str[paracol_start:paracol_start + end_match.start()]

        # Find \switchcolumn (optional for continuation pages)
        switch_match = re.search(PageRegex.SWITCHCOLUMN, paracol_content)

        if switch_match:
            # Has both columns
            left_content = paracol_content[:switch_match.start()].strip()
            main_content = paracol_content[switch_match.end():].strip()

            left_sections = self._extract_sections_from_column(left_content, region_name="left_column")
            main_sections = self._extract_sections_from_column(main_content, region_name="main_column")
        else:
            # No switchcolumn - all content is in main column (continuation page)
            left_sections = []
            main_sections = self._extract_sections_from_column(paracol_content.strip(), region_name="main_column")

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
            "textblock_literal": textblock_literal,
            "decorations": decorations if decorations else None
        }

    def _extract_sections_from_column(self, column_content: str, region_name: str) -> List[Dict[str, Any]]:
        """
        Extract all sections from column content.

        Args:
            column_content: LaTeX content for a single column
            region_name: Column identifier ("left_column" or "main_column")

        Returns:
            List of section dicts
        """

        sections = []

        # Find all section boundaries (both standard \section* and old Education header)
        section_markers = []

        # Find standard \section* markers
        for match in re.finditer(SectionRegex.SECTION_WITH_NAME, column_content):
            # Extract section name with balanced brace matching (handles nested braces)
            try:
                brace_pos = match.end()  # Position after '\section*{'
                section_name, end_pos = extract_balanced_delimiters(
                    column_content, brace_pos, open_char='{', close_char='}'
                )
                section_markers.append({
                    'start': match.start(),
                    'end': end_pos,  # Position after closing }
                    'name': section_name.strip(),
                    'type': 'standard'
                })
            except ValueError:
                # Skip malformed section with unbalanced braces
                continue

        # Find old Education header (5 resumes use non-standard format)
        for match in re.finditer(SectionRegex.OLD_EDUCATION_HEADER, column_content):
            section_markers.append({
                'start': match.start(),
                'end': match.end(),
                'name': 'Education',
                'type': 'old_education'
            })

        # Sort by position
        section_markers.sort(key=lambda x: x['start'])

        if not section_markers:
            return sections

        for i, marker in enumerate(section_markers):
            section_name = marker['name']

            # Get content from after this section header to before next section
            content_start = marker['end']
            if i + 1 < len(section_markers):
                content_end = section_markers[i + 1]['start']
            else:
                content_end = len(column_content)

            section_content = column_content[content_start:content_end].strip()

            # Extract trailing \vspace{...} as section spacing metadata
            spacing_after = None
            vspace_match = re.search(SectionRegex.TRAILING_VSPACE, section_content)
            if vspace_match:
                spacing_after = vspace_match.group(1)  # e.g., "2.8\sectionsep"
                # Strip vspace from content
                section_content = section_content[:vspace_match.start()].strip()

            # Infer type and parse section
            try:
                section_dict = self._parse_section_by_inference(section_name, section_content, region_name)

                # Ensure metadata dict exists
                if 'metadata' not in section_dict:
                    section_dict['metadata'] = {}

                # Move section-level fields into metadata
                section_dict['metadata']['name'] = section_name
                section_dict['metadata']['name_plaintext'] = to_plaintext(section_name)

                if spacing_after:
                    section_dict['metadata']['spacing_after'] = spacing_after

                sections.append(section_dict)
            except Exception as e:
                # Log error but continue parsing other sections
                print(f"WARNING: Failed to parse section '{section_name}': {type(e).__name__}: {e}")
                print(f"  Content preview: {section_content[:100]}...")
                # Skip this section and continue with next one
                continue

        return sections

    def _parse_section_by_inference(self, section_name: str, content: str, region_name: str) -> Dict[str, Any]:
        """
        Infer section type from content and parse accordingly.

        Args:
            section_name: Section name (e.g., "Core Skills") - will be added to metadata by caller
            content: Section content LaTeX
            region_name: Column identifier ("left_column" or "main_column")

        Returns:
            Section dict with type, metadata (empty), and content or subsections
        """

        # Try to infer type from content structure
        if re.search(EnvironmentPatterns.BEGIN_ITEMIZE_PROJ_MAIN, content):
            # Standalone projects section (about half of historical resumes use this)
            parsed = self.parse_projects(content)
            return {
                "type": "projects",
                "metadata": {},
                "subsections": parsed["subsections"]
            }

        elif re.search(EnvironmentPatterns.BEGIN_ITEMIZE_ACADEMIC, content):
            # Work experience section
            # Parse all work experience subsections
            subsections = []
            begin_pattern = EnvironmentPatterns.BEGIN_ITEMIZE_ACADEMIC
            for match in re.finditer(begin_pattern, content):
                # Find corresponding \end{itemizeAcademic}
                start = match.start()
                end_pattern = EnvironmentPatterns.END_ITEMIZE_ACADEMIC
                end_match = re.search(end_pattern, content[start:])
                if end_match:
                    subsection_latex = content[start:start + end_match.end()]
                    subsection = self.parse_work_experience(subsection_latex)
                    subsections.append(subsection)

            return {
                "type": "work_history",
                "metadata": {},
                "subsections": subsections
            }

        elif re.search(EnvironmentPatterns.BEGIN_ITEMIZE, content) and ContentPatterns.EDUCATION_UNIVERSITY in content:
            # education (check before skill_categories - more specific pattern)
            parsed = self.parse_education(content)
            return {
                "type": "education",
                "metadata": parsed["metadata"],
                "content": parsed.get("content", {})
            }

        elif re.search(EnvironmentPatterns.BEGIN_ITEMIZE, content) and re.search(EnvironmentPatterns.ITEM_BRACKET, content) and re.search(EnvironmentPatterns.BEGIN_ITEMIZE_LL, content):
            # skill_categories - outer itemize with \item[icon]Name + nested itemizeLL
            parsed = self.parse_skill_categories(content)
            return {
                "type": "skill_categories",
                "metadata": {},
                "subsections": parsed["subsections"]
            }

        elif FormattingPatterns.SETLENGTH in content and FormattingPatterns.BASELINESKIP in content and FormattingPatterns.SCSHAPE in content:
            # skill_list_caps
            parsed = self.parse_skill_list_caps(content)
            return {
                "type": "skill_list_caps",
                "metadata": {},
                "content": parsed["content"]
            }

        elif '|' in content:
            # skill_list_pipes (pipe-delimited list, may or may not have \texttt formatting)
            parsed = self.parse_skill_list_pipes(content)
            return {
                "type": "skill_list_pipes",
                "metadata": {},
                "content": parsed["content"]
            }

        elif region_name == "left_column" and re.search(EnvironmentPatterns.BEGIN_ITEMIZE_ANY, content):
            # personality_alias_array - Left column itemize variants (itemizeMain, itemizeLL)
            # All left-column itemize sections are personality sections (verified empirically)
            parsed = self.parse_personality_alias_array(content)
            return {
                "type": "personality_alias_array",
                "metadata": parsed.get("metadata", {}),
                "content": parsed["content"]
            }

        elif re.search(EnvironmentPatterns.BEGIN_ITEMIZE, content):
            # custom_itemize - Vanilla itemize with optional params and/or custom item markers
            # Check for exact \begin{itemize} match (not itemizeLL, itemizeMain, etc.)
            # This handles sections like "HPC Highlights" that use standard itemize environment
            parsed = self._parse_as_custom_itemize(content)
            return {
                "type": "custom_itemize",
                "metadata": parsed.get("metadata", {}),
                "content": parsed["content"]
            }

        elif re.search(EnvironmentPatterns.BEGIN_ITEMIZE_ANY, content):
            # simple_list - Fallback for custom itemize variants (itemizeLL, etc.)
            # This should rarely be reached now that left_column itemize is handled above
            parsed = self._parse_as_simple_list(content)
            return {
                "type": "simple_list",
                "metadata": parsed["metadata"],
                "content": parsed["content"]
            }

        else:
            # Unknown type - store as raw
            return {
                "type": "unknown",
                "metadata": {},
                "content": {"raw": content}
            }
