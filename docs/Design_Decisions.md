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

---

## Design Decision 5: Dynamic Validation for Integration Tests

**Date**: Oct 23, 2025

**Decision**: Integration tests validate parser/generator output against YAML test fixtures dynamically, rather than hardcoding expected values in test code.

**Issue**: Integration tests were failing when test fixtures were updated during commits. Tests contained hardcoded assertions like:
```python
assert metadata["date"] == "July 2025"
assert len(result["content"]["list"]) == 8
```

These hardcoded values became stale when fixtures were simplified (e.g., list shortened to 2 items). This created test fragility.

**Considered Alternatives**:
1. **Strategy 1 (Chosen)**: Load YAML fixtures dynamically and validate parsed values match them
2. **Strategy 2**: Validate only structure/types, not specific values
3. **Strategy 3**: Remove individual parse/generate tests, keep only round-trip tests

**Rationale for Strategy 1**:
- **Eliminates hardcoding fragility** - test file changes automatically update expected values
- **Maintains content validation** - still catches content corruption (e.g., parser swapping fields)
- **Explicit test intent** - "LaTeX parsing should match the YAML specification"
- **Granular failure messages** - easier to debug which conversion direction failed
- **Complements round-trip tests** - validates individual directions, not just full round-trips

**Implementation**:
```python
def test_parse_document_metadata():
    latex_path = STRUCTURED_PATH / "document_metadata_test.tex"
    yaml_path = STRUCTURED_PATH / "document_metadata_test.yaml"

    # Load expected values from YAML fixture
    expected = OmegaConf.to_container(OmegaConf.load(yaml_path))["document"]["metadata"]

    # Parse LaTeX
    parser = LaTeXToYAMLConverter()
    metadata = parser.extract_document_metadata(latex_path.read_text())

    # Validate against expected values (dynamic, not hardcoded)
    assert metadata["name"] == expected["name"]
    assert metadata["date"] == expected["date"]
```

**Trade-offs**:
- Tests now have dependency on YAML fixtures (test files must exist and be valid)
- Slightly more complex test setup (load YAML, navigate structure)
- Better long-term maintainability outweighs minor complexity increase

---

## Design Decision 6: Project-Specific LaTeX Patterns Over General Parsing

**Date**: Oct 24, 2025

**Decision**: Use pattern matching for project-specific LaTeX conventions rather than implementing a general-purpose LaTeX parser.

**Issue**: The Templating context needs to parse LaTeX resumes into structured data. Two approaches were possible:
1. Build a general LaTeX parser that handles arbitrary documents
2. Use regex patterns matching ARCHER's specific LaTeX conventions

**Rationale**:
- **Speed to functionality** - Pattern matching is significantly faster to implement than general parsing
- **Controlled environment** - All ~60 historical resumes follow the same template conventions (single paracol, custom environments from `mystyle/*.sty`, consistent section patterns)
- **Simplicity** - Regex patterns are straightforward to understand, debug, and maintain
- **Reliability** - Patterns are stable across years of historical resumes; 35 integration tests validate all patterns
- **User context** - Single user actively job searching needs functional tool immediately, not future-proof general solution

**Trade-offs**:
- Parser only works with ARCHER's template system, not arbitrary LaTeX resumes
- Template changes require parser updates (documented in `latex_pattern_assumptions.md`)
- Future users with different templates would need custom patterns or parser modifications

**Implementation**: All patterns centralized in `latex_patterns.py` with comprehensive documentation in `archer/contexts/templating/latex_pattern_assumptions.md` explaining each assumption and breaking conditions.

---

## Design Decision 7: Template-Based Type System

**Date**: Oct 24, 2025

**Decision**: Replace code-based LaTeX generation with Jinja2 templates, co-locating template files with type definitions in `archer/contexts/templating/types/`.

**Issue**: Round-trip conversion failed on real historical resumes due to unexpected pattern variations:
- Expected `\itemLL {PyTorch}`, encountered `\itemLL \texttt{PyTorch}`
- Expected `\item[\faIcon] {\scshape Name}`, encountered `\item[]{\hspace{-20pt}\scshape Name}`
- Expected `\itemLL {item}`, encountered `\item[--] {item}`

LaTeX patterns were embedded in Python string concatenation, making variations invisible until parse failures occurred.

**Rationale**:
- **Visibility** - Templates make expected LaTeX patterns explicit and inspectable; deviations become immediately obvious
- **Maintainability** - Single source of truth: template defines both generation output and parsing expectations
- **Better diagnostics** - Parser errors can reference specific template files and line numbers
- **Cleaner code** - Eliminates string concatenation in generators; separation of formatting (LaTeX) from logic (Python)
- **Foundation for variation support** - Externalizing patterns enables future support for multiple template variants per type

**Trade-offs**:
- Does not immediately fix pattern variations (still requires parser updates to handle new patterns)
- Adds Jinja2 dependency and requires migration effort (9 types × ~1 hour each)
- Template syntax errors become runtime errors instead of Python syntax errors
- What it DOES do: Makes pattern mismatches visible and provides clear path forward

