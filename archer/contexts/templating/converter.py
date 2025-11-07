"""
LaTeX <-> YAML Converter

Main module providing convenience functions for bidirectional conversion
between structured YAML and LaTeX resume format.

This module exports:
- Convenience functions: yaml_to_latex, latex_to_yaml
- Converter classes: YAMLToLaTeXConverter, LaTeXToYAMLConverter (re-exported)
"""

import re
from pathlib import Path
from typing import Any, Dict

from omegaconf import OmegaConf

from archer.contexts.templating.latex_patterns import DocumentRegex, EnvironmentPatterns
from archer.contexts.templating.latex_generator import YAMLToLaTeXConverter
from archer.contexts.templating.latex_parser import LaTeXToYAMLConverter


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
    if "document" in yaml_dict:
        # Full document
        latex = converter.generate_document(yaml_dict)
    elif "subsection" in yaml_dict:
        # Single subsection (for testing)
        latex = converter.convert_work_experience(yaml_dict["subsection"])
    else:
        raise ValueError("YAML must contain either 'document' or 'subsection' key")

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

    # Try to parse as full document first
    if re.search(DocumentRegex.BEGIN_DOCUMENT, latex_str) and re.search(DocumentRegex.END_DOCUMENT, latex_str):
        # Full document
        yaml_dict = converter.parse_document(latex_str)
    elif re.search(EnvironmentPatterns.BEGIN_ITEMIZE_ACADEMIC, latex_str):
        # Single work experience subsection (for testing)
        result = converter.parse_work_experience(latex_str)
        yaml_dict = {"subsection": result}
    else:
        raise ValueError("LaTeX must be either a full document or a single itemizeAcademic subsection")

    if output_path:
        conf = OmegaConf.create(yaml_dict)
        OmegaConf.save(conf, output_path)

        # Strip trailing blank lines for consistency
        content = output_path.read_text()
        output_path.write_text(content.rstrip() + '\n')

    return yaml_dict
