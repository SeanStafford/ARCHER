# ARCHER
```
  ⇗⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇒⇘
 ⇑                                                                           ⇓
 ⇑                                           /@                              ⇓
 ⇑                                          / @@                             ⇓
 ⇑                                         /   @@@                           ⇓
 ⇑                                        /      @@@                         ⇓
 ⇑                  ^                    /          @@@@                     ⇓
 ⇑                  x                   /              @@@                   ⇓
 ⇑                  xx                 /                  @@                 ⇓
 ⇑                 xxxx               /                     @@               ⇓
 ⇑                   xx              /                       @@              ⇓
 ⇑                     x ++++++++   /                         @@             ⇓
 ⇑                     +\        + /                           @@            ⇓
 ⇑                    +  \        /                             @@           ⇓
 ⇑                   %%%%%%%%%%%%/%%                             @@          ⇓
 ⇑                 ++++++++\++++/++++++                          @@          ⇓
 ⇑                 ¯-\         /  ¡--¯                           @@@         ⇓
 ⇑    ``'""';         \       /   ¦                               @@@        ⇓
 ⇑   -       `''''--___|     /_==≡                                 @@   ▓    ⇓
 ⇑   -           %     ¯¯¯¯--¯   **■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■@@@■■▓▓   ⇓
 ⇑   -      ,..  %               ** '''''''                         @@@ ▓    ⇓
 ⇑   -,,,    ',:..%--¯¯¯¯¯¯¯¯¯¯_=* #       ''""'"'''--__     _-¯¯==≡}@       ⇓
 ⇑     :,,     ''`           \ #  #                 %    ¯¯¯¯¯    {≡==       ⇓
 ⇑       ,,,                  \  #                   %     __-_  _{==        ⇓
 ⇑          :,,             #  \                 ......¯¯¯¯    ¯¯@@@         ⇓
 ⇑            ,,           #  # \            ......''''          @@          ⇓
 ⇑             -         #  #    \      .:'''''''''              @@          ⇓
 ⇑              -       #  #      \     -                       @@           ⇓
 ⇑              -     #  #         \   --                      @@            ⇓
 ⇑              -    #  #           \  -                      @@             ⇓
 ⇑              -, #  #              \--                     @@              ⇓
 ⇑               -#  #                \-                    @@               ⇓
 ⇑               - #                 --\                   @@                ⇓
 ⇑                -                  -- \                @@@                 ⇓
 ⇑               ,░░░░░░░░░░░░░░░░░░░░-  \            @@@@                   ⇓
 ⇑              ,,,,,,,,,,,,,,,,,,,,,,,-  \        @@@                       ⇓
 ⇑                                         \     @@@                         ⇓
 ⇑                                          \   @@                           ⇓
 ⇑                                           \ @@                            ⇓
 ⇑                                            \@                             ⇓
 ⇑                                                                           ⇓
 ⇑                                                                           ⇓
 ⇑         ><        <<<<<<<        ><<   <<     ><  <<<<<<<<  <<<<<<<       ⇓
 ⇑        >< <<      <<    ><<   ><<   >< <<     ><  <<        <<    ><<     ⇓
 ⇑       ><  ><<     <<    ><<  ><<       <<     ><  <<        <<    ><<     ⇓
 ⇑      ><<   ><<    < ><<      ><<       <<<<<< ><  <<<<<<    < ><<         ⇓
 ⇑     ><<<<<< ><<   <<  ><<    ><<       <<     ><  <<        <<  ><<       ⇓
 ⇑    ><<       ><<  <<    ><<   ><<   >< <<     ><  <<        <<    ><<     ⇓
 ⇑   ><<         ><< <<      ><<   ><<<<  <<     ><  <<<<<<<<  <<      ><    ⇓
 ⇑                                                                           ⇓
 ⇑                                                                           ⇓
 ⇑   »-------►   »-------►   »-------►   »-------►   »-------►   »-------►   ⇓
 ⇑                                                                           ⇓
 ⇑    Algorithmic Resume Composition                                         ⇓
 ⇑    to Hasten Employer Recognition                               v0.1.0    ⇓
 ⇑                                               created by Sean Stafford    ⇓
 ⇑                                                                           ⇓
  ⇖⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇐⇙
```

**Algorithmic Resume Composition to Hasten Employer Recognition**

A resume generation system that consumes job listings and generates *targeted* resumes using LaTeX typesetting.

## Overview

ARCHER automates the tedious process of tailoring resumes to specific job postings by:
- **Analyzing** job descriptions to extract requirements and key skills
- **Targeting** relevant content from a library of ~60 historical resumes
- **Generating** professionally typeset LaTeX documents
- **Rendering** publication-quality PDFs with consistent branding


## Architecture

ARCHER's architecture is inspired by **Domain-Driven Design** with four bounded contexts, each with isolated responsibilities:

### 1. Intake Context
**Responsibility**: Job description ingestion and parsing
- Accepts job descriptions
- Normalizes job information into internal representation

**Owns**: Job description parsing logic
**Never**: Makes targeting decisions or modifies templates

### 2. Targeting Context
**Responsibility**: Algorithmic content prioritization
- Evaluates relevance of experience, projects, and skills against job requirements
- Determines which content to include from archive of existing manually created resumes
- Indexes and searches historical resume content in structured format

**Owns**: Prioritization algorithms, relevance scoring, content selection logic, historical resume analysis
**Never**: Directly accesses job descriptions or raw LaTeX files

### 3. Templating Context
**Responsibility**: Resume structure and LaTeX template management
- **Bidirectional conversion** between LaTeX (.tex) and structured YAML
- Template-based LaTeX generation using Jinja2
- Config-driven parsing with operation-based system
- Manages ~10 content types with individual templates and parse configs
- ResumeDocument class for semantic access to resume content

