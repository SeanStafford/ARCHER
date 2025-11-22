# ARCHER Directory Structure

**Authoritative reference for ARCHER's directory organization.**

This document explains the purpose and structure of all major directories in the ARCHER project.

---

## Project Root

```
ARCHER/
├── .archive/              # Read-only historical reference (LaTeX compilation only)
├── archer/                # Python package (all source code)
├── data/                  # Working data (resumes, jobs, figures)
├── docs/                  # Documentation
├── notebooks/             # Jupyter notebooks for analysis
├── outs/                  # Generated outputs (PDFs, logs)
├── scripts/               # CLI utilities
├── tests/                 # Test suite
├── .env                   # Environment variables (not in git)
├── .env.example           # Template for environment setup
├── Makefile               # Build automation
├── pyproject.toml         # Python package configuration
├── README.md              # Project overview
└── TODO.md                # Development roadmap
```

---

## Data Directory (`data/`)

All working data organized by type.

```
data/
├── jobs/                  # Job descriptions
├── resumes/               # Active resumes by type
│   ├── experimental/      # Manually crafted with ARCHER tools
│   ├── generated/         # Full pipeline outputs (future)
│   ├── historical/        # Archive resumes (future migration)
│   └── test/              # Development/validation resumes (also future migration)
├── resume_archive/        # Legacy structure (being phased out)
└── figs/                  # Figure assets (logos, diagrams)
```

---

### Job Descriptions (`data/jobs/`)

**Purpose**: Store job descriptions for resume targeting.

- See `docs/NORMALIZED_JOB.md` for more information about what goes in here.

---

### Resumes by Type (`data/resumes/`)

Resumes organized by how they were created (matching registry `resume_type` field).

#### Directory Structure Pattern

Each resume type directory follows the same structure:

```
{type}/
├── structured/            # YAML format (structured data)
│   └── Res202511_MLEng.yaml
├── raw/                   # LaTeX format (necessary for historical resumes, potentially useless for generated resumes)
│   └── Res202511_MLEng.tex
└── compiled/              # pdfs reside here until validation and approval, after which they move to `outs/results/`
    └── Res202511_MLEng.pdf
```

See `docs/RESUME_STATUS_REFERENCE.md` for details for each type.

---

### Legacy Resume Archive (`data/resume_archive/`)

**Status**: Being phased out in favor of type-based organization in `data/resumes/`

**Current structure**:
```
resume_archive/
├── raw/                   # LaTeX with comments removed
├── structured/            # YAML format
├── fixtures/              # Test fixtures
└── database/              # Database metadata
```

**Migration plan**: See `TODO.md` section "Low Priority: Migrate to Type-Based Resume Directory Structure"

---

### Figures (`data/figs/`)

**Purpose**: Image assets used in resumes (logos, diagrams, etc.)

---

## Outputs Directory (`outs/`)

All generated outputs from ARCHER operations.

Example outs tree:

```
outs/
├── results/               # Final approved PDFs organized by date
│   └── 2025-11-21/
│       └── {resume_name}.pdf
└── logs/                  # Execution logs and pipeline events
    ├── resume_pipeline_events.log      # Tier 2: JSON Lines event log
    ├── resume_registry.csv             # Resume status tracking
    ├── compile_20251121_173045/        # Tier 1: Compilation logs
    │   ├── render.log
    │   └── resume.pdf  →  symlink to data/resumes/{type}/compiled/{resume_name}.pdf
    └── template_20251121_120000/
        └── template.log
```

### Results (`outs/results/`)

**Purpose**: Final approved PDFs ready for delivery (organized by date)

**Organization**: `YYYY-MM-DD/` subdirectories
- Makes it easy to find recent resumes
- Naturally archives older versions
- **Only contains validated and approved resumes** that have passed all quality checks

### Logs (`outs/logs/`)

**Purpose**: Logging system for execution tracking and debugging. See `docs/LOGGING_ARCHITECTURE.md` for details.

**Detailed In-Context Logs with Loguru**: `{phase}_TIMESTAMP/`
- Directory names reflect the pipeline phase (e.g., `compile_`, `template_`)
- Log files named after context (e.g., `render.log`, `template.log`)
- Human-readable loguru logs
- Provenance tracking (script, command, environment)
- Full execution traces for debugging

**Pipeline Events**: `resume_pipeline_events.log`
- JSON Lines format
- Resume state transitions
- Cross-context coordination
- Analytics and monitoring
- See `docs/PIPELINE_EVENTS_REFERENCE.md`

**Registry**: `resume_registry.csv`
- Authoritative resume status tracking
- CSV format (resume_name, resume_type, status, date_registered, date_modified)
- All mutations automatically logged to pipeline events
- See `docs/RESUME_STATUS_REFERENCE.md`

---

## Archive Directory (`.archive/`)

**Purpose**: Read-only historical reference for manual LaTeX compilation

**Characteristics**:
- Original LaTeX files with full history
- Can still be compiled manually (`cd .archive && pdflatex Resumes/Res202507.tex`)
- Permissions set to `r-xr-xr-x` (read-only, not writable)
- Source of truth for historical resume content

**Contents**:
```
.archive/
├── Resumes/               # Original .tex files (read-only)
├── mystyle/               # LaTeX style files (historical reference)
└── Figs/                  # Figure assets (historical reference)
```

**ARCHER's active components use copies**:
- LaTeX styles: `.archive/mystyle/` → `archer/contexts/rendering/mystyle/`
- Figures: `.archive/Figs/` → `data/figs/`
- Resumes: `.archive/Resumes/` → `data/resume_archive/` (future: `data/resumes/historical/`)

---

## Source Code (`archer/`)

Python package with bounded contexts following Domain-Driven Design.

```
archer/
├── contexts/              # Four bounded contexts
│   ├── intake/            # Job description parsing
│   ├── targeting/         # Content selection algorithms
│   ├── templating/        # LaTeX ↔ YAML conversion
│   └── rendering/         # PDF compilation
└── utils/                 # Shared utilities
```

Each context has (or will eventually have):
- `README.md` - Context-specific architecture documentation
- `logger.py` - Context wrapper for logging with automatic prefix
- `dependencies.txt` - System dependencies (if any)

---

## Scripts (`scripts/`)

CLI utilities for common operations.

Scripts use typer for consistent CLI interface and include usage examples in docstrings. Scripts that do not use typer should be upgraded to use typer.

---

## Documentation (`docs/`)

Conatins documentation.

---
