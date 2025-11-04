# Templating Context

The Templating context owns the structured representation of resume documents and handles **bidirectional conversion** between LaTeX (.tex) files and structured YAML format.

**Status:** ✅ **Complete** - 11 content types with operation-based parsing and template-based generation

## Quick Overview

```python
from archer.contexts.templating.converter import yaml_to_latex, latex_to_yaml

# LaTeX → YAML
yaml_data = latex_to_yaml("resume.tex")  # Returns dict

# YAML → LaTeX
latex_output = yaml_to_latex(yaml_data)  # Returns string
```

For direct access to converter classes (e.g., in tests):
```python
from archer.contexts.templating.latex_generator import YAMLToLaTeXConverter
from archer.contexts.templating.latex_parser import LaTeXToYAMLConverter
```

## Template Hierarchy

ARCHER uses a **single hierarchical template system** organized by rendering flow:

```
template/
├── structure/                     # Document structure
│   ├── document.tex.jinja        # Root orchestrator
│   └── preamble.tex.jinja        # Document metadata
├── wrappers/                      # Content wrappers
│   ├── section_wrapper.tex.jinja
│   └── work_history_wrapper.tex.jinja
└── types/                         # Content types (11 types)
    ├── work_experience/
    │   ├── type.yaml              # Schema definition (documentation only)
    │   ├── template.tex.jinja     # LaTeX generation template
    │   └── parse_config.yaml      # Parsing operations
    ├── project/
    ├── projects/                  # Container type (no template - manual wrapper)
    ├── skill_list_caps/
    ├── skill_list_pipes/
    ├── skill_categories/
    ├── skill_category/
    ├── education/
    ├── personality_alias_array/
    ├── personality_bottom_bar/
    ├── custom_itemize/
    └── simple_list/
```

**Rendering flow:** `document` includes `preamble`, then wraps each section with `section_wrapper` (or `work_history_wrapper`), which contains rendered `type` templates.

**Custom Jinja2 Delimiters** (to avoid LaTeX brace conflicts):
- Variables: `<<< var >>>`
- Blocks: `<%% for/if/etc %%>`
- Comments: `<# comment #>`

**Benefits:**
- **Visibility**: LaTeX patterns explicit in template files (not buried in Python)
- **Maintainability**: Single source of truth per type
- **Better errors**: Parser failures reference template path + line number
- **Code reduction**: String concatenation → `template.render()`

## Operation-Based Parsing

The parsing system uses a **unified `parse_with_config()` method** that reads declarative operations from `parse_config.yaml` files. Instead of type-specific parsing methods with hardcoded regex, each type defines parsing rules as a sequence of operations.

### Available Operations

**`set_literal`** - Set a literal value
```yaml
type_field:
  operation: set_literal
  output_path: type
  value: work_experience
```

**`extract_environment`** - Extract LaTeX environment with parameters
```yaml
environment:
  operation: extract_environment
  env_name: itemizeAcademic
  num_params: 4
  param_names:
    - metadata.company
    - metadata.title
    - metadata.location
    - metadata.dates
  output_context: environment_content  # Store content for later ops
```

**`split`** - Split strings on delimiters (regex or literal)
```yaml
split_title:
  operation: split
  source_path: metadata.title
  delimiter: '\\\\'  # Split on \\
  output_paths:
    - metadata.title
    - metadata.subtitle
```

**`recursive_parse`** - Parse nested structures using another config
```yaml
projects:
  operation: recursive_parse
  source: environment_content
  recursive_pattern: ITEMIZE_PROJECT_ENV
  config_name: project
  output_path: content.projects
```

**`parse_itemize_content`** - Parse bullet lists with markers
```yaml
bullets:
  operation: parse_itemize_content
  marker_pattern: ITEM_ANY
  source: environment_content
  output_path: content.bullets
```

**`extract_braced_after_pattern`** - Extract balanced braces after pattern
```yaml
extract_braced:
  operation: extract_braced_after_pattern
  pattern: '(\{)\s*\\setlength'  # Capture opening brace
  output_context: braced_content
```

**`extract_regex`** - Extract using named capture groups
```yaml
header:
  operation: extract_regex
  regex: '\\item\[(?P<icon>[^\]]*)\].*?\\scshape\s+(?P<name>[^}]+)\}'
  extract:
    icon: metadata.icon
    name: metadata.name
```

