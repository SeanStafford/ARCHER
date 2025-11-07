# Parsing Operations Reference

This document provides detailed examples of all parsing operations available in ARCHER's config-driven parsing system.

## Overview

The parsing system uses a **unified `parse_with_config()` method** that reads declarative operations from `parse_config.yaml` files. Instead of type-specific parsing methods with hardcoded regex, each type defines parsing rules as a sequence of operations.

Operations execute in order. Some operations store content in contexts (e.g., `environment_content`) for later operations to consume.

## Available Operations

### `set_literal`

Set a literal value in the output structure.

**Example:**
```yaml
type_field:
  operation: set_literal
  output_path: type
  value: work_experience
```

**Use case:** Setting the `type` field to identify section type.

---

### `extract_environment`

Extract a LaTeX environment with parameters.

**Example:**
```yaml
environment:
  operation: extract_environment
  env_name: itemizeAcademic
  num_params: 4
  param_names:
    - metadata.company
    - metadata.title
    - metadata.location
    - metadata.dates
  output_context: environment_content  # Store content for later ops
```

**Use case:** Extracting structured environments like `\begin{itemizeAcademic}{Company}{Title}{Location}{Dates}...\end{itemizeAcademic}`.

**Parameters:**
- `env_name`: LaTeX environment name (without `\begin`/`\end`)
- `num_params`: Number of parameters in curly braces
- `param_names`: Dotted paths where to store each parameter
- `output_context`: Context variable name to store environment content

---

### `split`

Split a string on a delimiter (regex or literal).

**Example:**
```yaml
split_title:
  operation: split
  source_path: metadata.title
  delimiter: '\\\\'  # Split on \\
  output_paths:
    - metadata.title
    - metadata.subtitle
```

**Use case:** Splitting multi-line titles like `Machine Learning Engineer\\Supporting a federal client` into title and subtitle.

**Parameters:**
- `source_path`: Dotted path to the string to split
- `delimiter`: Regex or literal delimiter
- `output_paths`: List of dotted paths for split results (first part, second part, etc.)

---

### `recursive_parse`

Parse nested structures using another type's parse config.

**Example:**
```yaml
projects:
  operation: recursive_parse
  source: environment_content
  recursive_pattern: ITEMIZE_PROJECT_ENV
  config_name: project
  output_path: content.projects
```

**Use case:** Parsing nested projects within work experience sections.

**Parameters:**
- `source`: Context variable containing the text to parse
- `recursive_pattern`: Regex pattern to find nested structures (from `latex_patterns.py`)
- `config_name`: Type name whose parse config to use for parsing each match
- `output_path`: Dotted path where to store list of parsed structures

**Note:** This operation removes matched content from the source context, so subsequent operations don't re-parse it.

---

### `parse_itemize_content`

Parse bullet lists with markers like `\itemi`, `\itemii`, `\item[--]`.

**Example:**
```yaml
bullets:
  operation: parse_itemize_content
  marker_pattern: ITEM_ANY
  source: environment_content
  output_path: content.bullets
```

**Use case:** Extracting bulleted lists from work experience, projects, skill categories.

**Parameters:**
- `marker_pattern`: Pattern name from `latex_patterns.py` (e.g., `ITEM_ANY`, `ITEM_LEVEL_ONE`)
- `source`: Context variable containing the text to parse
- `output_path`: Dotted path where to store list of bullets

**Output format:** Each bullet is a dict with `marker`, `latex_raw`, and `plaintext` fields.

---

### `extract_braced_after_pattern`

Extract balanced braces after a pattern match.

**Example:**
```yaml
extract_braced:
  operation: extract_braced_after_pattern
  pattern: '(\{)\s*\\setlength'  # Capture opening brace
  output_context: braced_content
```

**Use case:** Extracting content from `{\setlength{...} content here}` structures.

**Parameters:**
- `pattern`: Regex pattern that captures the opening brace
- `output_context`: Context variable name to store extracted content

---

### `extract_regex`

