# Resume Structure Testing Documentation

This document explains the testing strategy for ARCHER's LaTeX ↔ YAML conversion system, detailing what each type represents, its purpose, and how tests validate correctness.

---

## Testing Philosophy

ARCHER's templating system must achieve **perfect round-trip fidelity**:
- **LaTeX → YAML → LaTeX** produces identical output (ignoring cosmetic whitespace)
- **YAML → LaTeX → YAML** produces identical structure

This ensures that:
1. Historical resume content is accurately extracted for content mining
2. Generated resumes maintain exact formatting control
3. No information is lost during conversion

---

## Type Coverage Matrix

| Type | Parser | Generator | Unit Tests | Integration Tests | Documentation |
|------|--------|-----------|------------|-------------------|---------------|
| `work_experience` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `project` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `skill_list_caps` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `skill_list_pipes` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `skill_categories` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `skill_category` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `education` | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |

Legend: ✅ Complete | 🚧 In Progress | ⏳ Planned

---

## Type 1: `work_experience`

### Purpose
Represents a job position with company, title, location, dates, achievement bullets, and optional nested projects. This is the primary content type for work history sections.

### LaTeX Structure
Uses the `itemizeAcademic` environment:
```latex
\begin{itemizeAcademic}{Company}{Title}{Location}{Dates}
    \itemi First achievement bullet...
    \itemi Second achievement bullet...

    \begin{itemizeAProject}{{\large $\bullet$}}{Project Name}{dates}
        \itemii Project-specific bullet...
    \end{itemizeAProject}
\end{itemizeAcademic}
```

### YAML Structure
```yaml
type: work_experience
metadata:
  company: Company Name
  title: Job Title
  location: City, ST
  dates: Start -- End
  subtitle: Optional subtitle (e.g., contract details)
content:
  bullets:
  - text: Achievement description...
  projects:
  - type: project
    metadata: {...}
    bullets: [...]
```

### Test Coverage

**File:** `tests/integration/test_skill_list_caps.py` (originally created for work_experience, needs dedicated file)

**Key Tests:**
1. **Metadata Extraction** - Validates all 4 required parameters (company, title, location, dates) are correctly extracted
2. **Subtitle Handling** - Tests optional subtitle field (joined with `\\` in LaTeX)
3. **Bullet Parsing** - Ensures top-level `\itemi` bullets are correctly identified and captured
4. **Nested Project Detection** - Validates projects are parsed separately from top-level bullets
5. **Round-trip Fidelity** - Confirms LaTeX → YAML → LaTeX produces identical structure

**Why These Tests Matter:**
- Work experience is the **most complex content type** with nested structure
- Subtitle handling tests optional field logic critical for contract/consulting roles
- Bullet/project separation validates the parser correctly distinguishes between `\itemi` (top-level) and nested `\begin{itemizeAProject}` blocks
- Round-trip test ensures no information loss (critical for content reuse)

---

## Type 2: `project`

### Purpose
Represents a nested project within a work experience entry. Projects have their own title, optional dates, and second-level bullets. Used to highlight major initiatives within a role.

### LaTeX Structure
Uses `itemizeAProject` or `itemizeKeyProject`:
```latex
\begin{itemizeAProject}{{\large $\bullet$}}{Project Title}{dates}
    \itemii Technical accomplishment...
    \itemii Impact metric...
\end{itemizeAProject}
```

### YAML Structure
```yaml
type: project
metadata:
  name: Project title (may include \coloremph{} formatting)
  bullet_symbol: '{\large $\bullet$}'
  dates: Optional date range
bullets:
- text: Achievement description...
```

### Test Coverage

**Tests Included in:** `work_experience` integration tests

**Key Validations:**
1. **Bullet Symbol Preservation** - Ensures custom bullet symbols (e.g., colored bullets) are maintained
2. **Name Formatting** - Validates LaTeX commands in project names (e.g., `\coloremph{}`) are preserved
3. **Second-level Bullets** - Tests `\itemii` parsing distinct from `\itemi`
4. **Empty Dates** - Confirms optional dates field handled correctly

