# Test Resume Demo

ARCHER includes a fully functional demo using humorous Futurama-themed test resumes that demonstrate the complete pipeline from raw LaTeX to final PDF, including tracking, customization, and variants.

All demo files use the `_test_` prefix for easy identification and the associated files are distributed across the repository the same way actual resumes are.

---

## Demo Resumes

### 1. **_test_Res202511_Fry_MomCorp** (Baseline)
Philip J. Fry's resume for a delivery position - demonstrates the standard pipeline flow.

### 2. **_test_Res202511_Fry_MomCorp_finetuned** (Quality Reference)
Manually tuned variant that serves as a quality reference for future content density validation features. Demonstrates proper spacing, layout, and content organization, useful later for automated validation.

---

## File Locations

### Source Files (Raw LaTeX)

```
data/resume_archive/raw/
├── _test_Res202511_Fry_MomCorp.tex             # Baseline version
└── _test_Res202511_Fry_MomCorp_finetuned.tex   # Finetuned variant
```

### Structured Data

```
data/resume_archive/structured/
├── _test_Res202511_Fry_MomCorp.yaml
└── _test_Res202511_Fry_MomCorp_finetuned.yaml
```

### Normalized LaTeX

```
data/resume_archive/
├── _test_Res202511_Fry_MomCorp.tex
└── _test_Res202511_Fry_MomCorp_finetuned.tex
```

### Pipeline Tracking

```
outs/logs/
├── resume_registry.csv                         # Status registry
├── resume_pipeline_events.log                  # Event timeline
└── render_20251121_015223/                     # Detailed render log
    ├── render.log
    └── _test_Res202511_Fry_MomCorp_finetuned.pdf (symlink)
```

### Final Results

```
outs/results/
└── 20251121/
    └── _test_Res202511_Fry_MomCorp_finetuned.pdf   # Compiled PDF
```

---

## Tracing a Resume Through the Pipeline

### 1. Registration

Check the registry to see both resumes are tracked:

```bash
grep "_test_" outs/logs/resume_registry.csv
```

**Output:**
```csv
_test_Res202511_Fry_MomCorp,test,rendering_completed,2025-11-16T22:48:20.454347
_test_Res202511_Fry_MomCorp_finetuned,test,rendering_completed,2025-11-21T01:52:24.503886
```

### 2. Event Timeline

View the complete pipeline journey:

```bash
grep "_test_Res202511_Fry_MomCorp_finetuned" outs/logs/resume_pipeline_events.log | jq
```

**Key events:**
1. **Registration** - Manual registration with reason
2. **Rendering** - Status change to `rendering`
3. **Completion** - Status change to `rendering_completed` with metrics

### 3. LaTeX → YAML Conversion

Convert the baseline resume to structured YAML:

```bash
python scripts/convert_template.py convert data/resume_archive/raw/_test_Res202511_Fry_MomCorp.tex
```

**Output:** `data/resume_archive/structured/_test_Res202511_Fry_MomCorp.yaml`

### 4. YAML → LaTeX Roundtrip

Test bidirectional conversion fidelity:

```bash
python scripts/test_roundtrip.py test data/resume_archive/_test_Res202511_Fry_MomCorp.tex
```

**Expected:** 0 LaTeX diffs, 0 YAML diffs (perfect roundtrip)

### 5. PDF Compilation

Compile the finetuned version:

```bash
python scripts/compile_pdf.py compile data/resume_archive/_test_Res202511_Fry_MomCorp_finetuned.tex
```

**Output:** PDF in `outs/results/20251121/_test_Res202511_Fry_MomCorp_finetuned.pdf`

### 6. Status Tracking

View status timeline:

```bash
make track RESUME=_test_Res202511_Fry_MomCorp_finetuned
```

---

## Comparing Variants

### Diff the LaTeX Files

```bash
diff data/resume_archive/raw/_test_Res202511_Fry_MomCorp.tex \
     data/resume_archive/raw/_test_Res202511_Fry_MomCorp_finetuned.tex
```

**Key differences:**
- Content condensing:
    - One or more work_experience sections removed
    - Shortened professional profile
    - Newlines added in some list sections
    - Some bullet points possibly shortened
- Style customization (color scheme, new symbols)

---

## Using Test Resumes for Development

### Testing Status Changes

```bash
# Update status
python scripts/manage_registry.py update _test_Res202511_Fry_MomCorp rendering_failed \
    --reason "Testing failure handling"

# View timeline
make track RESUME=_test_Res202511_Fry_MomCorp
```

### Testing Normalization

```bash
# Normalize with suffix to create variant
python scripts/normalize_latex.py batch --in-place --suffix normalized \
    data/resume_archive/raw/
```

### Testing YAML Cleaning

```bash
# Remove latex_raw fields from YAML
# (manually edit to delete some latex_raw fields)

# Clean the YAML
python scripts/convert_template.py clean \
    data/resume_archive/structured/_test_Res202511_Fry_MomCorp.yaml --dry-run
```

---

## Demo Characteristics

**Distributed structure:** Files are located in their actual pipeline locations rather than a separate demo directory.

**Pipeline coverage:** Includes raw LaTeX, structured YAML, normalized output, and compiled PDF.

**Event tracking:** All stages are logged in the registry and event log with timestamps and compilation metrics.

**Isolated from real data:** `_test_` prefix and `type=test` distinguish these from actual resumes.

**Fictional content:** Uses Futurama characters (Philip J. Fry, Planet Express, MomCorp) for dynamically generated content (work experience, skills, projects, professional profile).

**LaTeX constants caveat:** The Education section does not vary at all across ARCHER resumes so it is not part of the dynamic resume generation pipeline. Therefore, modification of the Education section was not worth the effort for the test resume -- it contains real information. The LinkedIn URL in the header is also real.
