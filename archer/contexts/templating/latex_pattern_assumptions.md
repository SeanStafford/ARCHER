# LaTeX Pattern Assumptions

This document describes the LaTeX patterns ARCHER expects when parsing resumes, why they work, and under what conditions they might break. All patterns are defined in `archer/contexts/templating/latex_patterns.py`.

**Key Principle:** ARCHER's parser relies on **consistent formatting patterns** found across all historical resumes. These patterns are not universal LaTeX conventions but rather **project-specific conventions** maintained across ~60 historical resumes.

---

## DocumentPatterns

### `\begin{document}` and `\end{document}`

**What:** Standard LaTeX document boundary markers.

**When Used:** Every complete resume has exactly one `\begin{document}` and one `\end{document}` marking the document body boundaries.

**Why It Works:** These are required LaTeX commands for any compilable document. They are completely standardized and will never vary.

**Breaking Conditions:**
- None. These patterns are fundamental to LaTeX and cannot break.
- Parser expects exactly one of each. Multiple `\begin{document}` blocks would break.

**Design Decision:** We extract everything between these markers as the "document content" and parse the preamble separately. This allows clean separation of metadata (preamble) from content (body).

### `\clearpage`

**What:** LaTeX command that flushes all pending floats and starts a new page.

**When Used:** Placed between pages **inside the paracol environment** to force page breaks.

**Why It Works:** All historical resumes use `\clearpage` consistently to separate pages. It appears exactly (number of pages - 1) times in each resume.

**Breaking Conditions:**
- If `\clearpage` appears outside paracol (e.g., to clear floats in preamble), page detection could miscount.
- If someone uses `\newpage` or `\pagebreak` instead, parser won't detect the page boundary.
- If `\clearpage` appears in section titles or comments, parser would treat it as a page break.

**Design Decision:** We split on `\clearpage` to detect pages. This pattern-matching approach works because:
1. Historical resumes consistently use `\clearpage` for page breaks
2. `\clearpage` never appears in content (section names, bullet text)
3. Resumes don't use floats that would require `\clearpage` for clearing

**Limitation:** This approach is **project-specific**. General LaTeX documents might use `\clearpage` differently.

---

## PagePatterns

### `\begin{paracol}{2}` and `\end{paracol}`

**What:** Two-column parallel environment that enables left sidebar and main content columns.

**When Used:** **Single paracol environment wraps all pages** in every resume. Never nested, never multiple blocks.

**Why It Works:** The paracol pattern is universal across all historical resumes:
```latex
\begin{paracol}{2}
  % Page 1: left column with skills, main column with experience
  \section*{Skills}
  ...
  \switchcolumn
  \section*{Experience}
  ...
  \clearpage
  % Page 2: continuation (no left column)
  \section*{More Experience}
  ...
\end{paracol}
```

**Breaking Conditions:**
- **Multiple paracol blocks** - If someone wraps each page in separate `\begin{paracol}...\end{paracol}`, parser will only extract content from the first block.
- **Nested paracol** - Paracol doesn't support nesting; this would be a LaTeX error anyway.
- **Paracol with different column count** - Parser assumes `{2}` exactly. `\begin{paracol}{3}` would still match but break layout assumptions.
- **Content outside paracol** - Anything between `\begin{document}` and `\begin{paracol}` or after `\end{paracol}` would be ignored.

**Design Decision:** Extract content between first `\begin{paracol}{2}` and last `\end{paracol}`, then split on `\clearpage`. This assumes:
- One paracol wraps everything
- All pages share the same paracol environment
- Page breaks happen inside paracol (not between paracol blocks)

**Why This Pattern:** Using a single paracol for all pages allows LaTeX to balance columns automatically and maintain consistent spacing. It's more elegant than separate paracol blocks per page.

### `\switchcolumn`

**What:** Paracol command to switch from left column to main (right) column.

**When Used:** Appears exactly **once on page 1** after all left-column content. Continuation pages (page 2+) have no `\switchcolumn` because they only have main-column content.

**Why It Works:** Consistent pattern across all resumes:
- Page 1: Left column (skills) → `\switchcolumn` → Main column (experience)
- Page 2+: Main column only (experience continuation)

Parser logic:
1. Split paracol content on `\clearpage` to get page segments
2. For each segment, check for `\switchcolumn`
3. If present: content before = left column, content after = main column
4. If absent: all content = main column (continuation page)

