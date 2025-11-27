# Layout Diagnostics Reference

PDF layout validation for resume overflow detection.

## Purpose

`layout_diagnostics.py` compares a rendered PDF against the expected structure from a YAML resume to detect layout issues:
- **Page overflow**: Content flowing from one page to the next
- **Cascade effects**: When overflow on page N shifts all content on pages N+1, N+2, etc.
- **Missing sections**: Section header/content not found where expected

## Key Concepts

### Character Stream

A "character stream" is normalized text with all formatting removed:
- Lowercase only
- Alphanumeric characters only (no spaces, punctuation, or symbols)
- Line boundaries dissolved

Example: `"Machine Learning | PyTorch"` → `"machinelearningpytorch"`

This allows fuzzy matching that's robust to line wrapping differences between YAML and PDF.

### Page Terminology

- **`intended_page`**: Where content was meant to be (from YAML structure)
- **`expected_page`**: Computed page accounting for cascade from previous overflow
- **`actual_page`**: Where content was actually found in the PDF

Example: If page 1's main column overflows by 1 page:
- Page 2 content has `intended_page=2` but `expected_page=3`
- If found on page 3, `actual_page=3` and no additional overflow
- If found on page 4, there's additional overflow on page 2

### Cascade Effect

ARCHER's LaTeX uses `\switchcolumn` at each page boundary to synchronize columns. When one column overflows, ALL columns shift together. This simplifies tracking:

```
Page 1 overflow detected → All page 2 content expected on page 3
Page 2 overflow detected → All page 3 content expected on page 5
```

### Column-Level Overflow

Overflow is a **column** issue, not a section issue. If the "Experience" section overflows, the fix could be:
- Reduce "Experience" bullets
- Reduce "Projects" bullets (same column)
- Adjust any other section in that column

The diagnostics track overflow at the column level for this reason.

## Hierarchical Structure

```
DocumentDiagnostics
├── actual_page_count / intended_page_count
└── components: List[PageDiagnostics]
    └── components: List[ColumnDiagnostics]
        ├── overflow_amount
        └── components: List[SectionDiagnostics]
            ├── beginning_found / end_found
            └── intended_page / expected_page / actual_page
```

Each level:
- Derives issues from field values via `get_issues()`
- Aggregates child issues via `get_inherited_issues()`
- Reports validity via `is_valid` property

## API Usage

### Basic Validation

```python
from archer.contexts.rendering.layout_diagnostics import analyze_layout

diagnostics = analyze_layout(
    yaml_path="data/resume_archive/structured/Res202511_Role_Company.yaml",
    pdf_path="data/resumes/compiled/Res202511_Role_Company.pdf"
)

if diagnostics.is_valid:
    print("Layout OK")
else:
    for issue in diagnostics.get_inherited_issues():
        print(f"  - {issue}")
```

### Inspecting the Hierarchy

```python
# Document-level
print(f"Pages: {diagnostics.actual_page_count} (expected {diagnostics.intended_page_count})")

# Page by page
for page_diag in diagnostics.components:
    print(f"\nPage {page_diag.intended_page_number}:")

    # Column by column
    for col_diag in page_diag.components:
        if col_diag.overflow_amount > 0:
            print(f"  {col_diag.region_name}: overflowed by {col_diag.overflow_amount} page(s)")

        # Section by section
        for sec_diag in col_diag.components:
            status = "✓" if sec_diag.beginning_found and sec_diag.end_found else "✗"
            print(f"    [{status}] {sec_diag.section_name}")
```

## Issue Types

### Document-Level

| Issue | Meaning |
|-------|---------|
| `Page count mismatch: {actual} (expected {intended})` | PDF has different page count than YAML structure |

### Column-Level

| Issue | Meaning |
|-------|---------|
| `'{region}' on page {page} overflowed by {amount} page(s)` | Column content extends to subsequent pages |
| `'{region}' on page {page} has content below bottom margin` | Content too close to page bottom (stub - not yet implemented) |

### Section-Level

