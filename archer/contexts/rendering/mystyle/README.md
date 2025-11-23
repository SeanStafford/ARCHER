# ARCHER LaTeX Style System

This directory contains the modular LaTeX style files that define ARCHER's resume formatting.

## Files

### Style Files (.sty)

- **`packages.sty`** - Core LaTeX package imports (fonts, graphics, formatting)
- **`colors.sty`** - Brand color definitions for easy configuration of color schemes
- **`gencommands.sty`** - General-purpose commands and metadata
- **`pagestyles.sty`** - Header/footer configuration with professional profile
- **`tables.sty`** - Custom list environments (`itemizeAcademic`, `itemizeLL`, etc.)
- **`panels.sty`** - Text block positioning utilities
- **`symbols.sty`** - Icon/symbol definitions (FontAwesome integration)
- **`defaultspacing.sty`** - Default spacing parameters

### Assets

- **`Fonts/`** - Custom font files (e.g., `ringbearer.ttf` for decorative elements)

### Dependencies

- **`dependencies.txt`** - Required TeX Live packages for compilation (Debian/Ubuntu package names only)

## Installation

### System Dependencies

Install required LaTeX packages:

```bash
# Ubuntu/Debian - Install all dependencies at once
sudo apt-get install $(grep -v '^#' dependencies.txt | xargs)
```

### Verify Installation

Check that your LaTeX compiler can find the required packages:

```bash
xelatex --version
# pdflatex --version  # If using pdflatex
kpsewhich ebgaramond.sty  # Should return a path if installed correctly
```

## Usage

These style files are loaded by resume `.tex` files using `\input` directives:

```latex
\documentclass[11pt,letterpaper]{article}

% Load ARCHER style system
\input{mystyle/packages.sty}
\input{mystyle/colors.sty}
\input{mystyle/gencommands.sty}
\input{mystyle/pagestyles.sty}
\input{mystyle/tables.sty}
\input{mystyle/symbols.sty}
\input{mystyle/panels.sty}
\input{mystyle/defaultspacing.sty}

% Rest of document...
```

## Customization

Individual resumes customize appearance through:

1. **Branding variables** (colors, professional profile, job title)
2. **Spacing adjustments** (for content density)
3. **Content** (sections, experience, projects)

All structural styling remains in these `.sty` files and should not be modified per-resume.

## Font Notes

**EB Garamond** (`ebgaramond.sty`):
- Professional serif font used for body text
- Provided by `texlive-fonts-extra` package
- Alternative: Comment out line 11 in `packages.sty` to use default LaTeX fonts

---

## Questions or Additions?

If this document does not provide sufficient information, read the actual file(s) and update this document to be more useful for the next time it is referenced. 