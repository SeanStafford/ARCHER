"""
LLM-based metadata extraction for job descriptions.

Used as a fallback when heuristic extraction fails to find required fields.
"""

import json
import re

from archer.utils.llm import get_provider

# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

_SYSTEM_PROMPT = """\
You are a metadata extraction assistant. Extract job posting metadata from the provided text.
Return ONLY a JSON object with the requested fields. Use null for fields you cannot find.
Be precise and extract values as they appear in the text."""

_USER_PROMPT_TEMPLATE = """\
Extract the following fields from this job posting:

{fields_json}

Return a JSON object with these exact field names as keys.
Use null for any field you cannot find in the text.

---
Job Posting:
{content}"""

# =============================================================================
# FIELD INSTRUCTIONS
# =============================================================================

# Field-specific extraction instructions for viable fields only
# Based on validation: Company (100%), Role (91%), Location (80%), Salary (96%), Work Mode (91%)
_FIELD_INSTRUCTIONS = {
    "Company": (
        "The company/organization name. Use the full official name. "
        "If a parent company is mentioned (e.g., 'Acme Corp, a subsidiary of BigCo'), include both."
    ),
    "Role": (
        "The exact job title as written. Do not expand abbreviations "
        "(keep 'AI/ML Engineer' as-is, don't write 'Artificial Intelligence/Machine Learning Engineer')."
    ),
    "Location": (
        "Geographic location only (City, State). NOT work arrangement. "
        "If multiple locations (>3), return 'Multiple locations' or list the first 2-3. "
        "If only 'Remote' with no city, return 'Remote'. "
        "Do NOT include 'Hybrid', 'On-site', or schedule info here. "
        "If uncertain which location is primary, return null rather than picking one arbitrarily."
    ),
    "Salary": (
        "Salary range in format '$XXX,XXX - $XXX,XXX'. "
        "Convert K notation (e.g., '$150K' -> '$150,000'). "
        "Include only the numbers and range, not 'annually' or 'per year'."
    ),
    "Work Mode": (
        "Only one of: 'Remote', 'Hybrid', or 'On-site'. "
        "Hybrid means some days in office. Remote means fully remote. "
        "If unclear, use null."
    ),
}

# =============================================================================
# EXTRACTION FUNCTIONS
# =============================================================================


def build_extraction_prompt(fields: list[str], content: str) -> str:
    """
    Build a prompt for extracting specific metadata fields.

    Args:
        fields: List of field names to extract (e.g., ["Company", "Location"])
        content: Raw job description text

    Returns:
        User prompt string for the LLM
    """
    # Build field descriptions with instructions
    fields_dict = {}
    for field in fields:
        if field in _FIELD_INSTRUCTIONS:
            fields_dict[field] = _FIELD_INSTRUCTIONS[field]
        else:
            fields_dict[field] = field  # Fallback for any custom fields

    return _USER_PROMPT_TEMPLATE.format(
        fields_json=json.dumps(fields_dict, indent=2),
        content=content[:8000],
    )


def extract_metadata_with_llm(
    fields: list[str],
    content: str,
    model: str = "gpt-4o-mini",
    provider: str = "openai",
) -> dict[str, str | None]:
    """
    Extract metadata fields using an LLM.

    Args:
        fields: List of field names to extract
        content: Raw job description text
        model: LLM model to use (default: gpt-4o-mini for cost efficiency)
        provider: LLM provider ("openai" or "anthropic")

    Returns:
        Dict mapping field names to extracted values (None if not found)
    """
    if not fields:
        return {}

    llm = get_provider(provider_name=provider, model=model)

    user_prompt = build_extraction_prompt(fields, content)

    response = llm.generate(system_prompt=_SYSTEM_PROMPT, user_prompt=user_prompt)

    # Parse JSON response (may be wrapped in markdown code blocks)
    result = _parse_json_response(response.content)

    # Normalize results - ensure all requested fields are present
    normalized = {}
    for field in fields:
        value = result.get(field)
        # Convert empty strings and "null" strings to None
        if value is not None and str(value).lower() not in ("null", "none", "n/a", ""):
            normalized[field] = str(value).strip()
        else:
            normalized[field] = None

    return normalized


# =============================================================================
# RESPONSE PARSING
# =============================================================================


def _parse_json_response(text: str) -> dict:
    """Parse JSON from LLM response, handling markdown code blocks."""
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code blocks
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in text
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {}
