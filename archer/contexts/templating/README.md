# Templating Context

The Templating context owns the structured representation of resume documents and handles bidirectional conversion between LaTeX (.tex) files and structured YAML format.

## Type System

Resume content is organized into **types** that define the structure and LaTeX representation of resume elements. Each type specifies:
- LaTeX environment or command structure
- Required and optional metadata fields
- Content structure rules

Type definitions are stored in `data/resume_archive/structured/types/*.yaml`.

### Current Types

**work_experience** - Job position with company, title, location, dates, bullets, and optional nested projects (uses `itemizeAcademic` environment)

**project** - Nested project within work experience with title, dates, and bullets (uses `itemizeAProject` or `itemizeKeyProject`)

**skill_list_caps** - All-caps unbulleted skill list with small-caps formatting (e.g., Core Skills sections)

## Data Structures

**ResumeDocument** - Complete resume representation with fields, sections, and metadata

**ResumeSection** - Individual section with name and raw content

**DocumentMetadata** - Document-level metadata (name, date, brand, professional profile)

**Page** - Page structure with page number and regions (top, left_column, main_column)

**Section** - Typed section with name, type, content, and optional subsections

## Converter

**TypeRegistry** - Loads and caches type definitions from YAML files

**YAMLToLaTeXConverter** - Generates LaTeX from structured YAML using type definitions (currently supports work_experience, project, skill_list_caps)

**LaTeXToYAMLConverter** - Parses LaTeX to structured YAML format (currently supports work_experience, project, skill_list_caps)

## Roadmap

- Add remaining content types (skill_list_pipes, skill_categories, education)
- Implement page-level parsing and generation
- Add complete document metadata extraction
- Add round-trip validation tests