**Why These Tests Matter:**
- Projects are **always nested** - tests validate parser handles depth correctly
- Bullet symbol preservation is critical for visual branding consistency
- Name formatting preservation ensures emphasized project titles remain emphasized
- Tests validate parser doesn't confuse `\itemii` (project bullets) with `\itemi` (top-level bullets)

---

## Type 3: `skill_list_caps`

### Purpose
Displays high-level skills in an all-caps, unbulleted vertical list. Used for "Core Skills" sections where skills are primary capabilities, not specific tools. The small-caps formatting (`\scshape`) provides visual hierarchy.

### LaTeX Structure
Inline braced block with spacing and formatting:
```latex
\section*{Core Skills}
   { \setlength{\baselineskip}{10pt} \setlength{\parskip}{7.5pt} \scshape

    Machine Learning (ML)

    High-Performance\\Computing (HPC)

    Distributed Training

    MLOps

   }
```

**Key Characteristics:**
- Braced block with spacing commands (`\setlength`)
- Small caps formatting (`\scshape`)
- Items separated by blank lines or `\par`
- Items can contain `\\` for line breaks within a skill

### YAML Structure
```yaml
type: skill_list_caps
content:
  list:
  - Machine Learning (ML)
  - High-Performance\\Computing (HPC)
  - Distributed Training
  - MLOps
```

### Test Coverage

**File:** `tests/integration/test_skill_list_caps.py`

#### Test 1: `test_yaml_to_latex_skill_list_caps()`

**Purpose:** Validate YAML → LaTeX generation

**What It Tests:**
```python
converter = YAMLToLaTeXConverter()
latex = converter.convert_skill_list_caps(yaml_dict["section"])

assert "\\setlength{\\baselineskip}" in latex
assert "\\scshape" in latex
assert "Machine Learning (ML)" in latex
assert "High-Performance\\\\Computing (HPC)" in latex
```

**Why This Matters:**
- Confirms spacing commands are correctly inserted (critical for visual consistency)
- Validates `\scshape` formatting is applied (small-caps are distinguishing feature)
- Tests content preservation including special characters (`&`, parentheses)
- Verifies line breaks (`\\`) are properly escaped (double backslash in Python strings)

#### Test 2: `test_latex_to_yaml_skill_list_caps()`

**Purpose:** Validate LaTeX → YAML parsing

**What It Tests:**
```python
converter = LaTeXToYAMLConverter()
result = converter.parse_skill_list_caps(latex_str)

assert result["type"] == "skill_list_caps"
assert len(result["content"]["list"]) == 8
assert "High-Performance\\\\Computing (HPC)" in items
```

**Why This Matters:**
- Confirms parser correctly identifies the braced block pattern
- Validates blank line splitting (8 items from 8 skill lines)
- Tests line break preservation within items (`\\` retained)
- Ensures type identification is correct (important for dispatcher logic)

#### Test 3: `test_skill_list_caps_roundtrip()`

**Purpose:** Validate full round-trip fidelity

**What It Tests:**
```python
# YAML -> LaTeX
latex = converter_to_latex.convert_skill_list_caps(original_dict["section"])

# LaTeX -> YAML
roundtrip_dict = converter_to_yaml.parse_skill_list_caps(latex)

# Compare structures
assert roundtrip_dict == original_dict["section"]
```

**Why This Matters:**
- **Critical fidelity test** - ensures no information is lost in conversion
- Validates parser and generator are exact inverses
- Tests edge cases: line breaks, special characters, ampersands all survive round-trip
- Proves content can be reliably extracted from historical resumes and regenerated exactly

**Test Data:** `data/resume_archive/structured/core_skills_test.yaml` + `core_skills_test.tex`

**Edge Cases Covered:**
- ✅ Line breaks within items (`High-Performance\\Computing`)
- ✅ Special characters (`&` in "Testing \& Eval")
- ✅ Parentheses (skill abbreviations)
- ✅ Multiple blank lines between items (normalized)

---

## Type 4: `skill_list_pipes`

