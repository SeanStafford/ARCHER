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

## Next Steps

As each new type is added:
1. Create type definition YAML
2. Implement parser and generator
3. Create test fixtures (`.yaml` + `.tex`)
4. Write integration tests (all 3: yaml→latex, latex→yaml, roundtrip)
5. Document in this file with clear explanations of **why** each test matters
6. Run full test suite to ensure no regressions

This ensures every type has **complete, meaningful test coverage** that validates both correctness and real-world usage patterns.