Extract content using named capture groups.

**Example:**
```yaml
header:
  operation: extract_regex
  regex: '\\item\[(?P<icon>[^\]]*)\].*?\\scshape\s+(?P<name>[^}]+)\}'
  extract:
    icon: metadata.icon
    name: metadata.name
```

**Use case:** Extracting structured data like `\item[\faCode] {\scshape Programming Languages}`.

**Parameters:**
- `regex`: Regular expression with named capture groups (`(?P<name>...)`)
- `extract`: Mapping of capture group names to output dotted paths

---

## Complete Example: work_experience Parse Config

Here's a complete `parse_config.yaml` showing how operations work together:

```yaml
patterns:
  # Set the type field
  type_field:
    operation: set_literal
    output_path: type
    value: work_experience

  # Extract the itemizeAcademic environment
  environment:
    operation: extract_environment
    env_name: itemizeAcademic
    num_params: 4
    param_names:
      - metadata.company
      - metadata.title
      - metadata.location
      - metadata.dates
    output_context: environment_content

  # Split title on \\ to get subtitle
  split_title:
    operation: split
    source_path: metadata.title
    delimiter: '\\\\'
    output_paths:
      - metadata.title
      - metadata.subtitle

  # Parse nested projects (removes them from environment_content)
  projects:
    operation: recursive_parse
    recursive_pattern: ITEMIZE_PROJECT_ENV
    config_name: project
    source: environment_content
    output_path: content.projects

  # Parse remaining bullets
  bullets:
    operation: parse_itemize_content
    marker_pattern: ITEM_ANY
    source: environment_content
    output_path: content.bullets
```

**Execution flow:**

1. `type_field`: Sets `type: "work_experience"`
2. `environment`: Extracts `\begin{itemizeAcademic}{Company}{Title}{Location}{Dates}`, stores content in `environment_content` context, stores params in `metadata.*`
3. `split_title`: Splits `metadata.title` on `\\`, stores first part back in `metadata.title`, second part in `metadata.subtitle`
4. `projects`: Finds all `\begin{itemizeAProject}` and `\begin{itemizeKeyProject}` environments in `environment_content`, recursively parses each using `project` config, stores results in `content.projects`, **removes matched text from `environment_content`**
5. `bullets`: Parses remaining `\itemi`, `\itemii` bullets from `environment_content`, stores in `content.bullets`

## Example Output Structure

The above config produces this structure:

```python
{
    "type": "work_experience",
    "metadata": {
        "company": "Booz Allen Hamilton",
        "title": "Machine Learning Engineer",
        "subtitle": "Supporting a federal client",
        "location": "Catonsville, MD",
        "dates": "Nov 2023 --- May 2025"
    },
    "content": {
        "projects": [
            {
                "type": "project",
                "metadata": {
                    "title": "Scaling studies of MoE models",
                    "dates": "",
                    "environment_type": "itemizeAProject"
                },
                "content": {
                    "bullets": [
                        {
                            "marker": "itemii",
                            "latex_raw": "Performed original scaling studies...",
                            "plaintext": "Performed original scaling studies..."
                        }
                    ]
                }
            }
        ],
        "bullets": [
            {
                "marker": "itemi",
                "latex_raw": "\\textbf{Cut LLM training sessions from 1 month to 12 hours}...",
                "plaintext": "Cut LLM training sessions from 1 month to 12 hours..."
            }
        ]
    }
}
```

## Writing New Parse Configs

When adding a new content type:

1. **Analyze the LaTeX pattern** - Look at actual examples from historical resumes
2. **Identify structure** - Environment? Inline? Nested?
3. **Choose operations** - Pick operations that match the structure
4. **Test order** - Operations execute sequentially, earlier ops can set up context for later ops
5. **Validate** - Test on real historical resumes, not just synthetic fixtures

**Golden rule:** Patterns belong in `parse_config.yaml`, not in Python code. If you find yourself writing regex in Python, you're doing it wrong.
