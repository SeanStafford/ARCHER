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

A resume generation system that generates *targeted* resumes using LaTeX typesetting.

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

---

## Future Work

- Resume compilation preview workflow
- Content extraction algorithms for historical resume mining
- Automated section selection based on job type
- LLM integration for sophisticated job description analysis