### Example: work_experience Parse Config

```yaml
patterns:
  type_field:
    operation: set_literal
    output_path: type
    value: work_experience

  environment:
    operation: extract_environment
    env_name: itemizeAcademic
    num_params: 4
    param_names: [metadata.company, metadata.title, metadata.location, metadata.dates]
    output_context: environment_content

  split_title:
    operation: split
    source_path: metadata.title
    delimiter: '\\\\'
    output_paths: [metadata.title, metadata.subtitle]

  projects:
    operation: recursive_parse
    recursive_pattern: ITEMIZE_PROJECT_ENV
    config_name: project
    source: environment_content
    output_path: content.projects

  bullets:
    operation: parse_itemize_content
    marker_pattern: ITEM_ANY
    source: environment_content
    output_path: content.bullets
```

Operations execute in order. The `environment` operation stores content in `environment_content` context, which later operations (`projects`, `bullets`) read from. The `projects` operation removes nested projects from the content before `bullets` extracts remaining items.

### Example: Template File

Templates use custom Jinja2 delimiters and receive pre-rendered nested content:

```jinja
\begin{<<< latex_environment >>>}{<<< metadata.company >>>}{<<< title >>>}{<<< metadata.location >>>}{<<< metadata.dates >>>}

<%% for bullet in bullets %%>
    \<<< bullet.marker >>> <<< bullet.latex_raw >>>

<%% endfor %%>
<%% for project in rendered_projects %%>
<<< project >>>
<%% endfor %%>
\end{<<< latex_environment >>>}
```

Generator pre-renders projects, then passes them to the template:
```python
rendered_projects = [self.convert_project(p) for p in subsection["content"]["projects"]]
template.render(metadata=metadata, bullets=bullets, rendered_projects=rendered_projects)
```

## Content Types

### Experience Types

**work_experience** - Job position with company, title, location, dates, bullets, and optional nested projects
- LaTeX: `\begin{itemizeAcademic}{company}{title}{location}{dates}`
- Supports: Multi-level bullets (`\itemi`, `\itemii`), nested projects, spacing control

**project** - Nested project within work experience with title, dates, and bullets
- LaTeX: `\begin{itemizeAProject}{bullet}{title}{dates}` or `\begin{itemizeKeyProject}{bullet}{title}{dates}`

### Skill Types

**skill_list_caps** - All-caps unbulleted skill list with small-caps formatting
- LaTeX: `{Skill One} {Skill Two} {Skill Three}`
- Usage: Core competencies sections

**skill_list_pipes** - Pipe-separated inline list with monospace formatting
- LaTeX: `\texttt{Python} | \texttt{Bash} | \texttt{C++}`
- Usage: Language/tool lists

**skill_categories** - Container for multiple skill categories with hierarchical structure
- LaTeX: Outer `\begin{itemize}` containing multiple skill_category items

**skill_category** - Individual skill category with icon, name, and items
- LaTeX: `\item[icon] {\scshape Category Name}` + `\begin{itemizeLL}` for items

### Education & Personality Types

**education** - Academic credentials with multi-institution support
- LaTeX: Nested `\begin{itemize}` with `\item[]` for institutions and `\item[\faUserGraduate]` for degrees
- Features: Optional dissertation/minor, inline metadata

**personality_alias_array** - Icon-labeled personality items
- LaTeX: `\begin{itemizeMain}` with `\item[icon]` for each trait
- Example: "Bash Black Belt", "GPU Guru"

**personality_bottom_bar** - Bottom page decoration with textblock positioning
- LaTeX: `\begin{textblock*}{width}(x, y)` with custom content
- Example: "Two Truths and a Lie"

## Data Structures

### Document Hierarchy

```
ResumeDocument
├── metadata (DocumentMetadata)
│   ├── name, date, job_title, professional_profile
│   ├── brand_primary_color, topbar_color, etc.
│   └── left_column_width, spacing parameters
└── pages (List[Page])
    ├── page_number
    ├── has_clearpage_after (bool)  # Page metadata
    └── regions (PageRegions)
        ├── top (show_professional_profile)
        ├── left_column (List[Section])
        ├── main_column (List[Section])
        ├── textblock_literal (optional LaTeX passthrough)
        └── decorations (optional list of decorations)
```

