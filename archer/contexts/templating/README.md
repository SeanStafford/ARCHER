# Templating Context

The Templating context owns the structured representation of resume documents and handles bidirectional conversion between LaTeX (.tex) files and structured YAML format.

## Type System

Resume content is organized into **types** that define the structure and LaTeX representation of resume elements. Each type specifies:
- LaTeX environment or command structure
- Required and optional metadata fields
- Content structure rules

Type definitions are stored in `data/resume_archive/structured/types/*.yaml`.

### Implemented Types

**work_experience** - Job position with company, title, location, dates, bullets, and optional nested projects (uses `itemizeAcademic` environment)

**project** - Nested project within work experience with title, dates, and bullets (uses `itemizeAProject` or `itemizeKeyProject`)

**skill_list_caps** - All-caps unbulleted skill list with small-caps formatting (e.g., Core Skills sections)

**skill_list_pipes** - Pipe-separated inline skill list with monospace formatting (e.g., Languages: `Python | Bash | C++`)

**skill_categories** - Hierarchical skill section with FontAwesome icons and nested categories

**skill_category** - Individual category within skill_categories (icon + small-caps header + dashed list)

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

**TypeRegistry** - Loads and caches type definitions from YAML files

### YAMLToLaTeXConverter

Generates LaTeX from structured YAML:

**Type-specific generators:**
- `convert_work_experience()` - itemizeAcademic environment
- `convert_project()` - itemizeAProject environment
- `convert_skill_list_caps()` - Braced small-caps list
- `convert_skill_list_pipes()` - Pipe-separated `\texttt{}` list
- `convert_skill_category()` - Single category with icon
- `convert_skill_categories()` - Nested itemize with multiple categories

**Document-level generation:**
- `generate_preamble()` - Document metadata → `\renewcommand` statements
- `generate_page()` - Assembles complete page with paracol structure, left/main columns, sections
- `_generate_section()` - Generates LaTeX for individual section (handles type dispatch)

### LaTeXToYAMLConverter

Parses LaTeX to structured YAML:

**Type-specific parsers:**
- `parse_work_experience()` - itemizeAcademic → structured dict
- `_parse_project()` - itemizeAProject → structured dict
- `parse_skill_list_caps()` - Braced list → structured dict
- `parse_skill_list_pipes()` - Pipe-separated list → structured dict
- `_parse_skill_category()` - Single category → structured dict
- `parse_skill_categories()` - Nested itemize → structured dict

**Document-level parsing:**
- `extract_document_metadata()` - Parses preamble for `\renewcommand` fields and colors
- `extract_pages()` - Splits document on `\clearpage` markers, parses each page separately
- `extract_page_regions()` - Parses paracol environment, splits on `\switchcolumn`
- `_extract_sections_from_column()` - Extracts all sections from column content
- `_parse_section_by_inference()` - Automatically detects section type from LaTeX patterns

## Implementation Status

### Completed Features

**Content Type Parsing & Generation:**
- ✅ All 6 content types (work_experience, project, skill_list_caps, skill_list_pipes, skill_categories, skill_category)
- ✅ Round-trip validation for all types (LaTeX → YAML → LaTeX produces identical output)

**Document Structure:**
- ✅ Single-page parsing and generation (paracol two-column structure)
- ✅ Multi-page support with `\clearpage` handling
- ✅ Automatic section type inference from LaTeX patterns
- ✅ Document metadata extraction from preamble

**Testing:**
- ✅ Integration tests for all content types
- ✅ Page structure tests (column separation, section ordering)
- ✅ Multi-page tests (page splitting, continuation pages)
- ✅ Document metadata tests (preamble parsing, round-trip validation)

**Documentation:**
- ✅ Comprehensive testing documentation in `tests/ResumeStructureTesting.md`
- ✅ Demo notebooks for page structure (step 4), metadata (step 5), and multi-page (step 6)

### Not Yet Implemented

- Complete document assembly (`parse_document`, `generate_document`)
- Education section type
- Personality section types (unbulleted, inline)
- Bottom bar extraction and generation

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