### Purpose
Displays tools/languages in a compact inline format with pipe separators. Used for "Languages", "Hardware", or other categories where items are short identifiers. More space-efficient than vertical lists and emphasizes that items are tools/code through monospace formatting.

### LaTeX Structure
Inline text with `\texttt{}` wrapping and pipe separators:
```latex
\section*{Languages}

    \texttt{Python} | \texttt{Bash} | \texttt{C++} | \texttt{MATLAB} | \texttt{Mathematica}
```

**Key Characteristics:**
- Items wrapped in `\texttt{}` (monospace font for code/tools)
- Pipe separators ` | ` between items
- Single line format (line breaks `\\` optional for long lists)
- No braces or special environments

### YAML Structure
```yaml
type: skill_list_pipes
content:
  list:
  - Python
  - Bash
  - C++
  - MATLAB
  - Mathematica
```

### Test Coverage

**File:** `tests/integration/test_skill_list_pipes.py`

#### Test 1: `test_yaml_to_latex_skill_list_pipes()`

**Purpose:** Validate YAML → LaTeX generation

**What It Tests:**
```python
converter = YAMLToLaTeXConverter()
latex = converter.convert_skill_list_pipes(yaml_dict["section"])

assert "\\texttt{Python}" in latex
assert "\\texttt{Bash}" in latex
assert " | " in latex  # Pipe separators
```

**Why This Matters:**
- Confirms each item is wrapped in `\texttt{}` (semantic: monospace for tools/code)
- Validates pipe separator insertion (` | ` with spaces)
- Tests C++ special character handling (++ not escaped as ++, stays literal)
- Ensures output matches historical resume format exactly

#### Test 2: `test_latex_to_yaml_skill_list_pipes()`

**Purpose:** Validate LaTeX → YAML parsing

**What It Tests:**
```python
converter = LaTeXToYAMLConverter()
result = converter.parse_skill_list_pipes(latex_str)

assert result["type"] == "skill_list_pipes"
assert len(result["content"]["list"]) == 5
assert items[0] == "Python"  # Order preservation
```

**Why This Matters:**
- Confirms regex correctly extracts from `\texttt{...}` patterns
- Validates all items found (count check catches missing items)
- **Order preservation critical** - Python listed first signals primary language to hiring managers
- Tests parser handles `\texttt{}` unwrapping without leaving artifacts

#### Test 3: `test_skill_list_pipes_roundtrip()`

**Purpose:** Validate full round-trip fidelity

**What It Tests:**
```python
# YAML -> LaTeX -> YAML
latex = converter_to_latex.convert_skill_list_pipes(original_dict["section"])
roundtrip_dict = converter_to_yaml.parse_skill_list_pipes(latex)

assert roundtrip_dict == original_dict["section"]
assert roundtrip_dict["content"]["list"] == original_dict["section"]["content"]["list"]
```

**Why This Matters:**
- **Critical fidelity test** - ensures no information loss
- Validates parser and generator are exact inverses
- **Double-checks order** - language order is resume semantics, not just data
- Proves historical resume language lists can be reliably extracted and regenerated

#### Test 4: `test_skill_list_pipes_special_characters()`

**Purpose:** Validate handling of special LaTeX characters

**What It Tests:**
```python
latex_snippet = "\\texttt{C++} | \\texttt{C\\#} | \\texttt{F\\#}"
result = converter.parse_skill_list_pipes(latex_snippet)

assert "C++" in items
assert "C\\#" in items  # Escaped # preserved
```

**Why This Matters:**
- **C++** is extremely common language - must handle `++` correctly (not escaped in LaTeX)
- **C#/F#** test LaTeX escape handling (`\#` required in LaTeX)
- Validates regex doesn't break on special characters
- Ensures developer tool names survive round-trip exactly (critical for technical accuracy)

**Test Data:** `data/resume_archive/structured/languages_test.yaml` + `languages_test.tex`

