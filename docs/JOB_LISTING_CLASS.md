# JobListing API Reference

The `JobListing` class provides the intake context's primary API for representing parsed job descriptions. It is the main interface for the targeting context to analyze job requirements and match against resume content.

**Source**: `archer/contexts/intake/job_data_structure.py`

---

## Class Overview

| Class | Purpose |
|-------|---------|
| `JobListing` | Load and query a single job description from markdown |

---

## Loading Job Listings

### From a markdown file

```python
from archer.contexts.intake import JobListing

job = JobListing.from_file("data/jobs/MLEng_AcmeCorp_10130042.md")
```

The job identifier is derived from the filename stem. The title is derived from metadata or the first line of the file. To extract metadata from the `## Metadata` header section, use `use_markdown_tree=True`:

```python
job = JobListing.from_file("data/jobs/MLEng_AcmeCorp_10130042.md", use_markdown_tree=True)
```

### From raw text

```python
job = JobListing.from_text(markdown_text, job_identifier="MLEng_AcmeCorp_10130042")
```

### By identifier (auto-resolve)

```python
job = JobListing.from_identifier("MLEng_AcmeCorp_10130042")
```

Searches for markdown files in `JOBS_PATH` (see `.env.example`). Raises `ValueError` if not found.

### Identifier structure

The job identifier is the filename stem (without `.md`). It is underscore-delimited, with the job/requisition ID as the last component and a descriptive prefix identifying the role and company:

```
MLEng_AcmeCorp_10130042         → prefix: MLEng_AcmeCorp, ID: 10130042
TPSReportCollator_Sen_Initech_R0229614   → prefix: TPSReportCollator_Sen_Initech, ID: R0229614
```

---

## Parsers

`JobListing` uses two parsers, selected by the `use_markdown_tree` flag available on all factory methods:

| Parser | Flag | Metadata | Markdown structure |
|--------|------|----------|----------|
| `parse_job_text` | `False` (default) | Not extracted | Flat |
| `parse_job_structured_markdown` | `True` | Extracted from `## Metadata` section | Hierarchical |

Both parsers extract sections, classify qualification sections, and detect boilerplate. The structured parser additionally reads the `## Metadata` header block to populate the `metadata` dict and understand `##` -> `###` markdown section hierarchy.

---

## JobListing attributes

| Property | Type | Description |
|----------|------|-------------|
| `raw_text` | `str` | Original markdown text |
| `sections` | `dict[str, str]` | Parsed sections (name → content) |
| `required_qualifications_sections` | `list[str]` | Section names classified as required qualifications |
| `preferred_qualifications_sections` | `list[str]` | Section names classified as preferred qualifications |
| `metadata` | `dict[str, str]` | Structured metadata (see Metadata Fields below) |
| `job_identifier` | `str` | Identifier derived from filename or constructed from components |
| `title` | `str` | Job title (from metadata or first line of text) |
| `source_url` | `str` | URL where job was posted (if available) |

---

## JobListing methods

### `get_text(exclude_boilerplate=True) -> str`

Get the full job description text. By default, boilerplate sections are excluded.

```python
text = job.get_text()                    # Without boilerplate
full_text = job.get_text(exclude_boilerplate=False)  # Everything
```

### `get_sections() -> dict[str, str]`

Get all parsed sections as a dict copy.

### `get_required_qualifications() -> list[str]`

Parse bullet items from all required qualification sections.

```python
reqs = job.get_required_qualifications()
# ["5+ years of experience in machine learning", "Strong Python skills", ...]
```

### `get_preferred_qualifications() -> list[str]`

Parse bullet items from all preferred qualification sections.

---

## Metadata Fields

When loaded with `use_markdown_tree=True`, the `metadata` dict is populated from the `## Metadata` section of the markdown file.

**Required fields:**

| Field | Description |
|-------|-------------|
| `Company` | Company or organization name |
| `Role` | Full job title as posted |
| `Location` | City, State or "Remote" |

**Optional fields:**

| Field | Description |
|-------|-------------|
| `Job ID` | Requisition number or posting ID |
| `Salary` | Compensation range as posted |
| `Source` | ATS platform or job board name |
| `URL` | Direct link to job posting |
| `Focus` | Specialization area (e.g., "Pre-training", "Platform") |
| `Clearance` | Security clearance requirement |
| `Work Mode` | Remote / Hybrid / On-site |
| `Date Posted` | Posting date |

---

## Job Description File Format

Job description markdown files use a two-part structure: a `## Metadata` section containing structured fields, followed by body sections with the job description content.

### Metadata Section

All metadata lives inside a `## Metadata` section. Fields are `###` headers within it, with the field value on the line immediately after the heading.

```markdown
## Metadata

### Company
Acme Corp

### Role
Machine Learning Engineer

### Job ID
10130042

### Location
San Francisco, CA
```

### Body Sections

Body sections use `##` headings (same level as Metadata) and contain the job description content:

```markdown
## About the Role
<body content>

## Responsibilities
<body content>

## Required Qualifications
<body content>
```

### Formatting Conventions

1. **Title Case field names** — `### Job ID`, not `### job id`
2. **Omit optional fields** if not applicable — don't write "Not listed" or "N/A"
3. **All `###` fields must be inside `## Metadata`** — `###` headers outside Metadata are treated as body subsections
4. **Body sections use `##`** — same heading level as Metadata
5. **Field value on the line immediately after the heading** — no blank line between `###` and value
6. **No preamble** — all content must be inside a `##` section; text before the first heading is discarded with a warning

---

## Section Classification

The parser automatically classifies sections into archetypes:

- **Required qualifications**: Sections matching patterns like "Required Qualifications", "Minimum Requirements", "Must Have"
- **Preferred qualifications**: Sections matching patterns like "Preferred Qualifications", "Nice to Have", "Desired Skills"
- **Boilerplate**: EEO statements, benefits descriptions, legal disclaimers — excluded from `get_text()` by default

Section names are accessible via `required_qualifications_sections` and `preferred_qualifications_sections` properties. The `_section_archetypes` dict maps every section name to its archetype for inspection.

---

## Full Example

```python
from archer.contexts.intake import JobListing

# Load with metadata extraction
job = JobListing.from_file("data/jobs/MLEng_AcmeCorp_10130042.md", use_markdown_tree=True)

# Basic info
print(job.title)                     # "Machine Learning Engineer"
print(job.job_identifier)            # "MLEng_AcmeCorp_10130042"
print(job.metadata.get("Company"))   # "Acme Corp"

# Content access
text = job.get_text()                # Full text without boilerplate
reqs = job.get_required_qualifications()   # Parsed requirement bullets
prefs = job.get_preferred_qualifications() # Parsed preference bullets
```
