# Design Decisions

This document records architectural and design decisions made during ARCHER's development.

---

## Four Bounded Contexts

**Decision**: Structure ARCHER using four bounded contexts (Intake, Targeting, Templating, Rendering) based on Domain-Driven Design principles.

Resume generation involves distinct concerns: parsing job descriptions, selecting relevant content, building LaTeX documents, and compiling PDFs. These concerns have different inputs, outputs, and responsibilities.

