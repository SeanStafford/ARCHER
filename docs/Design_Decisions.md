# Design Decisions

This document records architectural and design decisions made during ARCHER's development. Each entry includes the issue that motivated the decision and the reasoning behind it.

---

## Design Decision 1: Four Bounded Contexts

**Date**: Oct 22, 2025

**Decision**: Structure ARCHER using four bounded contexts (Intake, Targeting, Templating, Rendering) based on Domain-Driven Design principles.

**Issue**: Resume generation involves distinct concerns: parsing job descriptions, selecting relevant content, building LaTeX documents, and compiling PDFs. These concerns have different inputs, outputs, and responsibilities.

**Rationale**:
- Separating concerns makes the codebase easier to understand and modify
- Each context can be developed and tested independently
- Clear boundaries prevent one context from making decisions that belong to another
- Reduces coupling between different parts of the system

**Trade-offs**: Requires more upfront planning and adds some communication overhead between contexts.

---

## Design Decision 2: Templating Context In Charge of Resume Structure

**Date**: Oct 23, 2025

**Decision**: The Templating context is responsible for converting between LaTeX (.tex) files and structured data representations of resumes.

**Issue**: Two contexts need to work with resume content:
- Targeting needs to search and analyze historical resumes
- Templating needs to populate templates with selected content

The question was whether to create a shared data model or assign structure conversion to one context.

**Rationale**:
- Templating already owns the LaTeX template system
- Converting .tex → structured data and structured data → .tex are related operations
- Targeting works with structured data (not raw LaTeX), keeping its focus on analysis
- Avoids introducing a shared model that would need to coordinate between contexts
- Simplifies the architecture - one context owns all structure-related concerns

**Implementation**: Targeting operates on structured resume data provided by Templating's conversion utilities. Templating provides both parsing (tex → data) and serialization (data → tex) capabilities.

---

## Design Decision 3: Historical Resume Analysis in Targeting Context

**Date**: Oct 23, 2025

**Decision**: Resume pattern analysis tools (keyword frequency, field analysis, section matching) belong in the Targeting context rather than general utilities.

**Issue**: Analysis tools were initially developed as standalone utilities in `archer/utils/resume_analyzer.py`. As the system grew, it became unclear whether these were generic utilities or domain logic.

**Rationale**:
- These tools directly support Targeting's responsibility for "historical resume indexing/search"
- Pattern analysis informs content prioritization decisions
- The analysis is specific to resume targeting, not a general-purpose capability
- Placing them in Targeting makes ownership clear

**Location**: Analysis tools moved to `archer/contexts/targeting/analysis.py`.

---

## Design Decision 4: Use OmegaConf and YAML for Structured Resume Format

**Date**: Oct 23, 2025

**Decision**: Use YAML as the structured format for resume documents, with OmegaConf as the library for reading/writing YAML files.

**Issue**: The Templating context needs a structured intermediate format that is:
- Human-readable for debugging and manual editing
- Machine-parseable for algorithmic manipulation
- Capable of round-trip conversion with LaTeX (no data loss)
- Type-safe with schema validation

**Rationale**:
- YAML is more readable than JSON for hierarchical documents with long text content
- OmegaConf provides schema validation, type checking, and variable interpolation
- OmegaConf is already a project dependency (used for configuration)
- YAML's multiline strings handle LaTeX commands better than JSON's escaped strings
- Consistent formatting conventions enable clean version control diffs

**Trade-offs**:
- YAML parsing is slower than JSON, but not performance-critical for this use case
- Learning curve for OmegaConf's specific conventions (e.g., single backslashes, line wrapping)

**Implementation**: All resume YAML files follow OmegaConf formatting conventions (documented in CLAUDE.md). Type definitions stored in `data/resume_archive/structured/types/` guide conversion between YAML and LaTeX.
