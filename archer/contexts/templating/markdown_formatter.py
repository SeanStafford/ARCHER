"""
Markdown Utilities

Helper functions for formatting structured resume data as markdown.
"""

from archer.utils.markdown import latex_to_markdown
from typing import Any, Dict


def format_work_experience_markdown(data: Dict[str, Any]) -> str:
    """
    Format single work experience entry as markdown.

    Company is formatted as ### (section header added separately by caller).
    Projects are formatted as ####.

    Args:
        data: Work experience data dict

    Returns:
        Markdown-formatted work experience (without section header)
    """
    parts = []

    # Company/institution as ### header
    company = data.get('company', 'Unknown Company')
    parts.append(f"### {company}\n")

    # Add metadata (title, dates, location)
    if data.get('title'):
        parts.append(f"**{data['title']}**")
    if data.get('dates'):
        parts.append(f"*{data['dates']}*")
    if data.get('location'):
        parts.append(f"{data['location']}")

    parts.append("")  # Blank line before content

    # Add top-level items
    for item in data.get('items', []):
        parts.append(f"- {item}")

    # Add projects as #### headers
    for project in data.get('projects', []):
        if project.get('name'):
            parts.append(f"\n#### {project['name']}\n")
        for item in project.get('items', []):
            parts.append(f"- {item}")

    return "\n".join(parts)


def format_subsections_markdown(data: Dict[str, Any], section_name: str) -> str:
    """
    Format wrapper sections with subsections (skill_categories, projects).

    Each subsection has a name and items. Formats as:
    ## Section Name
    ### Subsection 1
    - item
    - item
    ### Subsection 2
    - item

    Args:
        data: Section data dict with "subsections" key
        section_name: Name to use as header

    Returns:
        Markdown-formatted section with subsections
    """
    parts = [f"## {section_name}\n"]

    for subsection in data["subsections"]:
        subsection_name = subsection["name"]
        parts.append(f"\n### {subsection_name}\n")

        for item in subsection["items"]:
            parts.append(f"- {item}")

    return "\n".join(parts)


def format_education_markdown(data: Dict[str, Any], institution_name: str) -> str:
    """
    Format education data as markdown.

    Args:
        data: Education data dict
        institution_name: Name to use as header

    Returns:
        Markdown-formatted education
    """
    parts = [f"## {institution_name}\n"]

    if data.get('degree'):
        parts.append(f"**{data['degree']}**")
    if data.get('field'):
        parts.append(f"{data['field']}")
    if data.get('dates'):
        parts.append(f"*{data['dates']}*")

    parts.append("")  # Blank line before items

    for item in data.get('items', []):
        item_text = latex_to_markdown(item)
        parts.append(f"- {item_text}")

    return "\n".join(parts)