**Edge Cases Covered:**
- ✅ Special characters (`++` in C++)
- ✅ LaTeX escapes (`\#` for C#/F#)
- ✅ Order preservation (primary language first)
- ✅ Multiple items (5 languages)
- ✅ Monospace wrapping (`\texttt{}` semantic preservation)

**Why Order Matters:**
Listing Python first (vs alphabetical) signals to hiring managers: "This is my primary development language." This is resume semantics encoded in data order, not arbitrary. Tests must preserve it.

---

## Type 5: `skill_categories` (Parent Type)

### Purpose
Container section for organizing skills into multiple themed categories with icons and hierarchical structure. Used for "Software Tools", "AI Tools", or other sections where skills group naturally into technical domains. Provides visual organization through icons and category headers.

### LaTeX Structure
Uses `itemize` environment with multiple `\item[]` entries, each containing a nested `itemizeLL`:
```latex
\section*{Software Tools}

\begin{itemize}[leftmargin=\firstlistindent, labelsep = 0pt, align=center, labelwidth=\firstlistlabelsep, itemsep = 8pt]

\item[\faRobot] {\scshape LLM Architectures}
\begin{itemizeLL}
    \itemLL {Mixture of Experts (MoE)}
    \itemLL {Multimodal Models}
\end{itemizeLL}

\item[\faChartLine] {\scshape ML Frameworks}
\begin{itemizeLL}
    \itemLL {PyTorch}
    \itemLL {JAX/Equinox}
\end{itemizeLL}

\end{itemize}
```

**Key Characteristics:**
- Outer `itemize` environment with specific spacing parameters
- Each category is a `skill_category` subsection (Type 6)
- Nested structure: parent contains multiple children

### YAML Structure
```yaml
type: skill_categories
subsections:
- type: skill_category
  metadata:
    name: LLM Architectures
    icon: \faRobot
  content:
    list:
    - Mixture of Experts (MoE)
    - Multimodal Models
- type: skill_category
  metadata:
    name: ML Frameworks
    icon: \faChartLine
  content:
    list:
    - PyTorch
    - JAX/Equinox
```

---

## Type 6: `skill_category` (Child Type)

### Purpose
Individual themed skill category within a `skill_categories` section. Each category has an icon, small-caps header, and list of related tools/frameworks. Allows readers to quickly scan technical domains.

### LaTeX Structure
`\item[]` with icon, category name, and `itemizeLL` list:
```latex
\item[\faRobot] {\scshape LLM Architectures}
\begin{itemizeLL}
    \itemLL {Mixture of Experts (MoE)}
    \itemLL {Multimodal Models}
\end{itemizeLL}
```

**Key Characteristics:**
- `\item[icon]` with FontAwesome icon
- Category name in small caps (`\scshape`)
- Items in `itemizeLL` environment
- `\itemLL {item}` with braces around content

### YAML Structure
```yaml
type: skill_category
metadata:
  name: LLM Architectures
  icon: \faRobot
content:
  list:
  - Mixture of Experts (MoE)
  - Multimodal Models
```

### Test Coverage

**File:** `tests/integration/test_skill_categories.py`

#### Test 1: `test_yaml_to_latex_skill_categories()`

**Purpose:** Validate YAML → LaTeX generation for nested categories

**What It Tests:**
```python
converter = YAMLToLaTeXConverter()
latex = converter.convert_skill_categories(yaml_dict["section"])

assert "\\begin{itemize}" in latex
assert "\\item[\\faRobot]" in latex
assert "{\\scshape LLM Architectures}" in latex
assert "\\itemLL {PyTorch}" in latex
```

**Why This Matters:**
- Confirms outer `itemize` environment generated with correct parameters
- Validates icon preservation (`\faRobot`, `\faChartLine`, etc.)
- Tests small-caps formatting applied to category names
- Ensures `itemizeLL` nested correctly within each category
- Verifies all items wrapped in braces (`\itemLL {item}` not `\itemLL item`)

#### Test 2: `test_latex_to_yaml_skill_categories()`

**Purpose:** Validate LaTeX → YAML parsing for nested structure

**What It Tests:**
```python
converter = LaTeXToYAMLConverter()
result = converter.parse_skill_categories(latex_str)

assert len(result["subsections"]) == 3
assert cat1["metadata"]["icon"] == "\\faRobot"
assert "Mixture of Experts (MoE)" in cat1["content"]["list"]
```

**Why This Matters:**
- **Nested parsing is complex** - must correctly identify category boundaries
- Validates parser handles multiple `\item[]` entries without confusion
- Tests icon extraction from `\item[icon]` syntax
- Confirms category name extraction from `{\scshape name}` pattern
- Verifies `itemizeLL` items extracted per category (not mixed between categories)

#### Test 3: `test_skill_categories_roundtrip()`

**Purpose:** Validate full round-trip fidelity for nested structure

**What It Tests:**
```python
# YAML -> LaTeX -> YAML
latex = converter_to_latex.convert_skill_categories(original_dict["section"])
roundtrip_dict = converter_to_yaml.parse_skill_categories(latex)

assert roundtrip_dict == original_dict["section"]
assert len(roundtrip_dict["subsections"]) == len(original_dict["section"]["subsections"])
```

**Why This Matters:**
- **Most complex type so far** - nested structure must survive round-trip
- Validates category count preserved (no categories dropped or duplicated)
- Tests category order preservation (order signals priority to readers)
- Ensures items within each category maintain their list order
- Proves nested types can be reliably extracted and regenerated

#### Test 4: `test_skill_categories_icon_preservation()`

**Purpose:** Validate FontAwesome icons handled correctly

**What It Tests:**
```python
result = converter.parse_skill_categories(latex_snippet)
assert category["metadata"]["icon"] == "\\faDatabase"
```

**Why This Matters:**
- Icons are **visual semantics** - `\faRobot` signals AI, `\faDatabase` signals data tools
- Tests various icon types (`\faRobot`, `\faChartLine`, `\faCode`, `\faDatabase`)
- Validates backslash preserved in icon commands
- Ensures icons don't interfere with category name parsing

#### Test 5: `test_skill_categories_special_characters()`

**Purpose:** Validate special character handling in nested lists

**What It Tests:**
```python
items = result["subsections"][0]["content"]["list"]
assert "C++" in items
assert "C\\#" in items  # Escaped # preserved
```

**Why This Matters:**
- Special characters common in tool names (C++, C#, Python 3.9+)
- Tests `++` handling (not escaped in LaTeX)
- Tests `\#` escape preservation (required in LaTeX)
- Validates version numbers with special chars (3.9+)
- Ensures nested parsing doesn't break on special characters

**Test Data:** `data/resume_archive/structured/software_tools_test.yaml` + `software_tools_test.tex`

**Edge Cases Covered:**
- ✅ Multiple categories (3 categories tested)
- ✅ Different icons per category
- ✅ Variable item counts per category (2-3 items)
- ✅ Special characters (C++, C#, slashes in JAX/Equinox)
- ✅ Nested structure preservation (parent-child relationship)
- ✅ Category order preservation
- ✅ Item order within each category

**Why Nested Testing Matters:**
This is ARCHER's first **hierarchical type** - a parent containing typed children. Tests must validate:
- Parent correctly contains children (no flattening)
- Children correctly nest within parent (no promotion to siblings)
- Boundaries between categories detected correctly (no item mixing)
- Order preserved at both levels (category order + item order within each)

Successful nested type parsing proves the architecture can handle complex document structure, not just flat lists.

---

## Page Structure: Single-Page Resume

### Purpose
Validates complete page-level parsing including paracol two-column structure, section organization, and column separation. This is the first test of **document structure** beyond individual content types.

### LaTeX Structure
Two-column layout with `paracol` environment and `\switchcolumn`:
```latex
\begin{paracol}{2}

\section*{Core Skills}
   { ... skill list ... }

\section*{Languages}
    \texttt{Python} | \texttt{Bash} | \texttt{C++}

\switchcolumn

\section*{Experience}
    \begin{itemizeAcademic}{...}{...}{...}{...}
        \itemi Achievement bullet...
    \end{itemizeAcademic}

\end{paracol}
```

**Key Characteristics:**
- `\begin{paracol}{2}` starts two-column mode
- Left column contains multiple sections before `\switchcolumn`
- `\switchcolumn` marks column transition
- Main/right column contains remaining sections
- `\end{paracol}` closes structure

### Structured Format
```yaml
page:
  page_number: 1
  regions:
    top:
      show_professional_profile: true
    left_column:
      sections:
      - name: Core Skills
        type: skill_list_caps
        content: {...}
      - name: Languages
        type: skill_list_pipes
        content: {...}
    main_column:
      sections:
      - name: Experience
        type: work_history
        subsections: [...]
    bottom: null
```

### Test Coverage

**File:** `tests/integration/test_single_page.py`

#### Test 1: `test_parse_single_page_structure()`

**Purpose:** Validate parsing of paracol structure into regions

**What It Tests:**
```python
converter = LaTeXToYAMLConverter()
page_regions = converter.extract_page_regions(latex_str, page_number=1)

assert page_regions["left_column"] is not None
assert len(left_sections) == 2
assert left_sections[0]["name"] == "Core Skills"
```

**Why This Matters:**
- **First document-level parsing** - beyond individual content types
- Validates `\begin{paracol}{2}` and `\end{paracol}` detection
- Tests `\switchcolumn` marker correctly splits columns
- Confirms section names extracted from each column
- Ensures section type inference works (skill_list_caps, skill_list_pipes, work_history)

#### Test 2: `test_generate_single_page_structure()`

**Purpose:** Validate generation of paracol structure from regions

**What It Tests:**
```python
converter = YAMLToLaTeXConverter()
latex = converter.generate_page(yaml_dict["page"]["regions"])

assert "\\begin{paracol}{2}" in latex
assert "\\switchcolumn" in latex
assert "\\section*{Core Skills}" in latex
```

**Why This Matters:**
- Validates complete page assembly with correct structure
- Tests paracol environment wrapper generated
- Confirms `\switchcolumn` inserted at correct position
- Ensures all sections regenerated with correct types
- Verifies section order preserved within each column

#### Test 3: `test_single_page_roundtrip()`

**Purpose:** Validate full page-level round-trip fidelity

**What It Tests:**
```python
# LaTeX → structure → LaTeX
page_regions = parser.extract_page_regions(original_latex)
generated_latex = generator.generate_page(page_regions)
roundtrip_regions = parser.extract_page_regions(generated_latex)

assert len(roundtrip_regions["left_column"]["sections"]) == len(page_regions["left_column"]["sections"])
```

**Why This Matters:**
- **Critical page structure test** - proves page-level fidelity
- Validates column count preserved (2 columns in, 2 columns out)
- Tests section count preserved in each column
- Confirms section names and types survive round-trip
- Ensures no content moves between columns during conversion

#### Test 4: `test_paracol_column_separation()`

**Purpose:** Validate left and main columns correctly separated

**What It Tests:**
```python
left_names = [s["name"] for s in page_regions["left_column"]["sections"]]
main_names = [s["name"] for s in page_regions["main_column"]["sections"]]

assert "Core Skills" in left_names
assert "Experience" in main_names
assert "Experience" not in left_names  # No cross-contamination
```

**Why This Matters:**
- **Column separation is critical** - sections must stay in correct column
- Tests `\switchcolumn` correctly divides content
- Validates no sections appear in both columns (no duplication)
- Confirms no sections missing (no loss during split)
- Ensures layout structure preserved (skills left, experience right)

#### Test 5: `test_section_content_preserved()`

**Purpose:** Validate section content survives page-level parsing

**What It Tests:**
```python
core_skills = page_regions["left_column"]["sections"][0]
assert "Machine Learning" in core_skills["content"]["list"]

experience = page_regions["main_column"]["sections"][0]
assert work_exp["metadata"]["company"] == "Test Company"
```

**Why This Matters:**
- Page-level parsing must **not corrupt section content**
- Tests content from different types (skill lists, work experience) all preserved
- Validates metadata fields survive (company, title, etc.)
- Confirms nested content (bullets, projects) maintained
- Proves page parsing composes correctly with section parsing

**Test Data:** `data/resume_archive/structured/single_page_test.tex` + `single_page_test.yaml`

**Edge Cases Covered:**
- ✅ Multiple sections per column (2 in left, 1 in main)
- ✅ Different section types in same column (skill_list_caps + skill_list_pipes)
- ✅ Paracol environment boundaries
- ✅ Column transition (`\switchcolumn`)
- ✅ Section content preservation through page parsing

**Why Page Structure Testing Matters:**

This is ARCHER's **first hierarchical document structure** test - validating that:
- **Composition works** - section parsers combine correctly into page parser
- **Structure preserved** - paracol layout maintained through round-trip
- **No cross-contamination** - columns stay separate
- **Content fidelity** - all section content survives page-level parsing

Success here proves the architecture scales from individual types → sections → columns → complete pages.

---

## Step 5: Document Metadata Tests

**File:** `tests/integration/test_document_metadata.py`

Document metadata extraction and generation tests validate parsing of the LaTeX preamble (everything before `\begin{document}`). This is **ARCHER's first document-level parsing** - extracting metadata that applies to the entire resume.

**Purpose:** Parse `\renewcommand` fields and color definitions from preamble

**Type Definition:** `resume_components_data_structures.py:DocumentMetadata` data class

**Test Fixtures:**
- `data/resume_archive/structured/document_metadata_test.tex` - Minimal preamble with metadata
- `data/resume_archive/structured/document_metadata_test.yaml` - Corresponding structured metadata

**What Document Metadata Contains:**
- `name`: Full name (from `\renewcommand{\myname}{\textbf{...}}`)
- `date`: Date (from `\renewcommand{\mydate}{...}`)
- `brand`: Professional title/brand (from `\renewcommand{\brand}{...}`)
- `professional_profile`: Optional profile text (from `\renewcommand{\ProfessionalProfile}{...}`)
- `colors`: Color scheme (emphcolor, topbarcolor, leftbarcolor, brandcolor, namecolor)
- `fields`: All other `\renewcommand` fields (pdfkeywords, custom fields)

### Tests

#### Test 1: `test_parse_document_metadata()`

**Purpose:** Parse all metadata fields from LaTeX preamble

**What It Tests:**
```python
metadata = parser.extract_document_metadata(latex_str)

assert metadata["name"] == "Sean Stafford"
assert metadata["brand"] == "Research Infrastructure Engineer | Physicist"
assert metadata["colors"]["emphcolor"] == "NetflixDark"
assert metadata["fields"]["pdfkeywords"] == "Sean, Stafford, Resume"
```

**Why This Matters:**
- **Preamble parsing is foundational** - metadata applies to entire document
- Tests `\renewcommand` extraction with nested braces (e.g., `\textbf{...}`)
- Validates color field separation from general fields
- Confirms known fields (name, brand, profile) vs. custom fields handled correctly
- Proves parser handles LaTeX formatting commands (`\textbf`, `\centering`, `\par`)

#### Test 2: `test_generate_preamble()`

**Purpose:** Generate LaTeX preamble from metadata dict

**What It Tests:**
```python
preamble = generator.generate_preamble(metadata)

assert "\\renewcommand{\\myname}{\\textbf{Sean Stafford}}" in preamble
assert "\\renewcommand{\\emphcolor}{NetflixDark}" in preamble
assert "\\renewcommand{\\ProfessionalProfile}" in preamble
```

**Why This Matters:**
- **Generation must produce valid LaTeX** - preamble structure matters
- Tests correct `\renewcommand` syntax with nested braces
- Validates color commands generated correctly
- Confirms professional profile wrapped with `\centering \textbf{...}\par`
- Proves pdfkeywords and setuphyperandmeta included

#### Test 3: `test_metadata_roundtrip()`

**Purpose:** Validate LaTeX → metadata → LaTeX preserves all fields

**What It Tests:**
```python
metadata = parser.extract_document_metadata(original_latex)
generated_preamble = generator.generate_preamble(metadata)
roundtrip_metadata = parser.extract_document_metadata(generated_preamble + "\\begin{document}...")

assert roundtrip_metadata["name"] == metadata["name"]
assert roundtrip_metadata["colors"] == metadata["colors"]
```

**Why This Matters:**
- **Round-trip fidelity is critical** - metadata must survive conversion
- Tests parser and generator are inverses
- Validates no fields lost or corrupted
- Confirms color dict preserved completely
- Proves metadata extraction robust enough for real resumes

#### Test 4: `test_metadata_without_profile()`

**Purpose:** Handle optional professional profile field

**What It Tests:**
```python
# LaTeX has no \ProfessionalProfile command
metadata = parser.extract_document_metadata(latex)

assert metadata["name"] == "Test Name"
assert metadata["professional_profile"] is None
```

**Why This Matters:**
- **Optional fields must be handled** - not all resumes have profiles
- Tests parser doesn't fail when profile absent
- Validates `professional_profile` set to `None` (not empty string)
- Confirms other fields still extracted correctly
- Proves parser gracefully handles minimal preambles

#### Test 5: `test_metadata_field_preservation()`

**Purpose:** Preserve all `\renewcommand` fields, even unknown ones

**What It Tests:**
```python
# LaTeX has custom \renewcommand{\customfield}{Custom Value}
metadata = parser.extract_document_metadata(latex)

assert "customfield" in metadata["fields"]
assert metadata["fields"]["customfield"] == "Custom Value"
```

**Why This Matters:**
- **Unknown fields must not be lost** - resumes may have custom metadata
- Tests parser doesn't drop unrecognized `\renewcommand` fields
- Validates custom fields stored in `fields` dict
- Confirms known fields (name, brand, colors) separated from custom fields
- Proves parser extensible to new metadata fields without code changes

**Edge Cases Covered:**
- ✅ Nested braces in field values (`\textbf{...}`)
- ✅ Multi-line field values (professional profile)
- ✅ Optional fields (professional_profile can be None)
- ✅ Unknown custom fields preserved
- ✅ Color fields separated from general fields

**Why Document Metadata Testing Matters:**

This is ARCHER's **first document-level parsing** - validating that:
- **Preamble extraction works** - everything before `\begin{document}` parsed correctly
- **Nested brace handling robust** - LaTeX commands within field values handled
- **Field categorization correct** - colors, known fields, custom fields separated appropriately
- **Optional fields supported** - parser doesn't fail on missing fields
- **Round-trip fidelity** - metadata survives conversion without corruption

Success here proves ARCHER can extract document-wide configuration (name, brand, colors) that will later be used to generate customized resumes from templates.

---
## Testing Strategy

### Unit Tests
- **Fast, isolated** - Test individual parser/generator functions
- **Mock dependencies** - No file I/O, no LaTeX compilation
- **Edge case focused** - Empty strings, malformed input, missing fields

### Integration Tests
- **Full round-trip** - Real file fixtures, complete conversion pipeline
- **Fixture-based** - Each type has dedicated `.tex` and `.yaml` test files
- **Regression detection** - Any change breaking round-trip is caught immediately

### Test Data Management
All test fixtures stored in: `data/resume_archive/structured/`
- `{type}_test.yaml` - Source YAML structure
- `{type}_test.tex` - Corresponding LaTeX
- `{type}_roundtrip.tex` - Generated output (for manual inspection)

---

## Success Criteria

For each type, tests must validate:
1. ✅ **Structure Preservation** - All required fields extracted/generated
2. ✅ **Content Fidelity** - Text content byte-identical (ignoring whitespace)
3. ✅ **Formatting Preservation** - LaTeX commands (`\textbf{}`, `\coloremph{}`, etc.) maintained
4. ✅ **Round-trip Identity** - Original → Convert → Convert → Original produces identical result
5. ✅ **Edge Case Handling** - Special characters, line breaks, empty fields work correctly

---

## Next Steps

As each new type is added:
1. Create type definition YAML
2. Implement parser and generator
3. Create test fixtures (`.yaml` + `.tex`)
4. Write integration tests (all 3: yaml→latex, latex→yaml, roundtrip)
5. Document in this file with clear explanations of **why** each test matters
6. Run full test suite to ensure no regressions

This ensures every type has **complete, meaningful test coverage** that validates both correctness and real-world usage patterns.
