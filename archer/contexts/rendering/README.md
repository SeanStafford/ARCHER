# Rendering Context

The Rendering context handles **LaTeX compilation** and PDF generation for resume documents. It provides both a pure compilation function and an orchestration wrapper with comprehensive logging and output management.


---

## Quick Overview

```python
from archer.contexts.rendering import compile_resume
from pathlib import Path

# High-level: Compile with registry tracking and logging
result = compile_resume(
    tex_file=Path("data/resume_archive/Res202506.tex")
)

if result.success:
    print(f"PDF generated: {result.pdf_path}")
else:
    print(f"Compilation failed: {result.errors}")
```

---

## Architecture

**`compile_latex()` - Pure Compilation**
- Low-level LaTeX compilation function
- No registry integration, no logging
- Strict preconditions (assertions)
- Used by: `compile_resume()`, tests, standalone scripts
- Returns: `CompilationResult`

**`compile_resume()` - Orchestration**
- High-level wrapper for ARCHER resume compilation
- Integrates registry tracking (Tier 2 logging)
- Detailed loguru logging (Tier 1 logging)
- Organized output management (results/ + logs/)
- Success-based artifact cleanup
- Used by: Production resume generation, main pipeline

**Design rationale:** Separation of concerns - pure compilation logic vs. ARCHER-specific orchestration.

---

## Two-Tier Logging

### Tier 1: Detailed In-Context Logging with Loguru

**Purpose:** Comprehensive execution traces for debugging and auditing

**Implementation:**
- Logs to `outs/logs/render_TIMESTAMP/render.log`
- All rendering logs prefixed with `[render]` for multi-context clarity.

### Tier 2: Pipeline Event Logging

**Purpose:** Status tracking

**Implementation:** JSON Lines format via `update_resume_status()`

**Events logged:**
- `compiling` (compilation start)
- `compiling_completed` (compilation success)
- `compiling_failed` (compilation failure with error details)
- `validating` (validation start)
- `validating_completed` (validation success with page count)
- `validating_failed` (validation failure with quality issues)

---

## Output Organization

### Success Path

When compilation succeeds:

```
outs/
├── results/2025-11-14/
│   └── Res202506.pdf                ← Final PDF (dated)
└── logs/render_20251114_210621/
    ├── render.log                   ← Minimal log
    └── Res202506.pdf                → Symlink to results/
```

**Actions:**
1. PDF moved to **dated results directory** (`outs/results/YYYY-MM-DD/`)
2. Symlink created in log directory for easy navigation
3. **All LaTeX artifacts deleted** (.aux, .log, .out, .toc)
4. Minimal `render.log` kept for audit trail

**Result:** Clean outputs, easy to find PDFs by date

### Failure Path

When compilation fails:

```
outs/logs/render_20251114_210621/
├── render.log                      ← Detailed log with full stdout/stderr
├── Res202506.aux
├── Res202506.log                   ← pdflatex log for debugging
├── Res202506.out
└── Res202506.toc
```

**Actions:**
1. **All artifacts preserved** for debugging
2. Full pdflatex stdout/stderr logged to `render.log`
3. No PDF in results/ (compilation failed)

**Result:** Complete debugging context available

**Design rationale:** Success needs minimal logging. Failure needs maximum detail.

---

## LaTeX Style System (mystyle/)

The rendering context owns the LaTeX style files that define resume formatting.

**Location:** `archer/contexts/rendering/mystyle/`

**Contents:**
- **`packages.sty`** - Core LaTeX package imports
- **`colors.sty`** - Brand color definitions
- **`gencommands.sty`** - General commands and metadata
- **`pagestyles.sty`** - Header/footer with professional profile
- **`tables.sty`** - Custom environments (itemizeAcademic, itemizeAProject, etc.)
- **`panels.sty`** - Text block positioning
- **`symbols.sty`** - FontAwesome icons
- **`defaultspacing.sty`** - Default spacing values
- **`Fonts/`** - Custom font files

**Integration:** pdflatex finds `mystyle/` via `TEXINPUTS` environment variable (set in `.env`).

LaTeX files reference styles as:
```latex
\input{mystyle/packages.sty}
\input{mystyle/colors.sty}
```

---

## Dependencies

### System Dependencies

The rendering context requires a **LaTeX distribution** installed system-wide. This cannot be installed via pip - it must be installed using your OS package manager.

System dependencies are declared in `dependencies.txt` files for transparency and discoverability. This setup allows automated dependency checker with the `check_dependencies.sh` script that recursively checks all `dependencies.txt` files in a given directory. The easier way to use is this to run the `make check-deps` command which reports all system dependencies for ARCHER and their status (installed vs missing).

### Verify Installation

```bash
pdflatex --version
```

---

## Usage Examples

### Basic Compilation (Production)

```python
from archer.contexts.rendering import compile_resume
from pathlib import Path

result = compile_resume(
    tex_file=Path("data/resume_archive/Res202506.tex")
)

if result.success:
    print(f"✓ PDF: {result.pdf_path}")
    print(f"  Warnings: {len(result.warnings)}")
else:
    print(f"✗ Compilation failed")
    for error in result.errors:
        print(f"  - {error}")
```

### Custom Output Directory

```python
result = compile_resume(
    tex_file=Path("resume.tex"),
    output_dir=Path("custom/output/dir")
)
```

### Low-Level Compilation (No Tracking)

```python
from archer.contexts.rendering.compiler import compile_latex

result = compile_latex(
    tex_file=Path("test.tex"),
    compile_dir=Path("tmp"),
    num_passes=1,
    keep_artifacts=True  # Keep .aux, .log for inspection
)
```

### Accessing Compilation Details

```python
result = compile_resume(tex_file)

print(f"Success: {result.success}")
print(f"PDF: {result.pdf_path}")
print(f"Errors: {len(result.errors)}")
print(f"Warnings: {len(result.warnings)}")

# First 5 errors
for error in result.errors[:5]:
    print(f"  {error}")

# Full pdflatex output (for debugging)
print(result.stdout)
print(result.stderr)
```

---

## Error Detection

The compiler parses LaTeX logs for multiple error patterns:

### Standard errors

```
! LaTeX Error: File `ebgaramond.sty' not found.
! Undefined control sequence.
! Missing $ inserted.
```

### Non-standard errors

```
Undefined control sequence
File ended while scanning use of \textbf
Emergency stop
```

### Failure conditions

1. pdflatex returns non-zero exit code
2. No PDF generated
3. LaTeX errors in log

### Success conditions 

Warnings are common -- especially overfull/underfull boxes. Success/failure detection ignores warnings.

Success = PDF generated + no errors + pdflatex non-zero


## Future Enhancements

Potential improvements (not yet implemented):

1. **PDF validation**
   - Page count verification (enforce 2-page limit)
   - Content verification (extract text, check for expected sections)
   - Visual comparison (diff against reference PDFs)

2. **Performance optimization**
   - Parallel compilation for batch operations
   - Incremental compilation (reuse .aux files)
   - Caching of unchanged resumes

3. **Advanced diagnostics**
   - Overfull/underfull box analysis with line numbers
   - Font warning detection
   - Package conflict resolution

4. **Retry logic**
   - Automatic retry on transient failures
   - Fallback to single-pass compilation