**Implementation**: See `archer/contexts/templating/NEW_TYPE_APPROACH.md` for full specification. Migration plan: (1) POC with `skill_list_caps`, (2) incremental migration of remaining 8 types, (3) enhanced error messages referencing templates, (4) documentation updates.

**Update - Completed Oct 24, 2025:**
All 4 stages complete. 9 types migrated to template-based generation. 35 integration tests + 8 unit tests passing. Major reduction in generator code size.

---

## Design Decision 8: Symmetric Template-Based Bidirectional Conversion

**Date**: Oct 24, 2025

**Decision**: Use declarative YAML configs to drive LaTeX parsing, mirroring the template-based approach already used for generation.

**Issue**: After migrating generation to Jinja2 templates (Decision 7), an asymmetry remained:
- **Generation (YAML → LaTeX)**: Template-based, declarative, patterns visible in `.tex.jinja` files
- **Parsing (LaTeX → YAML)**: Code-based, hardcoded regex in Python methods, patterns buried in code

This asymmetry made parsing patterns invisible and difficult to maintain. Changes to LaTeX structure required finding and updating regex in Python code.

**Rationale**:
- **Symmetry** - Both conversion directions now use declarative templates (Jinja2 for generation, YAML configs for parsing)
- **Visibility** - Regex patterns externalized to YAML files, easily inspectable alongside generation templates
- **Maintainability** - Pattern changes require editing config files, not Python code
- **Generic implementation** - Single `parse_with_config()` function works for all 9 types by loading their parsing configs
- **Foundation for variants** - Easy to add alternative parsing configs for historical resume pattern variations

**Implementation**: Each type directory contains `parse_config.yaml` alongside `template.tex.jinja`. Parsing configs declare regex patterns, capture groups, and field mappings using dot notation for nested structures (e.g., `content.list`). Generic parser function in `converter.py` loads configs and extracts data. See `notebooks/template_bidirectional_demo.ipynb` for pedagogical demonstration.

---

## Design Decision 9: Dual Storage Pattern for Metadata and Content

**Date**: Oct 26, 2025

**Decision**: Store both raw LaTeX and plaintext versions for metadata fields and content items that can contain formatting.

**Issue**: The Templating context needs perfect LaTeX roundtrip preservation, but the future Targeting context will need plaintext for semantic analysis (keyword matching, relevance scoring). Destructively stripping LaTeX formatting loses information needed for roundtrip, while keeping only raw LaTeX forces Targeting to parse LaTeX for every analysis operation.

**Rationale**:
- **Separation of concerns** - Templating uses raw LaTeX for generation, Targeting uses plaintext for analysis
- **No LaTeX parsing in Targeting** - Targeting context can operate entirely on plaintext without understanding LaTeX syntax
- **Perfect roundtrip** - Raw fields preserve exact formatting (e.g., whether `\textbf` wrapper was present)
- **Future-proof** - Structure anticipates Targeting context needs before implementation

**Implementation**:
- Metadata fields: Store `name` + `name_plaintext`, `professional_profile` + `professional_profile_plaintext`
- Content items: Store `marker`, `latex_raw`, and `plaintext` for each bullet
- Utility function `to_plaintext()` in `latex_parsing_tools.py` strips all LaTeX commands

**Trade-offs**: Increases YAML file size (~30-40%) and storage overhead, but negligible for a few dozen yamls.

---

## Design Decision 10: Processing Modes Architecture - Clean vs Normalize

**Date**: Oct 26, 2025

**Decision**: Treat normalization as a complete processing mode with its own philosophy, not as a feature toggle applied after cleaning.

**Issue**: Originally designed as three separate modules (`clean_latex.py`, `normalize_latex.py`, `process_latex.py`) suggesting normalization was an optional add-on to cleaning. This created confusion about whether you could "normalize while keeping some comments" or apply granular control to normalization.

**Rationale**:
- **Conceptual clarity** - Normalization is inherently opinionated about what the output should contain; it's a complete processing strategy, not a post-processing step
- **Architectural accuracy** - The system has two distinct modes of operation, not one mode with optional features
- **Clean Mode** provides granular control over comment removal for targeted cleanup
- **Normalize Mode** applies opinionated full processing (removes ALL comments, normalizes blank lines, standardizes Education headers, strips trailing whitespace)

**Implementation**: Consolidated to two files (`clean_latex.py` for low-level utilities, `process_latex_archive.py` for orchestration). The `normalize` parameter selects between modes. Warning system alerts users if they provide cleaning flags with `--normalize` (flags are ignored in Normalize Mode).

