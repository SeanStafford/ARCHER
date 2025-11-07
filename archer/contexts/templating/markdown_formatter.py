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

    # Add top-level bullets
    for bullet in data.get('bullets', []):
        bullet_text = latex_to_markdown(bullet)
        parts.append(f"- {bullet_text}")

    # Add projects as #### headers
    for project in data.get('projects', []):
        if project.get('name'):
            proj_name = latex_to_markdown(project['name'])
            parts.append(f"\n#### {proj_name}\n")
        for bullet in project.get('bullets', []):
            bullet_text = latex_to_markdown(bullet)
            parts.append(f"- {bullet_text}")

    return "\n".join(parts)


def format_skills_markdown(data: Dict[str, Any], section_name: str) -> str:
    """
    Format skills data as markdown.

    Handles both flat skill lists and categorized skills.

    Args:
        data: Skills data dict
        section_name: Name to use as header

    Returns:
        Markdown-formatted skills
    """
    parts = [f"## {section_name}\n"]

    # Handle flat skills list
    if "skills" in data:
        for skill in data['skills']:
            skill_text = latex_to_markdown(skill)
            parts.append(f"- {skill_text}")

    # Handle categorized skills
    elif "categories" in data:
        for category in data['categories']:
            if category.get('name'):
                parts.append(f"\n### {category['name']}\n")
            for skill in category.get('skills', []):
                skill_text = latex_to_markdown(skill)
                parts.append(f"- {skill_text}")

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