**Owns**: LaTeX↔YAML conversion, template system, resume structure representation
**Never**: Makes content prioritization decisions

### 4. Rendering Context
**Responsibility**: PDF compilation and output management
- Compiles LaTeX to PDF using `pdflatex`
- Validates compilation success
- Manages output files and directory structure

**Owns**: LaTeX compilation, PDF generation, output management
**Never**: Modifies template content

### Context Communication

Contexts communicate through well-defined APIs with explicit data structures:

```
Intake → (normalized job) → Targeting → (content selections) → Templating → (.tex file) → Rendering → (PDF)
```


---

## Installation

### Prerequisites

- Python 3.9+
- LaTeX distribution (TeX Live, MiKTeX, or MacTeX)
- Make (for using Makefile commands)

#### Installing LaTeX

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install texlive-latex-base texlive-fonts-recommended texlive-latex-extra
```

**macOS (using Homebrew):**
```bash
brew install --cask mactex-no-gui
# or for minimal install:
brew install basictex
```

**Windows:**
Download and install MiKTeX from https://miktex.org/download

**Verify installation:**
```bash
pdflatex --version
```

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd ARCHER

# Create virtual environment
make venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
make install

# For development (includes pytest, ruff)
make install-dev

# Configure environment (optional)
cp .env.example .env
# Edit .env to customize paths if needed
```

#### Verifying System Dependencies

ARCHER automatically checks all system dependencies (LaTeX, SQLite, etc.) across all of the archer module:
```bash
make check-deps
```

---

## LaTeX Template System

ARCHER's resume styling is implemented through a modular LaTeX package system in `archer/contexts/rendering/mystyle/`:

- **`packages.sty`** - Core LaTeX package imports
- **`gencommands.sty`** - General-purpose commands and metadata
- **`pagestyles.sty`** - Header/footer configuration with professional profile
- **`tables.sty`** - Custom list environments 



---

## Historical Resume Archive

ARCHER leverages manually-created resumes as a content library. These are processed and stored in `data/resume_archive/structured/` as YAML files:

**Purpose**:
- **Content extraction source** - Experience bullets, project descriptions, skill lists
- **Pattern recognition** - Which sections/content work for different job types
- **Customization examples** - Variation in branding, spacing, section selection
- **Quality reference** - Well-crafted quantified achievements


When generating a new resume, ARCHER analyzes relevant historical resumes to:
1. Identify which content is most relevant to the target job
2. Learn which section combinations work for that job type
3. Extract and adapt proven bullet points and project descriptions
4. Match branding/color choices to similar company types

---

## Project Structure

```
ARCHER/
├── archer/
│   ├── contexts/
│   │   ├── intake/         # Job description parsing
│   │   ├── targeting/      # Content prioritization
│   │   │   └── historical/ # Analysis of previous resumes
│   │   ├── templating/     # LaTeX ↔ YAML conversion (complete)
│   │   └── rendering/      # PDF compilation
│   │       └── mystyle/    # LaTeX style files
│   └── utils/              # Shared utilities
├── data/
│   └── resume_archive/     # Normalized LaTeX resumes
│       ├── raw/            # Raw LaTeX resumes
│       ├── structured/     # YAML resumes
│       └── fixtures/       # Test fixtures
├── docs/                   # Design documentation
├── scripts/                # CLI utilities
├── tests/                  # Test suite
├── outs/
│   ├── results/            # Final generated resumes
│   └── logs/               # Script execution logs
└── pyproject.toml          # Package configuration
```

---

## Resume Registry

ARCHER maintains a master registry (`outs/logs/resume_registry.csv`) tracking all resumes and their pipeline status. This CSV serves as the authoritative source for resume names and enables cross-context status tracking.

---

## Development

### Useful Commands

```bash
# View all available commands
make help

# Format code before committing
make format

# Check code quality
make lint

# Clean cache files and LaTeX artifacts
make clean
```

### Testing

ARCHER uses pytest with several test categories marked for different use cases.

**Run tests:**
```bash
# Run all tests (excludes slow tests by default)
make test

# Run all tests including slow tests
make test-all

# Run only unit tests (fast, mocked)
make test-unit

# Run only integration tests
make test-integration

# Run tests with coverage report
make test-cov

# Open coverage report in browser
make test-cov-html
```

**Test markers** (configured in `pyproject.toml`):
- `@pytest.mark.unit` - Fast unit tests with mocked dependencies
- `@pytest.mark.integration` - Integration tests (may involve LaTeX compilation)
- `@pytest.mark.slow` - Tests taking >1 second (excluded by default)
- `@pytest.mark.latex` - Tests requiring LaTeX compiler

**Run specific test types manually:**
```bash
pytest -m unit                    # Only unit tests
pytest -m integration             # Only integration tests
pytest -m latex                   # Only LaTeX-dependent tests
pytest tests/integration/test_two_page.py  # Specific test file
```

**Configuration**: Test settings are defined in `pyproject.toml` under `[tool.pytest.ini_options]`. By default, tests run with verbose output, short tracebacks, and slow tests excluded.

---

## Current Progress

**Completed**:
- ✅ Bidirectional LaTeX ↔ YAML conversion system
- ✅ Template-based LaTeX generation with Jinja2
- ✅ Config-driven parsing with 11 content types
- ✅ ResumeDocument API for semantic resume access
- ✅ 100% YAML roundtrip fidelity
- ✅ 98% LaTeX roundtrip fidelity

**In Progress**:
- Rendering context integration with templating
- Resume pattern analysis tools

**Planned**:
- Job description parser (Intake context)
- Content relevance scoring (Targeting context)
- Automated section selection based on job type
- Full pipeline integration (Intake → Targeting → Templating → Rendering)
- LLM integration for job description analysis