### Section Structure

```
Section
├── name (str)                    # Display name
├── type (str)                    # Type identifier (e.g., 'work_experience')
├── metadata (Dict)               # Type-specific metadata
├── content (Dict)                # Type-specific content
├── subsections (List[Section])   # Nested content (e.g., projects)
└── spacing_after (str)           # LaTeX spacing command
```

## Converter Architecture

### Layered Design

**Decorations** (positioning, visual elements)
- Handled by: `textblock_literal`, `decorations` fields in PageRegions
- Examples: Page gradients, bottom bars, textblock positioning
- **Preserved verbatim** - not parsed into structured fields

**Content** (semantic information)
- Handled by: Type-specific parsers and generators
- Examples: Work experience bullets, skill lists, education
- **Fully structured** - parsed into typed sections with metadata + content

### Module Structure

**`converter.py`** - Public API and utility functions
- `yaml_to_latex()` - File-based YAML → LaTeX conversion
- `latex_to_yaml()` - File-based LaTeX → YAML conversion

**`latex_generator.py`** - Template-based LaTeX generation
- `YAMLToLaTeXConverter` class
- Type-specific conversion methods (all use `template.render()`)
- Document assembly with preamble, pages, decorations

**`latex_parser.py`** - Config-driven LaTeX parsing
- `LaTeXToYAMLConverter` class
- Unified `parse_with_config()` method (operation-based engine)
- Helper functions: `set_nested_field()`, `get_nested_field()`

**`registries.py`** - Template and config loading
- `TemplateRegistry` - Loads/caches `template.tex.jinja` files
- `ParseConfigRegistry` - Loads/caches `parse_config.yaml` files

### Processing Hierarchy

**Level 0: Registries**
- `TemplateRegistry` - Loads `template.tex.jinja` files, caches compiled templates
- `ParseConfigRegistry` - Loads `parse_config.yaml` operation definitions

**Level 1: Type-Specific Converters**
- Parsing: Unified `parse_with_config()` reads operations from `parse_config.yaml`
- Generation: Type-specific methods (all use `template.render()`)
- Patterns in YAML configs, not hardcoded in Python

**Level 2: Section Assembly**
- `_parse_section_by_inference()` - Auto-detects section type from LaTeX
- `_generate_section()` - Dispatches to type-specific generator

**Level 3: Page Regions**
- `extract_page_regions()` - Parses paracol structure, splits on `\switchcolumn`
- `generate_document()` - Assembles pages with columns, decorations, clearpage metadata

**Level 4: Multi-Page Document**
- `extract_document_metadata()` - Parses preamble (`\renewcommand` fields, colors)
- `extract_pages()` - Splits on `\clearpage`, captures page metadata
- `parse_document()` / `generate_document()` - Complete document conversion

**Level 5: High-Level API**
- `latex_to_yaml()` / `yaml_to_latex()` - File-based conversion

### Core Components

**YAMLToLaTeXConverter** (in `latex_generator.py`) - Generates LaTeX from structured YAML
- Template-based generation for all types
- Pattern: `template = registry.get_template(type_name); return template.render(section)`
- Document assembly: preamble + pages + clearpage markers

**LaTeXToYAMLConverter** (in `latex_parser.py`) - Parses LaTeX to structured YAML
- Operation-based parsing via unified `parse_with_config()` method
- Reads operations from `parse_config.yaml` files
- Enhanced error messages with template path references
- Automatic section type inference

**TemplateRegistry** (in `registries.py`) - Jinja2 template loading and caching
- Custom environment with LaTeX-safe delimiters (`<<< >>>`, `<%% %%>`)
- Methods: `get_template()`, `get_template_source()`, `get_expected_pattern_preview()`

**ParseConfigRegistry** (in `registries.py`) - Parsing config loading and caching
- Loads `parse_config.yaml` files with operation definitions
- Methods: `get_config()`, `get_config_path()`, `is_cached()`

## Enhanced Error Handling

Parser errors reference template files for expected patterns:

```
Failed to parse skill_category: No \item[icon] {\scshape name} pattern found
Expected pattern from: archer/contexts/templating/template/types/skill_category/template.tex.jinja
Type: skill_category
Actual LaTeX:
\item[]{\hspace{-20pt}\scshape Category Name}
```

