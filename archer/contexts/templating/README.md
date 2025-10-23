# Templating Context

The Templating context owns the structured representation of resume documents and handles bidirectional conversion between LaTeX (.tex) files and structured YAML format.

## Type System

Resume content is organized into **types** that define the structure and LaTeX representation of resume elements. Each type specifies:
- LaTeX environment or command structure
- Required and optional metadata fields
- Content structure rules

Type definitions are stored in `data/resume_archive/structured/types/*.yaml`.

## Current Types

**work_experience** - Job position with company, title, location, dates, bullets, and optional nested projects (uses `itemizeAcademic` environment)

**project** - Nested project within work experience with title, dates, and bullets (uses `itemizeAProject` or `itemizeKeyProject`)

**skill_list_caps** - All-caps unbulleted skill list with small-caps formatting (e.g., Core Skills sections)

## Roadmap

This context will implement parsers and generators to enable:
- LaTeX → YAML conversion for mining historical resume content
- YAML → LaTeX generation for producing tailored resumes
- Complete document structure handling (pages, columns, metadata)
