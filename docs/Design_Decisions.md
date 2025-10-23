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
