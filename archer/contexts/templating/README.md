# Templating Context

The Templating context owns the structured representation of resume documents and handles bidirectional conversion between LaTeX (.tex) files and structured YAML format.

## Type System

Resume content is organized into **types** that define the structure and LaTeX representation of resume elements. Each type specifies:
- LaTeX environment or command structure
- Required and optional metadata fields
- Content structure rules

### Template-Based Architecture

**Type Directory Structure:**
```
archer/contexts/templating/types/
├── work_experience/
│   ├── type.yaml              # Schema definition
│   └── template.tex.jinja     # LaTeX template with placeholders
├── project/
│   ├── type.yaml
│   └── template.tex.jinja
├── skill_list_caps/
│   ├── type.yaml
│   └── template.tex.jinja
└── ... (9 types total)
```

Each type has:
- **`type.yaml`**: Schema defining metadata fields, content structure, LaTeX environment
- **`template.tex.jinja`**: Jinja2 template with LaTeX pattern and placeholders

**Benefits:**
- **Visibility**: LaTeX patterns explicit in template files (not buried in Python code)
- **Maintainability**: Single source of truth for each type's LaTeX structure
- **Better Errors**: Parser errors can reference template file + line number
- **Cleaner Code**: Generators simplified from string concatenation to template rendering

**Custom Delimiters** (to avoid LaTeX brace conflicts):
- Variables: `<<< var >>>`
- Blocks: `<%% block %%>`
- Comments: `<# comment #>`

### Implemented Types

**work_experience** - Job position with company, title, location, dates, bullets, and optional nested projects (uses `itemizeAcademic` environment)

**project** - Nested project within work experience with title, dates, and bullets (uses `itemizeAProject` or `itemizeKeyProject`)

**skill_list_caps** - All-caps unbulleted skill list with small-caps formatting (e.g., Core Skills sections)

**skill_list_pipes** - Pipe-separated inline skill list with monospace formatting (e.g., Languages: `Python | Bash | C++`)

**skill_categories** - Hierarchical skill section with FontAwesome icons and nested categories

**skill_category** - Individual category within skill_categories (icon + small-caps header + dashed list)

**education** - Academic credentials with multi-institution, multi-degree structure and optional details (uses nested `itemize` with `\faUserGraduate` icon)

**personality_alias_array** - Personality section with icon-labeled items (uses `itemizeMain` environment, e.g., "Bash Black Belt")

**personality_bottom_bar** - Bottom bar positioned with textblock for personality content (e.g., "Two Truths and a Lie")

## Data Structures

### Resume Components

**ResumeDocument** - Complete resume representation with fields, sections, and metadata. Primary data model shared between Templating and Targeting contexts.

**ResumeSection** - Individual section with name and raw content

**DocumentMetadata** - Document-level metadata from preamble (name, date, brand, professional profile, colors)

**Page** - Page structure with page number and regions (top, left_column, main_column, bottom)

**PageRegions** - Two-column paracol structure with top bar, left column, main column, optional bottom bar

**Column** - Ordered list of sections within a column

**Section** - Typed section with name, type, content, and optional subsections

**Subsection** - Nested content within sections (work experience entries, skill categories)

**TopBar** / **BottomBar** - Page header/footer regions

### LaTeX Pattern Constants

**latex_patterns.py** - Centralized pattern definitions organized into frozen dataclasses:

- **DocumentPatterns** - Document boundaries (`\begin{document}`, `\end{document}`, `\clearpage`)
- **PagePatterns** - Paracol structure (`\begin{paracol}{2}`, `\switchcolumn`, `\end{paracol}`)
- **SectionPatterns** - Section markers (`\section*`)
- **EnvironmentPatterns** - Custom environments (itemizeAcademic, itemizeAProject, itemizeLL)
- **MetadataPatterns** - Preamble commands (`\renewcommand`, field names)
- **ColorFields** - Color field enumeration (emphcolor, topbarcolor, etc.)
- **FormattingPatterns** - Formatting commands (`\textbf`, `\scshape`, `\texttt`, etc.)

## Converter Architecture

**TypeRegistry** - Loads and caches type definitions from `type.yaml` files

**TemplateRegistry** - Loads and caches Jinja2 templates from `template.tex.jinja` files
- Custom Jinja2 environment with LaTeX-safe delimiters
- Template caching for performance
- Helper methods for error messages: `get_template_source()`, `get_expected_pattern_preview()`

### YAMLToLaTeXConverter

Generates LaTeX from structured YAML using template-based approach:

**Type-specific generators** (all use template rendering):
- `convert_work_experience()` - Renders work_experience template
- `convert_project()` - Renders project template
- `convert_skill_list_caps()` - Renders skill_list_caps template
- `convert_skill_list_pipes()` - Renders skill_list_pipes template
- `convert_skill_category()` - Renders skill_category template
- `convert_skill_categories()` - Renders skill_categories template (nested)
- `convert_education()` - Renders education template
- `convert_personality_alias_array()` - Renders personality_alias_array template
- `generate_bottom_bar()` - Renders personality_bottom_bar template

**Pattern** (simplified from string concatenation):
```python
def convert_skill_list_caps(self, section: Dict[str, Any]) -> str:
    template = self.template_registry.get_template("skill_list_caps")
    return template.render(section)
```

