# ResumeDocument API Reference

The `ResumeDocument` class provides a high-level API for consuming structured resume data in both **markdown** and **plaintext** formats. This is the primary interface for the **Targeting context** to analyze and select content.

**Source**: `archer/contexts/templating/resume_data_structure.py`

---

## Class Overview

| Class | Purpose |
|-------|---------|
| `ResumeDocument` | Load and query a single resume from YAML or .tex |
| `ResumeSection` | Represents one section (skills, experience, etc.) |
| `ResumeDocumentCollection` | Batch-load resumes via registry (preferred) |

---

## Dual-Mode Architecture

**Why two modes?**
- **markdown**: Preserves inline formatting (`**bold**`, `*italic*`, `` `code` ``) for human-readable output
- **plaintext**: Strips all formatting for text analysis, search, embeddings, and LLM processing

**Mode selection:**
```python
from archer.contexts.templating.resume_data_structure import ResumeDocument
from pathlib import Path

# Markdown mode (default) - preserves formatting
doc = ResumeDocument(Path("resume.yaml"), mode="markdown")

# Plaintext mode - strips all formatting
doc = ResumeDocument(Path("resume.yaml"), mode="plaintext")
```

**Note**: Structural markdown (headers `##`, bullets `-`) is always present regardless of mode. Mode only controls inline content formatting within text.

---

## Loading Resumes

### From YAML (preferred)
```python
doc = ResumeDocument(Path("data/resume_archive/structured/resume.yaml"))
```

### From LaTeX
```python
doc = ResumeDocument.from_tex(Path("data/resume_archive/resume.tex"))
```
Converts LaTeX → YAML internally via temp file, then loads. Use YAML when available for performance.

### Batch Loading
```python
from archer.contexts.templating import ResumeDocumentCollection

# Load all historical resumes (default)
collection = ResumeDocumentCollection()

# Load with options
collection = ResumeDocumentCollection(
    resume_types=("historical", "experimental"),
    format_mode="plaintext",
    show_progress=True,
)

# Access by filename
doc = collection["Res202506"]

# Iterate
for doc in collection:
    print(doc.filename)

# Add more types later
collection._load(("test",), format_mode="plaintext")
```

Uses the resume registry to enumerate resumes by type, checks status eligibility
(e.g. historical must be `"parsed"`, experimental must be `"approved"`), and
resolves YAML paths via `get_resume_file()`.

---

## Document Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | Candidate name (plaintext) |
| `professional_title` | `str` | Job title/brand |
| `professional_profile` | `str` | Summary paragraph |
| `sections` | `List[ResumeSection]` | All sections in document |
| `page_count` | `int` | Number of pages |
| `left_column_ratio` | `float` | Left column width (e.g., 0.275) |
| `source_path` | `str` | Original file path |
| `filename` | `str` | Filename without extension |

---

## Getting Text Output

**Full document:**
```python
text = doc.get_all_text()  # Complete formatted text with page breaks (---)
```

**Section-specific:**
```python
for section in doc.sections:
    print(f"## {section.name}")
    print(section.text)  # Lazy-evaluated, cached
```

**Table of contents:**
```python
print(doc.table_of_contents)
# Output:
#  1. Core Skills                  | page 1 | left_column     | skill_list_caps
#  2. AI & Machine Learning        | page 1 | left_column     | skill_categories
#  3. Experience                   | page 1 | main            | work_history
```

---

## ResumeSection

Each section contains:

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Section name (plaintext) |
| `section_type` | `str` | Type identifier (see below) |
| `data` | `dict` | Structured content (varies by type) |
| `page_number` | `int` | Page where section appears (1-indexed) |
| `region` | `str` | Layout region (`left_column`, `main`, etc.) |
| `text` | `str` | Markdown representation (lazy, cached) |

### Supported Section Types

| Type | Description | Data Structure |
|------|-------------|----------------|
| `work_history` | Employment history | `{subsections: [{company, title, items, projects}]}` |
| `work_experience` | Single job entry | `{company, title, dates, items, projects}` |
| `education` | Degrees/institutions | `{items: [str]}` |
| `skill_list_caps` | ALL CAPS skill list | `{items: [str]}` |
| `skill_list_pipes` | Pipe-separated skills | `{items: [str]}` |
| `skill_categories` | Grouped skills | `{subsections: [{name, items}]}` |
| `projects` | Project list | `{subsections: [{name, items}]}` |
| `personality_alias_array` | Traits/interests | `{items: [str]}` |
| `personality_bottom_bar` | Bottom bar traits | `{items: [str]}` |

