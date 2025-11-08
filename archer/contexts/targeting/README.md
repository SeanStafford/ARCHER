# Targeting Context

## Primary Responsibility

**Select relevant content from historical resume archive to populate new resumes based on job requirements.**

The targeting context is the "brain" of ARCHER - it decides *which* experience bullets, projects, and skills to include from the resume archive for a specific job application.

## Context Boundaries

**Owns**:
- Content selection logic (which bullets, projects, skills to include)
- Relevance scoring algorithms (how well does content match job requirements?)
- Historical resume analysis (pattern extraction from archive)
- Section prioritization and ordering decisions

**Never**:
- Directly accesses raw job descriptions (uses normalized data from Intake context)
- Directly reads `.tex` files (uses structured `ResumeDocument` from Templating context)
- Makes LaTeX formatting decisions (that's Templating's responsibility)

## Current Structure

```
archer/contexts/targeting/
├── __init__.py                  # Context docstring
├── README.md                    # This file
├── selector.py                  # MAIN: Content selection (future)
├── scorer.py                    # Relevance scoring (future)
│
└── historical/                  # Statistical analysis subdirectory
    ├── __init__.py
    └── analyzer.py              # Pattern analysis of resume archive
```

## Current Implementation

### Historical Analysis (`historical/analyzer.py`)

Statistical analysis of the resume archive to understand patterns and inform content selection.

**`ResumeArchiveAnalyzer`** - Analyzes structured resume data from archive

**Key Methods**:
- `load_archive()` - Parse all resumes in archive directory
- `section_prevalence()` - Count how often each section appears
- `field_value_distribution(field)` - Distribution of field values (e.g., brand, colors)

**Usage**:
```python
from pathlib import Path
from archer.contexts.targeting.historical.analyzer import ResumeArchiveAnalyzer

analyzer = ResumeArchiveAnalyzer(Path("data/resume_archive"))
analyzer.load_archive()

# Which sections are most common?
prevalence = analyzer.section_prevalence()
# {"Core Skills": 57, "Experience": 57, "Education": 57, ...}

# What brand values are used?
brands = analyzer.field_value_distribution("brand")
# {"Software Engineer | Physicist": 34, "Machine Learning Engineer | Physicist": 26, ...}
```

## Future Directions

### Content Selection (High Priority)

**`selector.py`** - Main content selection logic
- Select N most relevant experience bullets for job
- Identify portfolio projects to highlight
- Choose skill categories to include
- Determine section ordering and emphasis
- Assemble final content package for Templating context

**`scorer.py`** - Relevance scoring algorithms
- Score experience bullets against job requirements
- Keyword matching (tools, frameworks, methodologies)
- Semantic similarity (future: LLM-based scoring)
- Domain matching (ML job → ML experience prioritized)

### Advanced Analysis (Future)

**Skill Categorization Analysis**:
- Which skills appear together in successful resumes?
- Common category groupings (ML Frameworks, MLOps, Infrastructure)
- Icon usage patterns for different skill types

**Project Reuse Tracking**:
- Identify portfolio projects used across multiple applications
- Track which projects work for which job types
- Quantify achievement impact (metrics, percentages)

**Temporal Pattern Analysis**:
- Content evolution over time (parse YYYYMM from filename)
- Skills added/deprecated over career trajectory
- Section presence changes (when did HPC Highlights first appear?)

**Job Type Clustering**:
- Extract job type from brand field or filename
- Group resumes by job type (ML Engineer, Software Engineer, Research)
- Identify common patterns per cluster (ML roles → AI & ML section)

**Content Density Optimization**:
- Bullets per work experience (mean, min, max)
- Projects per job position
- Skills per category
- Optimal section count per page/column

**Semantic Similarity** (LLM Integration):
- Embed job description and experience bullets
- Compute cosine similarity for relevance
- Generate explanations for content selection decisions

## Design Philosophy

The targeting context operates on **structured data**, not raw LaTeX. This separation:
- Makes analysis simpler (no regex hell)
- Enables sophisticated algorithms (ML, LLMs can't parse LaTeX easily)
- Respects context boundaries (Templating owns LaTeX knowledge)
- Improves testability (work with Python dicts, not string patterns)

**Access Pattern**:
```python
# ✅ CORRECT: Use ResumeDocument from Templating
from archer.contexts.templating.resume_data_structure import ResumeDocument

doc = ResumeDocument.from_tex(path)
sections = doc.sections  # List[ResumeSection]
brand = doc.get_field("brand")

# ❌ WRONG: Don't parse LaTeX directly in targeting
content = path.read_text()
sections = re.findall(r"\\section\*\{([^}]+)\}", content)  # NO!
```

## Integration with Other Contexts

```
Intake Context → Targeting Context → Templating Context → Rendering Context
(parses job)     (selects content)    (populates LaTeX)   (compiles PDF)
```

**Flow**:
1. **intake** provides normalized job description to targeting
2. **targeting** analyzes job, searches archive, selects relevant content
3. **templating** receives content selections, populates template, generates `.tex`
4. **rendering** compiles `.tex` to PDF

**Data Exchange**:
- intake → targeting: `NormalizedJob` (job type, skills, requirements)
- targeting → templating: `ContentSelections` (bullets, projects, skills, sections, branding)
- templating → rendering: Populated `.tex` file

## Testing Strategy

**Unit Tests**:
- Individual analysis methods (section counting, field extraction)
- Scoring algorithms (relevance calculation)
- Content selection logic (mock archive data)

**Integration Tests**:
- Load real archive, verify analysis correctness
- End-to-end: job description → content selections
- Validate selections make sense for job type

## See Also

- `/home/sean/CLAUDE.md` - User's strategic goals (technical credibility, AI usage philosophy)
- `docs/Design_Decisions.md` - Architectural decisions (why DDD, why YAML, etc.)
- `archer/contexts/templating/README.md` - Templating context (structured data conversion)