**Document-level generation:**
- `generate_preamble()` - Document metadata → `\renewcommand` statements
- `generate_page()` - Assembles complete page with paracol structure, left/main columns, sections, bottom bar
- `generate_document()` - Complete document assembly (preamble + pages + clearpage markers)
- `_generate_section()` - Generates LaTeX for individual section (handles type dispatch)

### LaTeXToYAMLConverter

Parses LaTeX to structured YAML with enhanced error handling:

**Type-specific parsers:**
- `parse_work_experience()` - itemizeAcademic → structured dict
- `_parse_project()` - itemizeAProject → structured dict
- `parse_skill_list_caps()` - Braced list → structured dict
- `parse_skill_list_pipes()` - Pipe-separated list → structured dict
- `_parse_skill_category()` - Single category → structured dict
- `parse_skill_categories()` - Nested itemize → structured dict
- `parse_education()` - Multi-institution nested itemize → structured dict
- `parse_personality_alias_array()` - itemizeMain → structured dict
- `extract_bottom_bar()` - Textblock bottom bar → structured dict

**Document-level parsing:**
- `extract_document_metadata()` - Parses preamble for `\renewcommand` fields and colors
- `extract_pages()` - Splits document on `\clearpage` markers, parses each page separately
- `extract_page_regions()` - Parses paracol environment, splits on `\switchcolumn`, extracts bottom bar
- `parse_document()` - Complete document parsing (metadata + pages)
- `_extract_sections_from_column()` - Extracts all sections from column content
- `_parse_section_by_inference()` - Automatically detects section type from LaTeX patterns

**Enhanced Error Handling:**
- `_create_parsing_error()` - Creates `TemplateParsingError` with template path reference
- Parser errors now show:
  - Expected pattern from template file
  - Template file path and type name
  - Actual LaTeX snippet that failed to parse
- Example error message:
  ```
  Failed to parse skill_category: No \item[icon] {\scshape name} pattern found
  Expected pattern from: archer/contexts/templating/types/skill_category/template.tex.jinja
  Type: skill_category
  Actual LaTeX:
  \item[]{\hspace{-20pt}\scshape Category Name}
  ```

## Implementation Status

### Completed Features

**Content Type Parsing & Generation:**
- ✅ All 9 content types fully implemented:
  - work_experience, project (experience and projects)
  - skill_list_caps, skill_list_pipes, skill_categories, skill_category (3 skill types)
  - education (academic credentials)
  - personality_alias_array, personality_bottom_bar (2 personality types)
- ✅ Round-trip validation for all types (LaTeX → YAML → LaTeX produces identical output)

**Document Structure:**
- ✅ Single-page parsing and generation (paracol two-column structure)
- ✅ Multi-page support with `\clearpage` handling
- ✅ Bottom bar extraction and generation (textblock positioning)
- ✅ Automatic section type inference from LaTeX patterns
- ✅ Document metadata extraction from preamble
- ✅ Complete document assembly (`parse_document`, `generate_document`)

**High-Level API:**
- ✅ `latex_to_yaml()` - Convert LaTeX files to YAML (supports full documents and components)
- ✅ `yaml_to_latex()` - Convert YAML to LaTeX (supports full documents and components)

**Template-Based Generation:**
- ✅ All 9 types use Jinja2 templates (migrated from string concatenation)
- ✅ Type definitions and templates co-located in `archer/contexts/templating/types/`
- ✅ Custom delimiters avoid LaTeX brace conflicts (`<<< >>>`, `<%% %%>`)
- ✅ Enhanced error messages with template path references
- ✅ 90% reduction in generator code size (string concat → template.render())
- ✅ TemplateRegistry with caching and helper methods

**Testing:**
- ✅ 35 passing integration tests covering:
  - All content type round-trips (work_experience, project, all skill types, education, personality types)
  - Page structure tests (column separation, section ordering)
  - Multi-page tests (page splitting, continuation pages)
  - Document metadata tests (preamble parsing, round-trip validation)
  - Bottom bar tests (extraction, generation, round-trip)
- ✅ 8 passing TemplateRegistry unit tests

**Documentation:**
- ✅ Comprehensive testing documentation in `tests/ResumeStructureTesting.md`
- ✅ Demo notebooks: page structure (step 4), metadata (step 5), multi-page (step 6), complete system (step 7)

## Testing

All implemented types have comprehensive round-trip validation tests ensuring LaTeX → YAML → LaTeX produces identical output (ignoring cosmetic whitespace).

**Test Coverage:**
- Individual type round-trips (work_experience, project, all skill types)
- Page structure parsing and generation (paracol, column separation, section ordering)
- Complete single-page resumes with multiple section types
- Multi-page resumes with `\clearpage` markers and continuation pages
- Document metadata extraction and preamble generation

See `tests/ResumeStructureTesting.md` for detailed testing philosophy, edge cases, and coverage matrix.

## Demo Notebooks

- `step4_page_structure_demo.ipynb` - Single-page paracol structure parsing and generation
- `step5_document_metadata_demo.ipynb` - Document metadata extraction from preamble
- `step6_two_page_demo.ipynb` - Multi-page document parsing with `\clearpage` handling
- `step7_complete_document_demo.ipynb` - Complete system demonstration (all 9 types, bottom bar, document assembly)