### Extracting Items

```python
section = doc.get_section("Core Skills")
items = section.get_items()  # ['Python', 'PyTorch', 'Docker', ...]
```

Works for skills, bullets, and project items. Returns empty list for education/personality.

**Batch extraction:**
```python
results = doc.get_items_by_section(["Core Skills", "AI & Machine Learning"])
# {'Core Skills': ['Python', ...], 'AI & Machine Learning': ['TensorFlow', ...]}
```

---

## LaTeX to Markdown Conversion

The `latex_to_markdown()` function (from `archer/utils/markdown.py`) handles conversion:

### Formatting Commands
| LaTeX | Markdown |
|-------|----------|
| `\textbf{text}` | `**text**` |
| `\textit{text}` | `*text*` |
| `\texttt{text}` | `` `text` `` |
| `\coloremph{text}` | `**text**` |

### Special Symbols
| LaTeX | Result |
|-------|--------|
| `\texttimes` | `×` |
| `$\to$` | `→` |
| `\&` | `&` |

### Structural Commands (stripped)
| LaTeX | Result |
|-------|--------|
| `\\` | ` ` (space) |
| `\nolinebreak`, `\nopagebreak` | removed |
| `\centering`, `\par`, `\hfill` | removed |
| `\href{url}{text}` | `text` (keeps link text only) |
| `\color{...}` | removed |

### Nested Braces
Uses `extract_balanced_delimiters()` to handle nested structures like `\textbf{Foo \texttt{Bar}}` → `**Foo `Bar`**`

---

## Plaintext Conversion

The `to_plaintext()` function (from `archer/utils/latex_parsing_tools.py`) provides aggressive stripping:

### Removed
- All formatting commands (`\textbf`, `\textit`, `\color`, etc.)
- Standalone commands (`\centering`, `\par`, `\vspace`)
- Literal braces used for grouping
- Extra whitespace

### Converted
| LaTeX | Plaintext |
|-------|-----------|
| `$\to$` | ` to ` |
| `\rightarrow` | `->` |
| `\leq`, `\geq` | `<=`, `>=` |
| `\{`, `\}` | `{`, `}` |
| `\%`, `\$`, `\&` | `%`, `$`, `&` |
| `\;`, `\,`, `\:` | space |

---

## Mode-Specific Examples

**Work Experience Bullet (from YAML):**
```yaml
bullets:
  - marker: itemi
    latex_raw: "\textbf{Reduced} compute time from 1 month $\to$ 12 hours"
    plaintext: "Reduced compute time from 1 month to 12 hours"
```

| Mode | Output |
|------|--------|
| markdown | `**Reduced** compute time from 1 month → 12 hours` |
| plaintext | `Reduced compute time from 1 month to 12 hours` |

**Skill List Item:**
```yaml
items:
  - marker: itemLL
    latex_raw: "\texttt{Python}"
    plaintext: "Python"
```

| Mode | Output |
|------|--------|
| markdown | `` `Python` `` |
| plaintext | `Python` |

---

## Implementation Notes

### Key Internal Methods

**`_get_plaintext_items_from_yaml_list(content)`**
- Extracts items from standardized lists
- Checks both `content["items"]` (skill lists) and `content["bullets"]` (personality, skill_category)
- Markdown mode: Converts `latex_raw` via `latex_to_markdown()`
- Plaintext mode: Uses `plaintext` field directly

**`_parse_work_experience(section_data)`**
- Converts all metadata fields (company, title, dates, location) based on mode
- Processes bullets and nested projects
- Ensures LaTeX in metadata (like `\&`) is properly converted

**`_parse_education(section_data)`**
- Education content is hardcoded in Jinja template (never changes)
- Renders template to get actual content, then parses the LaTeX
- Returns only items list

**`_get_section_data(section_data, section_name)`**
- Auto-detects section type and dispatches to type-specific parsers
- For `skill_category`, extracts name from `metadata["name"]`
- Unknown types attempt list formatting, then fall back to empty

### Caching

`ResumeSection.text` is lazy-evaluated and cached via `_text_cache`. First access triggers `_format_to_text()`, subsequent accesses return cached value.

### Error Handling

- `FileNotFoundError`: YAML/tex file doesn't exist
- `ValueError`: Invalid YAML structure (missing `document` key) or invalid mode
- `AttributeError`: Section not found in `get_section()`
- Batch loading emits `UserWarning` for failed files, continues with successful ones
