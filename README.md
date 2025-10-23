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
- Evalutates relevance of experience, projects, and skills against job requirements
- Determines which content to include from archive of existing manually created resumes

**Owns**: Prioritization algorithms, relevance scoring, content selection logic
**Never**: Directly accesses job descriptions or templates

### 3. Templating Context
**Responsibility**: LaTeX template building and population
- Manages custom LaTeX style system
- Populates templates with targeted content

**Owns**: LaTeX template system, template population, structure management
**Never**: Makes content prioritization decisions

### 4. Rendering Context
**Responsibility**: PDF compilation and output management
- Compiles LaTeX to PDF using `pdflatex`
- Validates compilation success
- Manages output files and directory structure

**Owns**: LaTeX compilation, PDF generation, output management
**Never**: Modifies template content

### Context Communication


```
Intake → Targeting → Templating → Rendering → (PDF)
```


---

## Installation

### Prerequisites

- Python 3.9+
- LaTeX distribution (TeX Live, MiKTeX, or MacTeX)
- Make (for using Makefile commands)

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

---

## LaTeX Template System

ARCHER's resume styling is implemented through a modular LaTeX package system 

- **`packages.sty`** - Core LaTeX package imports
- **`gencommands.sty`** - General-purpose commands and metadata
- **`pagestyles.sty`** - Header/footer configuration with professional profile
- **`tables.sty`** - Custom list environments 

### Design Philosophy

All styling is centralized in `.sty` files. 
### Custom LaTeX Environments

Resume content is structured using custom environments (defined in `tables.sty`):

**Experience Entries**:
- `\begin{itemizeAcademic}{Company}{Title}{Location}{Dates}` - Job position header
- `\itemi` - Top-level achievement bullet
- `\itemii` - Second-level bullet within projects


---

## Historical Resume Archive

ARCHER leverages manually-created production resumes as a content library. After cleaning, these are processed and stored in `data/resume_archive/`:

**Purpose**:
- **Content extraction source** - Experience bullets, project descriptions, skill lists
- **Pattern recognition** - Which sections/content work for different job types
- **Customization examples** - Variation in branding, spacing, section selection
- **Quality reference** - Well-crafted quantified achievements

**Naming convention**: `ResYYYYMM_Position_Company.tex`

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
│   │   ├── templating/     # LaTeX template management
│   │   └── rendering/      # PDF compilation
│   └── utils/              # Shared utilities (latex_cleaner, etc.)
├── data/                   
│   └── resume_archive/     # Cleaned, processed resume content
├── scripts/                # Python CLI utilities
├── outs/
│   └── resumes/            # Generated resumes
└── pyproject.toml          # Project setup and config
```

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

## Future Work

- Resume compilation preview workflow
- Content extraction algorithms for historical resume mining
- Automated section selection based on job type
- LLM integration for sophisticated job description analysis