**Trade-offs**: Less flexibility in Normalize Mode (can't selectively preserve comments), but this is intentional - normalization requires consistent opinions about output format.

---

## Design Decision 11: Self-Contained LaTeX Parsing Utilities

**Date**: Oct 26, 2025

**Decision**: Make `archer/utils/latex_parsing_tools.py` completely self-contained with zero project dependencies, storing all regex patterns as named constants at the top of the file.

**Issue**: LaTeX parsing patterns were scattered as inline regex throughout converter code and in project-specific pattern files. The user explicitly requested utilities that could be reused in other LaTeX projects without ARCHER dependencies.

**Rationale**:
- **Reusability** - Zero project dependencies means the module can be dropped into any LaTeX project
- **Visibility** - All patterns defined as named constants at top of file, eliminating hidden inline regex
- **Maintainability** - Pattern changes happen in one place (constant definition), not scattered across function bodies
- **Clarity** - Descriptive function names (`unwrap_command()`, `strip_formatting()`) clearer than raw `re.sub()` calls

**Implementation**: Created `LaTeXPatterns` dataclass with pattern templates using format strings (e.g., `r'\\{command}\s*'`). Functions use only stdlib imports (`re`, `typing`, `dataclasses`). All project-specific patterns remain in `latex_patterns.py` within the templating context.

**Trade-offs**: Some duplication between `LaTeXPatterns` (general) and `latex_patterns.py` (project-specific), but clean separation enables reuse.

---

## Design Decision 12: Hybrid Approach to Itemize Extraction

**Date**: Oct 26, 2025

**Decision**: Add `simple_list` fallback type for unknown itemize environments, defer enhanced utility consolidation, reject low-level extraction layer.

**Issue**: Found ~60 lines of duplicated itemize extraction logic across 6 parsers, and 31 sections (56% of resumes) were falling through to `type: unknown` because they used itemize environments that didn't match known semantic types. Three options were considered: (1) low-level extraction layer with two-pass processing, (2) enhanced utility function to consolidate extraction, (3) fallback generic list type.

**Rationale**:
- **Pragmatic solution** - The actual problem is 31 unknown sections, not code duplication
- **Minimal risk** - Adding one new type is isolated change with no impact on working parsers
- **Current architecture works** - 98% diff reduction already achieved; tight 1:1 coupling between environments and types is good design (self-documenting, type-safe)
- **Two-pass processing not justified** - All 6 itemize-based types are well-defined; extracting before type inference adds complexity for unclear benefit

**Implementation**: Created `simple_list` type with config-driven parsing. Captures environment name, item command, and items list. Falls back to this type for any itemize environment not matching known semantic patterns. Enhanced utility consolidation deferred as optional future improvement.

**Trade-offs**: Duplication remains in 6 parsers (~60 lines), but acceptable given working state and low maintenance burden.

---

## Design Decision 13: Normalization Convergence

**Date**: Nov 3, 2025

**Decision**: Implement `apply_normalization_until_convergence()` that runs normalization rules repeatedly until output stabilizes.

**Issue**: Single-pass normalization was insufficient because rule interactions created new patterns that triggered other rules. For example, textblock repositioning could move `\vspace` commands adjacent to `\switchcolumn`, triggering column boundary spacing rules that weren't applied in the first pass.

**Rationale**:
- **Rule interactions** - Normalization rules can create new patterns that match other rules' conditions
- **Order dependencies** - The sequence in which rules are applied affects whether subsequent rules trigger
- **Stable output** - Convergence ensures consistent results regardless of initial state or rule ordering
- **Correctness** - Guarantees all applicable normalizations are applied, not just those visible in initial pass

**Implementation**: Wrapper function runs normalization rules repeatedly, comparing output after each pass. Stops when two consecutive passes produce identical output. Includes safety limit to prevent infinite loops if rules conflict.

**Trade-offs**: Slower processing (typically 2-3 passes instead of 1), but correctness requirement outweighs performance concern for archive processing.

---

## Design Decision 14: Acceptance Criteria for Roundtrip Fidelity

**Date**: Nov 3, 2025

**Decision**: Establish 81.8% LaTeX roundtrip pass rate as acceptable for production quality, consciously not fixing remaining cosmetic differences.

**Issue**: After achieving 100% YAML roundtrip and 81.8% LaTeX roundtrip, identified remaining issues including: 2 resumes with `\setlength{\parskip}{7pt}` becoming `7.5pt` (hardcoded in template), extra blank lines in some outputs, and minor spacing variations around decorations.

**Rationale**:
- **Cost-benefit analysis** - Remaining differences are cosmetic and don't affect rendered PDF appearance
- **Diminishing returns** - Fixing 7pt→7.5pt would require extracting parskip as optional metadata for 2 resumes (4% of archive)
- **Perfect fidelity not required** - 100% YAML roundtrip guarantees semantic preservation; LaTeX differences are formatting only
- **Pragmatic engineering** - Effort to eliminate final 24 diff lines across 10 resumes not justified by benefit

**Trade-offs**: Acknowledged imperfection in LaTeX roundtrip, but semantic correctness (validated by 100% YAML roundtrip) is the critical requirement. Established that cosmetic differences in LaTeX output are acceptable when semantic structure is preserved.

---