Custom exception: `TemplateParsingError` includes template path, type name, and actual LaTeX snippet.

## Dual Storage Pattern

### Metadata Fields (2 versions)

Metadata fields that can contain optional LaTeX formatting use **dual storage**:

```python
# Parser extracts both versions
metadata = {
    "professional_profile": r"\centering \textbf{I optimize LLM architectures}\par",  # Raw LaTeX
    "professional_profile_plaintext": "I optimize LLM architectures",  # Pure text
    "name": r"\textbf{Sean Stafford}",  # May have formatting
    "name_plaintext": "Sean Stafford"   # Stripped version
}
```

**Why both versions?**
- **Raw** → Templating context uses for generation (preserves original formatting for perfect roundtrip)
- **Plaintext** → Future Targeting context uses for decision-making (no LaTeX parsing required)

**Applied to:** `name`, `brand`, `professional_profile` (and their `_plaintext` counterparts)

### Content Items (3 fields)

Bullets and list items use a **3-field structure** to preserve both structure and content:

```python
# Work experience bullets
bullets = [
    {
        "marker": "itemi",  # LaTeX bullet command
        "latex_raw": r"\textbf{Reduced compute time from 1 month $\to$ 12 hours}",  # With formatting
        "plaintext": "Reduced compute time from 1 month to 12 hours"  # Stripped for analysis
    },
    {
        "marker": "itemii",
        "latex_raw": r"Scaled from 1 $\to$ 64 GPUs using \texttt{PyTorch Lightning}",
        "plaintext": "Scaled from 1 to 64 GPUs using PyTorch Lightning"
    }
]

# Skill category items
items = [
    {
        "marker": "item[--]",  # Or "itemLL" depending on environment
        "latex_raw": r"{PyTorch}",  # Preserves braces, formatting
        "plaintext": "PyTorch"  # Clean text
    }
]
```

**Why 3 fields?**
- **marker** → Preserves structural variants (`itemi` vs `itemii`, `item[--]` vs `itemLL`)
- **latex_raw** → Preserves original formatting for perfect roundtrip
- **plaintext** → Enables text analysis without LaTeX parsing

**Template usage:**
```jinja
<%% for bullet in bullets %%>
    \<<< bullet.marker >>> <<< bullet.latex_raw >>>
<%% endfor %%>
```

**Applied to:** Work experience bullets, project bullets, skill category items, custom itemize items

## Development Methodology

### Data-Driven Pattern Discovery

The parsing system was built by analyzing **actual data patterns** from 50+ historical resumes:

```bash
# Find all pipe-separated list variations
grep -ho ".*|.*|.*" data/resume_archive/*.tex | grep -v itemize | sort | uniq -c

# Results revealed:
# - 25 resumes: GPUs | CPUs | ASICs (plain text)
# - 12 resumes: \texttt{Python} | \texttt{Bash} (formatted)
# - 30+ resumes: {Python} | {Bash} (leftover braces)
```

**Key insight:** Structural pattern is **pipe delimiter**, not item formatting. Parser splits on ` | `, extracts items as-is.

### Testing with Real Data

**Golden rule:** Test on original archive files, not manually adjusted versions.

Synthetic fixtures hide real-world variation. Historical resumes contain:
- Icon-less skill categories with `\hspace{-20pt}` positioning
- Nested braces in section titles
- Multiple consecutive `\vspace` commands
- Tab indentation vs spaces
- Trailing comments on LaTeX commands

**Validation approach:**
- Parse dozens of historical resumes (zero failures tolerated)
- Measure roundtrip accuracy (YAML and LaTeX diffs)
- Track systematic improvements

## Implementation Status

### ✅ Complete Features

**Content Types (11/11):**
- ✅ All types implemented with template-based generation
- ✅ Operation-based parsing via unified `parse_with_config()`
- ✅ Round-trip validation for all types

**Document Structure:**
- ✅ Multi-page support with `\clearpage` handling
- ✅ Page metadata (`has_clearpage_after`) for conditional clearpage generation
- ✅ Two-column paracol structure (left_column, main_column)
- ✅ Bottom bar extraction and generation (textblock positioning)
- ✅ Decoration passthrough (gradients, positioning commands)
- ✅ Document metadata extraction from preamble (colors, spacing, profile)
- ✅ Dual storage for formatted metadata fields (raw + plaintext)