**Breaking Conditions:**
- **Multiple switchcolumns per page** - Parser assumes ≤1 per page. Multiple switches would cause content misattribution.
- **Switchcolumn on page 2+** - If continuation page has `\switchcolumn`, parser would incorrectly split content into left/main columns.
- **No switchcolumn on page 1** - Page 1 content would all go to main column (no left sidebar).

**Design Decision:** Use `\switchcolumn` as the delimiter between left and main columns. This matches the natural paracol usage pattern and requires no column counting or position tracking.

**Why This Pattern:** Paracol environments naturally separate columns with `\switchcolumn`. Page 1 needs both columns (sidebar + content), while continuation pages only need content column. This avoids repeating sidebar skills on every page.

---

## SectionPatterns

### `\section*{Name}`

**What:** LaTeX starred section command (unnumbered section heading).

**When Used:** Every major resume section (Skills, Experience, Education, etc.) starts with `\section*{Name}`.

**Why It Works:** Section headings are the primary structural delimiter in resumes:
- Parser finds all `\section*{...}` occurrences
- Text between consecutive sections = one section's content
- Parser infers section type from content patterns (see EnvironmentPatterns)

**Breaking Conditions:**
- **Numbered sections** - Using `\section{Name}` instead of `\section*{Name}` would not match the pattern.
- **Different heading levels** - Using `\subsection*`, `\paragraph*`, etc. would not be detected as top-level sections.
- **Section command in content** - If `\section*` appears in a bullet point or project name, it would be treated as a section boundary.
- **Nested sections** - Parser doesn't handle hierarchical sections; everything is top-level.

**Design Decision:** Split column content on `\section*{...}` boundaries. This is robust because:
1. All sections use starred sections (consistent)
2. Section names are short and controlled (no accidental `\section*` in content)
3. Resumes are flat structure (no subsections within sections)

**Why This Pattern:** Unnumbered sections (`\section*`) are standard for resumes since numbering ("1. Experience", "2. Education") looks unprofessional. The starred variant is universal across resume LaTeX.

### Type Inference Order

**Critical Principle:** When inferring section type from patterns, always check **most specific patterns first**.

**Why:** Some types share patterns (subset relationships). Education is a subset of skill_categories:
- Both have: `\begin{itemize}` + `\item[]` + `\scshape`
- Education additionally has: `"Florida State University"` or `"St. Mary's College"`

**Correct Order (most → least specific):**
1. `itemizeAcademic` - Unique environment (most specific)
2. Education - 4 checks: itemize + item[] + scshape + institution name
3. skill_categories - 3 checks: itemize + item[] + scshape
4. skill_list_caps - 3 checks: setlength + baselineskip + scshape
5. skill_list_pipes - 2 checks: texttt + pipe
6. `itemizeMain` - Unique environment
7. unknown - Fallback

**Wrong:** If skill_categories checked before education, education sections would be misidentified as skill_categories since they match the less-specific pattern.

**Implementation:** See `_parse_section_by_inference()` in `converter.py`

---

## EnvironmentPatterns

### `itemizeAcademic` - Work Experience

**What:** Custom environment for job entries defined in `tables.sty`.

**When Used:** Every work experience entry uses:
```latex
\begin{itemizeAcademic}{Company}{Title}{Location}{Dates}
    \itemi Achievement bullet
    \begin{itemizeAProject}{\large $\bullet$}{Project Name}{dates}
        \itemii Project detail
    \end{itemizeAProject}
\end{itemizeAcademic}
```

**Why It Works:** Parser extracts parameters from the `\begin{itemizeAcademic}{...}{...}{...}{...}` line and parses bullets/projects inside. This environment is **project-specific** - defined in our `tables.sty`, not standard LaTeX.

**Breaking Conditions:**
- **Different parameter order** - Parser assumes `{Company}{Title}{Location}{Dates}` order. Swapping would mis-assign fields.
- **Missing parameters** - Fewer than 4 parameters would cause extraction to fail.
- **Parameters with unbalanced braces** - Parser uses brace counting; `{Title with {nested}}` could break.
- **Using standard itemize** - Using `\begin{itemize}` instead of custom environment wouldn't provide metadata.

**Design Decision:** Custom environment encodes metadata (company, title) in the environment declaration rather than separate commands. This keeps metadata co-located with content and makes parsing deterministic.

**Why This Pattern:** Custom environments allow:
1. Semantic markup (`itemizeAcademic` vs generic `itemize`)
2. Metadata in environment signature (company, title, dates)
3. Consistent styling controlled by `tables.sty`
4. Clear structural boundaries for parser

