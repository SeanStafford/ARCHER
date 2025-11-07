## ResumeDocument API

The `ResumeDocument` class provides a high-level API for consuming structured resume data in both **markdown** and **plaintext** 
formats. This is the primary interface for the **Targeting context** to analyze and select content.

### Dual-Mode Architecture

**Why two modes?**
- **markdown**: Preserves inline formatting (bold, italic, monospace) for human-readable output
- **plaintext**: Strips all formatting for text analysis, search, and LLM processing

**Mode selection:**
```python
from archer.contexts.templating.resume_data_structure import ResumeDocument
from pathlib import Path

# Markdown mode (default) - preserves ** bold **, * italic *, ` code `
doc = ResumeDocument(Path("resume.yaml"), mode="markdown")

# Plaintext mode - strips all formatting
doc = ResumeDocument(Path("resume.yaml"), mode="plaintext")
```

### Getting Text Output

**Full document text:**
```python
text = doc.get_all_text()  # Returns complete formatted text
```

**Section-specific text:**
```python
for section in doc.sections:
    section_text = section.format_to_text()  # Respects document mode
    print(f"## {section.name}\n{section_text}\n")
```

### Mode-Specific Formatting Examples

**Work Experience Bullet:**
```yaml
bullets:
  - marker: itemi
    latex_raw: "\textbf{Reduced} compute time from 1 month $\to$ 12 hours"
    plaintext: "Reduced compute time from 1 month to 12 hours"
```

**Markdown output:** `**Reduced** compute time from 1 month → 12 hours`
**Plaintext output:** `Reduced compute time from 1 month to 12 hours`

**Skill List Item:**
```yaml
items:
  - marker: itemLL
    latex_raw: "\texttt{Python}"
    plaintext: "Python"
```

**Markdown output:** `` `Python` ``
**Plaintext output:** `Python`

### LaTeX to Markdown Conversion

The `latex_to_markdown()` function handles common LaTeX commands:

**Formatting commands:**
- `\textbf{text}` → `**text**`
- `\textit{text}` → `*text*`
- `\texttt{text}` → `` `text` ``
- `\coloremph{text}` → `**text**`

**Special symbols:**
- `\texttimes` → `×`
- `$\toHere is some additional documentation in case it is useful:

```
 → `→`
- `\&` → `&`

**Structural commands (stripped):**
- `\\` → ` ` (line breaks → spaces)
- `\nolinebreak`, `\nopagebreak` → removed
- `\centering`, `\par`, `\hfill` → removed
- `\href{url}{text}` → `text` (keeps link text only)

**Nested braces:** Uses `extract_balanced_delimiters()` to handle nested structures like `\textbf{Foo \texttt{Bar}}`

### Implementation Details

**Key methods in ResumeDocument:**

`_get_plaintext_items_from_yaml_list(content)` - Extracts items from standardized lists
- Checks both `content["items"]` (skill lists) and `content["bullets"]` (personality, skill_category)
- Markdown mode: Converts `latex_raw` → markdown
- Plaintext mode: Uses `plaintext` field directly

`_parse_work_experience(section_data)` - Extracts work experience data
- Converts all metadata fields (company, title, dates, location) based on mode
- Processes bullets and nested projects
- Ensures LaTeX in metadata (like `\&`) is properly converted

`_parse_education(section_data)` - Parses education sections
- Converts institution, degree, field, dates based on mode
- Handles multi-institution structures

`_get_section_data(section_data, section_name)` - Generic section parser
- Auto-detects section type
- For `skill_category`, extracts name from `metadata["name"]`
- Dispatches to type-specific parsers

**Unknown type fallback:**
- If section type is unrecognized, tries to format as a list
- Falls back to `"## {name}\n\n(No content)"` for empty/unknown sections