| Issue | Meaning |
|-------|---------|
| `'{section}' ({region}): expected page does not exist in PDF` | Cascade pushed section beyond PDF pages |
| `'{section}' ({region}): beginning not found (intended page {N}, checked through page {M})` | Section header or content prefix not found |
| `'{section}' ({region}): end not found (checked pages {N} through {M})` | Section beginning found but end missing |

## Detection Algorithm

### Finding Section Beginning

Two conditions must both be met:
1. Section header found as whole line (normalized exact match)
2. First 30 characters of section content found in column stream

### Finding Section End

After beginning is found:
1. Search for last 30 characters of section content
2. If not found on current page, extend search to subsequent pages
3. Track how many pages were needed (overflow amount)

### Handling Section Bumps

When a previous section overflows, subsequent sections may be "bumped" to the next page entirely. The algorithm:
1. Search expected page first
2. If not found, check next page
3. If found on next page, update offset for remaining sections


## Dependencies

- **`PDFDocument`**: Provides `get_lines()`, `get_character_stream()` from PDF
- **`ResumeDocument`**: Provides `sections`, `page_count`, `left_column_ratio` from YAML

## PDFDocument

`PDFDocument` (`archer/utils/pdf_processing.py`) provides column-aware text extraction from PDFs.

### Column-Based Extraction

Characters are binned into columns based on x-coordinate position. For example, with `column_splits=[0.3]`:
- Column 0 (left): characters with x < 30% of page width
- Column 1 (main): characters with x ≥ 30% of page width

Layout diagnostics gets the split ratio from `ResumeDocument.left_column_ratio` (parsed from the resume's `\setlength{\leftbarwidth}` value) and passes it to `PDFDocument`.

### Font Filtering

PDFs contain characters from multiple fonts including icons (FontAwesome) and math symbols (CMSY10). Layout diagnostics filters to text fonts only (`["Times", "Arial", "Garamond", "LMMono", ...]`) to avoid matching decorative elements.

### Line Reconstruction

Characters are clustered into lines by y-coordinate proximity (default tolerance: 3pt). This handles baseline shifts between bold and regular text that would otherwise split a single visual line into multiple extracted lines.

### Key Methods

- `get_lines(page, column)`: Raw text lines for a page/column
- `get_character_stream(page, column)`: Normalized stream (lowercase alphanumeric only)
- `get_multipage_character_stream(start, end, column)`: Stream spanning multiple pages

## ResumeDocument

`ResumeDocument` (`archer/contexts/templating/resume_data_structure.py`) provides the expected structure from YAML.

Layout diagnostics uses:
- `sections`: List of `ResumeSection` objects, each with `name`, `page_number`, `region`, and `text`
- `page_count`: Expected number of pages (derived from max section page number)
- `left_column_ratio`: Column split point for PDF extraction (e.g., 0.275)

Section `text` is normalized to a character stream and compared against PDF content to detect whether sections appear where expected.

See `docs/RESUME_DOCUMENT_CLASS.md` for full API documentation.

## Known Limitations

### Horizontal Overflow

When text overflows horizontally past the column boundary (overfull hbox), those characters are extracted into the wrong column. This causes false "section not found" errors.

**Detection**: Requires parsing LaTeX `.log` file for overfull box warnings. See TODO.md section 2 for planned feedback loop architecture.

**Workaround**: When diagnostics show missing sections without clear page overflow, the root cause is likely horizontal overflow.

### Professional Profile

The professional profile spans the full page width, but `PDFDocument` extracts by column. Full-width content gets split and character stream matching fails.

**Status**: Stub field exists (`professional_profile_found`) but validation not implemented.

### Bottom Margin

Detecting content too close to the page bottom requires y-coordinate tracking, which `PDFDocument` currently discards after line clustering.

**Status**: Stub field exists (`content_below_margin`) but validation not implemented.



## See Also

- `archer/contexts/rendering/TODO.md` - Future enhancements (overfull box analysis, margin checking)
- `docs/RESUME_DOCUMENT_CLASS.md` - ResumeDocument API
- `archer/utils/pdf_processing.py` - PDFDocument implementation