### `itemizeAProject` and `itemizeKeyProject` - Projects

**What:** Custom environments for nested projects within work experience.

**When Used:**
```latex
\begin{itemizeAProject}{\large $\bullet$}{Project Name}{dates}
    \itemii Project achievement
\end{itemizeAProject}
```

**Why It Works:** Projects nest inside work experience. Parser detects project boundaries by `\begin{itemizeAProject}` and extracts name/dates from parameters.

**Breaking Conditions:**
- **Wrong bullet symbol** - Parser expects `{\large $\bullet$}` as first parameter. Different symbol would work but violates convention.
- **No project dates** - Parser expects 3 parameters. Missing dates would break extraction.
- **Projects outside work experience** - Parser only looks for projects within `itemizeAcademic` content.

**Design Decision:** Projects are **always nested** within work experience, never standalone. This matches real-world semantics (projects belong to jobs) and simplifies parsing (no ambiguity about project ownership).

### `itemizeLL` - Skill Categories

**What:** Custom environment for compact skill lists with line-item formatting.

**When Used:**
```latex
\item[{\faIcon}] {\scshape Category Name}
\begin{itemizeLL}
    \itemLL {Python}
    \itemLL {C++}
\end{itemizeLL}
```

**Why It Works:** Used for categorized skills (e.g., "ML Frameworks: PyTorch, TensorFlow"). Parser extracts category name from `\item[icon] {\scshape Name}` and skill items from `\itemLL {skill}` entries.

**Breaking Conditions:**
- **Missing icon** - `\item[] {\scshape Name}` would have empty icon field.
- **No scshape formatting** - `\item[icon] {Name}` wouldn't match the pattern.
- **Regular `\item` instead of `\itemLL`** - Skill items wouldn't be extracted correctly.

**Design Decision:** Skill categories use icon + small-caps header for visual distinction. Parser looks for this specific formatting pattern to identify skill categories vs other list types.

### `itemizeMain` - Personality Alias Array

**What:** Custom environment for personality/fun sections with icon-labeled items.

**When Used:**
```latex
\begin{itemizeMain}
    \item[\blackbelt] Bash Black Belt
    \item[\faUserNinja] NumPy Ninja
\end{itemizeMain}
```

**Why It Works:** Parser extracts icon and text from each `\item[icon] text` line.

**Breaking Conditions:**
- **Using standard itemize** - Standard `\begin{itemize}` would be confused with other section types.
- **Multi-line text** - Parser assumes text ends at line break. Text spanning multiple lines would only capture first line.
- **Nested environments** - `itemizeMain` doesn't support nesting; parser doesn't look for it.

**Design Decision:** Dedicated environment (`itemizeMain` vs generic `itemize`) makes type inference unambiguous. When parser sees `\begin{itemizeMain}`, it knows this is personality content, not skills or experience.

---

## MetadataPatterns

### `\renewcommand` Fields

**What:** LaTeX command to redefine macros, used throughout preamble to set document metadata.

**When Used:**
```latex
\renewcommand{\myname}{\textbf{Sean Stafford}}
\renewcommand{\mydate}{October 2025}
\renewcommand{\brand}{ML Engineer | Physicist}
\renewcommand{\emphcolor}{NetflixDark}
```

**Why It Works:** Parser extracts all `\renewcommand{\fieldname}{value}` pairs from preamble and categorizes them as either:
- Known fields (name, date, brand, professional profile)
- Color fields (emphcolor, topbarcolor, etc.)
- Generic fields (everything else stored in `fields` dict)

**Breaking Conditions:**
- **Newcommand instead of renewcommand** - `\newcommand{\myname}{...}` wouldn't be extracted (though it would fail to compile since `\myname` is predefined in `gencommands.sty`).
- **Unbalanced braces** - Parser uses brace counting for values; unbalanced braces break extraction.
- **Multi-line values** - Parser handles multi-line values with proper brace counting, but newlines in values are preserved.
- **Commands in field names** - `\renewcommand{\my\textbf{name}}{...}` would confuse parser.

**Design Decision:** All metadata goes in preamble as `\renewcommand` statements. This separates metadata from content and makes extraction straightforward (parse everything before `\begin{document}`).

**Why This Pattern:** LaTeX preamble is the standard location for document configuration. Using `\renewcommand` allows:
1. Variables can be referenced throughout document (`\myname`, `\brand`)
2. Single source of truth for metadata
3. Easy customization without touching document body
4. Clear separation: preamble = config, body = content