**Template System:**
- ✅ Hierarchical template organization (structure/wrappers/types)
- ✅ Custom Jinja2 delimiters for LaTeX compatibility
- ✅ Template caching for performance
- ✅ Enhanced error messages with template references

**Roundtrip Testing (over 50 historical resumes):**
- ✅ **100% YAML roundtrip** - Perfect semantic structure preservation
- ✅ **~85% LaTeX roundtrip** - Exact LaTeX output matching input
- ✅ 35 passing integration tests covering all types and document structures
- ✅ Zero parsing errors across entire archive

**Remaining LaTeX diffs (10 files, 24 total diff lines):**
- Extra blank lines (cosmetic)
- Minor formatting variations (e.g., `7pt` vs `7.5pt` parskip)
- Spacing around decorations (cosmetic)
- None affect semantic content or visual appearance

## Key Files

**Core modules:**
- `converter.py` - Public API (`yaml_to_latex()`, `latex_to_yaml()`)
- `latex_generator.py` - Template-based LaTeX generation (`YAMLToLaTeXConverter`)
- `latex_parser.py` - Operation-based parsing (`LaTeXToYAMLConverter`, `parse_with_config()`)
- `registries.py` - Template and config loading (`TemplateRegistry`, `ParseConfigRegistry`)
- `latex_patterns.py` - Centralized regex patterns and constants

**Utilities:**
- `process_latex_archive.py` - Batch processing for historical resumes
- `../utils/latex_parsing_tools.py` - Reusable parsing helpers (zero project dependencies)

## Usage Examples

### Convert Historical Resume

```python
from archer.contexts.templating.converter import yaml_to_latex, latex_to_yaml
from pathlib import Path

# Parse existing resume
yaml_data = latex_to_yaml(Path("data/resume_archive/Res202410_SomeCompany.tex"))

# Modify content (e.g., via Targeting context)
yaml_data["document"]["pages"][0]["regions"]["main_column"]["sections"][0]["content"]["bullets"][0]["latex_raw"] = "Updated bullet"

# Generate new resume
new_latex = yaml_to_latex(yaml_data)
Path("outs/resumes/modified_resume.tex").write_text(new_latex)
```

### Type-Specific Conversion (for testing/debugging)

```python
from archer.contexts.templating.latex_parser import LaTeXToYAMLConverter
from archer.contexts.templating.latex_generator import YAMLToLaTeXConverter

# Convert just a skill section
skill_section_latex = r"""
\item[] {\scshape Languages}
\addcontentsline{toc}{section}{ Languages}

\begin{itemizeLL}
    \item[--] {Python}
    \item[--] {Bash}
\end{itemizeLL}
"""

parser = LaTeXToYAMLConverter()
skill_yaml = parser.parse_skill_category(skill_section_latex.strip())

# Modify and regenerate
skill_yaml["content"]["items"].append({"marker": "item[--]", "latex_raw": "{C++}", "plaintext": "C++"})
generator = YAMLToLaTeXConverter()
new_latex = generator.convert_skill_category(skill_yaml)
```

## Testing

Run integration tests:

```bash
# All templating tests
pytest tests/integration/test_*.py -v

# Specific type tests
pytest tests/integration/test_work_experience.py -v
pytest tests/integration/test_skill_types.py -v

# Round-trip test on historical resume
python scripts/test_roundtrip.py data/resume_archive/Res202410_Example.tex
```

## Environment Variables

Required in `.env`:

```bash
RESUME_COMPONENT_TYPES_PATH=/home/sean/ARCHER/archer/contexts/templating/template/types
TEMPLATING_CONTEXT_PATH=/home/sean/ARCHER/archer/contexts/templating
```

## Architecture Principles

### Core Design

1. **Operation-based parsing**: Unified `parse_with_config()` reads operations from declarative YAML configs
2. **Config-driven patterns**: Parsing patterns in `parse_config.yaml`, not Python code
3. **Template-based generation**: LaTeX structure in Jinja templates, not string concatenation
4. **Co-located definitions**: Each type's type.yaml, template, and parse config live together
5. **Enhanced diagnostics**: Errors reference template files and show expected patterns

This document represents the culmination of iterative refinement toward a clean, maintainable, and highly accurate bidirectional conversion system.