### `\setuphyperandmeta`

**What:** Custom command defined in `gencommands.sty` that configures PDF metadata and hyperref.

**When Used:**
```latex
\setuphyperandmeta{\myname}{\mydate}{\pdfkeywords}
```

**Why It Works:** Parser doesn't process this command's arguments (they're just variable references). It exists in the generated preamble for LaTeX compilation but isn't parsed back.

**Breaking Conditions:**
- **Missing in generated preamble** - PDF won't have correct metadata, but compilation works.
- **Different parameter order** - Purely a generation concern; parser ignores it.

**Design Decision:** Include in generated preamble for completeness (proper PDF metadata) but don't parse it. The actual values are already extracted from `\renewcommand` statements.

### `\def\nlinesPP{1}`

**What:** LaTeX primitive to define the number of lines for professional profile.

**When Used:** Only when `professional_profile` is set. Controls vertical spacing of profile text on page 1.

**Why It Works:** Parser looks for this pattern when extracting professional profile. Its presence indicates profile formatting is active.

**Breaking Conditions:**
- **Different values** - Parser doesn't validate the number; it just notes presence.
- **Using `\renewcommand`** - If someone used `\renewcommand{\nlinesPP}{1}` instead, parser might not recognize it.

**Design Decision:** Use `\def` for this one-off setting rather than creating a macro to renew. This is a LaTeX style choice rather than a parsing requirement.

---

## ColorFields

### Known Color Names

**What:** Enumeration of color fields used for resume theming (emphcolor, topbarcolor, leftbarcolor, brandcolor, namecolor).

**When Used:** These specific field names are defined in `colors.sty` and used throughout the resume for consistent theming.

**Why It Works:** Parser extracts these fields separately from generic `\renewcommand` fields and stores them in a `colors` dict. This enables:
- Easy color scheme swapping
- Validation of color names (could check against known colors)
- Targeted color customization in Targeting context

**Breaking Conditions:**
- **Additional color fields** - New colors (e.g., `\footercolor`) wouldn't be recognized unless added to `ColorFields` enum.
- **Typos in field names** - `\emphcolour` (British spelling) wouldn't match; would go to generic `fields`.
- **Color values in wrong format** - Parser doesn't validate color values. Invalid colors cause LaTeX compilation errors, not parse errors.

**Design Decision:** Hardcode the list of known color fields rather than auto-detecting any field containing "color". This ensures explicit control over what's treated as theming vs content.

**Why This Pattern:** Colors are first-class resume attributes (they define the "brand") and deserve dedicated storage separate from generic metadata. This makes color scheme management explicit and prevents confusion with non-color fields.

---

## FormattingPatterns

### Text Formatting Commands

**What:** Standard LaTeX formatting commands (`\textbf`, `\scshape`, `\texttt`, etc.) used throughout resume content.

**When Used:** Throughout bullets, titles, and metadata:
- `\textbf{text}` - Bold (achievements, metrics)
- `\scshape text` - Small caps (section headers, institutions)
- `\texttt{text}` - Monospace (skill names, tools)
- `\coloremph{text}` - Custom color emphasis (project names)

**Why It Works:** Parser handles these in two ways:
1. **During metadata extraction** - Strips formatting to get clean values (e.g., `\textbf{Sean}` → `Sean`)
2. **During content parsing** - Preserves formatting in bullets and text (e.g., `\textbf{Reduced latency}` stays as-is)

**Breaking Conditions:**
- **Nested formatting** - `\textbf{\scshape text}` is preserved as-is but might complicate further processing.
- **Custom formatting commands** - Unknown commands are preserved but not specially handled.
- **Unbalanced braces** - `\textbf{missing brace` would break brace counting in parameter extraction.

**Design Decision:**
- **Metadata**: Strip formatting (we only care about the text)
- **Content**: Preserve formatting (it carries semantic meaning: bold = important, texttt = technical term)

**Why This Pattern:** LaTeX formatting is semantic (bold means emphasis, not just visual styling). Preserving it in content allows:
1. Round-trip fidelity (LaTeX → YAML → LaTeX maintains formatting)
2. Semantic understanding (bold text = achievements/metrics)
3. Future processing (e.g., extract all `\textbf{}` content as "key achievements")

### Layout Commands (`\setlength`, `\centering`, `\par`)

**What:** LaTeX commands controlling spacing and alignment.

**When Used:**
- `\setlength{\baselineskip}{10pt}` - Line spacing in skill lists
- `\centering` - Center alignment for professional profile
- `\par` - Paragraph break in professional profile

**Why It Works:** Parser recognizes these as indicators of specific content types:
- `\setlength{\baselineskip}` + `\scshape` → skill_list_caps
- `\centering` + `\textbf` → professional profile formatting

**Breaking Conditions:**
- **Different spacing values** - Parser doesn't validate the `10pt`; pattern is `\setlength{\baselineskip}{...}`.
- **Missing spacing commands** - If skill list omits `\setlength`, type inference might fail.
- **Spacing in wrong context** - `\setlength{\baselineskip}` in a bullet would be preserved but might confuse type inference.

**Design Decision:** Use presence of layout commands as **type inference signals**. The specific values don't matter for parsing, only the pattern presence.

**Why This Pattern:** Certain content types have characteristic formatting:
- Skill lists: Custom line spacing
- Professional profile: Centered, bold
- Project names: Color emphasis

Parser uses these formatting patterns to infer content types when structure alone is ambiguous.

---

## General Assumptions

### Pattern Consistency

**Core Assumption:** All historical resumes follow the same LaTeX patterns because:
1. They were all generated from the same template system (`template_resume.tex` + `mystyle/*.sty`)
2. Manual edits preserved the structural patterns
3. Consistent style is a deliberate design choice (professional appearance, easier maintenance)

**Implication:** Parser is **project-specific**, not general-purpose. It won't parse arbitrary LaTeX resumes.

### Why Pattern Matching Works Here

**Advantages:**
1. **Speed** - Regex patterns are fast; no need for full LaTeX parsing
2. **Simplicity** - No LaTeX parser dependency, no abstract syntax tree
3. **Robustness** - Patterns are stable across 60+ resumes over multiple years
4. **Maintainability** - Patterns are explicit and documented (this file!)

**Limitations:**
1. **Fragility** - Deviating from patterns breaks parser
2. **Not general** - Can't parse resumes from other templates
3. **Manual updates** - New LaTeX patterns require parser updates
4. **No validation** - Parser assumes well-formed input

### When Patterns Would Break

**Critical Breaking Changes:**
1. **Switching to different document class** (e.g., `moderncv`) - All patterns invalid
2. **Replacing paracol with minipage/multicol** - Page detection breaks
3. **Using numbered sections** (`\section{Experience}`) - Section detection breaks
4. **Abandoning custom environments** - Type inference breaks
5. **Multiple paracol blocks per document** - Page splitting breaks

**Non-Breaking Changes:**
1. **New color schemes** - Color names change, pattern stays
2. **Different spacing values** - Numbers change, pattern stays
3. **New section types** - Add new type inference rules
4. **Content variations** - Text changes, structure stays

### Design Philosophy

**Trade-off:** Pattern matching sacrifices generality for reliability within a specific domain.

**Why This Works for ARCHER:**
1. **Controlled environment** - We control all resume generation
2. **Consistent conventions** - Historical resumes set precedent
3. **Documentation** - This file makes assumptions explicit
4. **Testing** - 35 integration tests validate patterns

**Future-Proofing:**
1. **Document patterns** (this file) - Future developers understand assumptions
2. **Test coverage** - Tests catch pattern changes
3. **Centralize patterns** (`latex_patterns.py`) - Single source of truth
4. **Validate on parse** - Raise clear errors when patterns don't match

---

## Summary

ARCHER's LaTeX parsing is **pattern-based** and **project-specific**. It works because:

1. ✅ **All resumes use consistent patterns** (single paracol, starred sections, custom environments)
2. ✅ **Patterns are documented** (this file + `latex_patterns.py`)
3. ✅ **Patterns are tested** (35 integration tests covering all types)
4. ✅ **Patterns are explicit** (no hidden assumptions, all patterns defined in one place)

It breaks when:
1. ❌ **Patterns change** (new template system, different environments)
2. ❌ **Structure changes** (multiple paracols, numbered sections)
3. ❌ **Conventions violated** (manual edits that break patterns)

**Guidance for Future Development:**
- **Adding new content types:** Define new environment or formatting pattern, add to type inference
- **Changing templates:** Update patterns in `latex_patterns.py`, update parser logic, update tests
- **Handling edge cases:** Document them here, add test coverage, make parser more lenient
- **Supporting variations:** Parameterize patterns (e.g., detect both `\clearpage` and `\newpage`)
