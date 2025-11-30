# Orchestration and CLI Patterns

This document codifies the patterns for pipeline-relevant orchestration functions and their corresponding CLI commands in ARCHER.

## Overview

ARCHER uses a two-layer architecture for resume pipeline operations:

1. **In-Context Orchestration Functions** - Python functions in bounded contexts that handle logging, validation, and registry tracking
2. **CLI Scripts** - Thin Typer wrappers that call orchestration functions and format output for the terminal

```
User runs CLI command
        │
        ▼
┌─────────────────────────────────────┐
│          CLI Script Layer           │
│  - Validate resume_identifier       │
│  - Call orchestration function      │
│  - Display results to terminal      │
│  - Exit with appropriate code       │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│     In-Context Orchestration        │
│  - Setup two-tier logging           │
│  - Pre-validation (raises errors)   │
│  - Call pure function               │
│  - Update registry status           │
│  - Cleanup artifacts                │
│  - Return result dataclass          │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│         Pure Functions              │
│  - Actual work (compile, convert)   │
│  - No logging or registry           │
│  - Returns result or raises         │
└─────────────────────────────────────┘
```

---

## Orchestration Functions

Orchestration functions live in bounded contexts and wrap pure functions with pipeline infrastructure.

### Responsibilities

1. **Pre-validation** - Check resume is registered, type/status allows operation, files exist
2. **Setup logging** - Create timestamped log directory, configure loguru
3. **Update registry** - Set status to in-progress, then success/failure
4. **Call pure function** - Do the actual work
5. **Handle outcomes** - Clean artifacts on success, keep on failure
6. **Return result** - Dataclass with success, paths, timing, diagnostics

### Result Dataclasses

Every orchestration function returns a result dataclass with these common fields:

```python
@dataclass
class SomeResult:
    success: bool                      # Whether operation succeeded
    error: Optional[str] = None        # Error message if failed
    log_dir: Optional[Path] = None     # Directory with logs and artifacts
    time_s: float = 0.0                # Elapsed time in seconds

    # Operation-specific fields...
    output_path: Optional[Path] = None
    page_count: Optional[int] = None
```

**Examples:**
- `CompilationResult` - `pdf_path`, `compile_dir`, `errors`, `warnings`, `page_count`
- `ConversionResult` - `input_path`, `output_path`, `yaml_diffs`, `latex_diffs`
- `ValidationResult` - `is_valid`, `diagnostics`, `feedback`

### Pre-Validation Pattern

Pre-validation happens **before** logging starts and **raises ValueError** for invalid inputs:

```python
def some_orchestration_function(resume_name: str, ...) -> SomeResult:
    """Orchestration function with pre-validation."""

    # Pre-validation (raises ValueError - no logging yet)
    if not resume_is_registered(resume_name):
        raise ValueError(f"Resume not registered: {resume_name}")

    resume_type = get_resume_status(resume_name).get("resume_type")
    if resume_type not in ALLOWED_TYPES:
        raise ValueError(f"Invalid resume type: {resume_type}")

    input_file = get_resume_file(resume_name, "tex")  # Raises if not found

    if not allow_overwrite and output_path.exists():
        raise ValueError(f"Output already exists: {output_path}")

    # --- Logging starts here ---
    log_dir = LOGS_PATH / f"operation_{now()}"
    setup_context_logger(log_dir)

    # ... rest of orchestration
```

**Invalid resume_identifier can mean:**
- Not registered in registry
- Wrong resume type for this operation (e.g., parsing historical vs experimental)
- Wrong status for this operation (e.g., must be 'normalized' before parsing)
- Required file not found (tex, yaml, pdf)
- Output file exists and overwrite not allowed

### Orchestration Function Template

```python
def orchestrate_operation(
    resume_name: str,
    output_dir: Optional[Path] = None,
    allow_overwrite: bool = True,
) -> OperationResult:
    """
    Perform operation with registry tracking and logging.

    Args:
        resume_name: Resume identifier (must be registered)
        output_dir: Output directory (default: determined by resume type)
        allow_overwrite: Allow overwriting existing output (default: True)

    Returns:
        OperationResult with success status and diagnostics

    Raises:
        ValueError: If resume not registered, invalid type/status, or file not found
    """
    # 1. Pre-validation (raises ValueError)
    _validate_operation_allowed(resume_name)
    input_file = get_resume_file(resume_name, "tex")

    if output_dir is None:
        output_dir = _get_default_output_dir(resume_name)

    output_path = output_dir / f"{resume_name}.ext"
    if not allow_overwrite and output_path.exists():
        raise ValueError(f"Output already exists: {output_path}")

    # 2. Setup logging (Tier 1)
    log_dir = LOGS_PATH / f"operation_{now()}"
    log_file = setup_context_logger(log_dir)
    log_operation_start(resume_name, input_file, log_file)

    # 3. Update registry to in-progress (Tier 2)
    update_resume_status(
        updates={resume_name: "operating"},
        source="context_name",
    )

    start_time = time.time()

    # 4. Call pure function (returns same result type)
    result = pure_operation(input_file, log_dir)

    elapsed = time.time() - start_time
    result.time_s = elapsed
    result.log_dir = log_dir

    # 5. Handle success vs failure
    if result.success:
        # Move/copy output to final location
        shutil.move(result.output_path, output_path)
        result.output_path = output_path  # Update to final location

        # Cleanup artifacts
        for file in log_dir.iterdir():
            if file.name != "context.log":
                file.unlink()

        extra_fields = {"output_path": str(output_path)}
        outcome = "operation_completed"
    else:
        # Keep artifacts for debugging
        extra_fields = {"error": result.error}
        outcome = "operation_failed"

    # 6. Update registry with outcome (Tier 2)
    update_resume_status(
        updates={resume_name: outcome},
        source="context_name",
        time_s=elapsed,
        **extra_fields,
    )

    # Log result (Tier 1)
    log_operation_result(resume_name, result, elapsed)

    return result
```

---

## CLI Script Pattern

CLI scripts are thin wrappers around orchestration functions. They handle:
- User input parsing
- Calling orchestration function
- Displaying results to terminal
- Exiting with appropriate code

### Resume Identifier Convention

All pipeline-relevant CLI commands take `resume_identifier: str` as the primary argument, **not file paths**.

```python
@app.command("operation")
def operation_command(
    resume_identifier: Annotated[
        str,
        typer.Argument(help="Resume identifier (must be registered)"),
    ],
    # ... other options
):
```

The CLI **never** resolves file paths - that's the orchestration function's job via `get_resume_file()`.

### CLI Command Template

```python
@app.command("operation")
def operation_command(
    resume_identifier: Annotated[
        str,
        typer.Argument(help="Resume identifier (must be registered)"),
    ],
    no_overwrite: Annotated[
        bool,
        typer.Option("--no-overwrite", help="Prevent overwriting existing output"),
    ] = False,
):
    """
    Perform operation on a resume.

    The resume must be registered and have appropriate status.

    Examples:\n

        $ python scripts/script.py operation Res202511

        $ python scripts/script.py operation Res202511 --no-overwrite
    """
    # Display header
    typer.secho(f"\nOperating: {resume_identifier}", fg=typer.colors.BLUE, bold=True)
    typer.echo("")

    # Call orchestration function (catches ValueError for pre-validation errors)
    try:
        result = orchestrate_operation(
            resume_name=resume_identifier,
            allow_overwrite=not no_overwrite,
        )
    except ValueError as e:
        typer.secho(f"Error: {e}\n", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # Display results
    typer.echo("")
    if result.success:
        typer.secho("✓ Operation succeeded", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"  Output: {display_path(result.output_path)}")
    else:
        typer.secho("✗ Operation failed", fg=typer.colors.RED, bold=True)
        if result.error:
            typer.echo(f"  Error: {result.error}")

    # Always show log location
    if result.log_dir:
        typer.echo(f"  Log: {display_path(result.log_dir / 'context.log')}")
    typer.echo("")

    # Exit with appropriate code
    raise typer.Exit(code=0 if result.success else 1)
```

### Terminal Output Conventions

**Header (before operation):**
```python
typer.secho(f"\nVerbing: {resume_identifier}", fg=typer.colors.BLUE, bold=True)
typer.echo("")
```

**Success:**
```python
typer.secho("✓ Operation succeeded", fg=typer.colors.GREEN, bold=True)
typer.echo(f"  Key: {value}")
```

**Failure:**
```python
typer.secho("✗ Operation failed", fg=typer.colors.RED, bold=True)
typer.echo(f"  Error: {result.error}")
```

**Details (indented with two spaces):**
```python
typer.echo(f"  Time: {result.time_s:.2f}s")
typer.echo(f"  Output: {display_path(result.output_path)}")
typer.echo(f"  Log: {display_path(result.log_dir / 'context.log')}")
```

**Path Display Helper:**
```python
def display_path(path: Path) -> str:
    """Return path relative to PROJECT_ROOT for cleaner display."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)
```

**Blank lines:**
- One blank line after header, before calling orchestration
- One blank line before result section
- One blank line before exit

**Exit codes:**
```python
raise typer.Exit(code=0 if result.success else 1)
```

### Typer Docstring Format

Format examples with single-line commands and inline comments:

```python
@app.command()
def operation(resume_identifier: str):
    """
    Perform operation on a resume.

    Description of what this does and any requirements.

    Examples:\n

        $ python scripts/script.py operation Res202511           # Basic usage

        $ python scripts/script.py operation Res202511 --verbose # With verbose output
    """
```

**Pattern:** `Examples:\n` (explicit newline) + blank line + single-line commands with inline `#` comments. This creates cleaner `--help` output.

---

## Two-Tier Logging

### Tier 1: Detailed Context Logs (loguru)

Each context has its own logger module at `archer/contexts/{context}/logger.py`:

```python
"""
Context-specific logger.

Provides logging interface with automatic [context] prefix.
"""
from archer.utils.logger import setup_logger as _setup_logger

CONTEXT_PREFIX = "[context]"

def setup_context_logger(log_dir: Path) -> Path:
    """Setup logger for this context."""
    return _setup_logger(
        context_name="context",
        log_dir=log_dir,
        extra_provenance={"Key": "value"},
    )

# Wrapper functions with automatic prefix
def _log_info(message: str) -> None:
    logger.info(f"{CONTEXT_PREFIX} {message}")

def _log_success(message: str) -> None:
    logger.success(f"{CONTEXT_PREFIX} {message}")

def _log_error(message: str) -> None:
    logger.error(f"{CONTEXT_PREFIX} {message}")

def _log_warning(message: str) -> None:
    logger.warning(f"{CONTEXT_PREFIX} {message}")

def _log_debug(message: str) -> None:
    logger.debug(f"{CONTEXT_PREFIX} {message}")

# High-level operation-specific helpers
def log_operation_start(resume_name: str, input_path: Path, log_file: Path) -> None:
    _log_info(f"Starting operation: {resume_name}")
    _log_info(f"Log file: {log_file}")
    _log_debug(f"Source: {input_path}")

def log_operation_result(resume_name: str, result, elapsed_time: float) -> None:
    if result.success:
        _log_success(f"{resume_name}: operation succeeded ({elapsed_time:.2f}s)")
    else:
        _log_error(f"{resume_name}: operation failed ({elapsed_time:.2f}s)")
```

**Log directory naming:** `outs/logs/{operation}_{timestamp}/`
- `parse_20251130_143022/`
- `compile_20251130_143025/`
- `validate_20251130_143030/`

**Log file naming:** `{context}.log`
- `template.log` for templating context
- `render.log` for rendering context

### Tier 2: Pipeline Events (registry)

Pipeline events track resume progression through the system:

```python
from archer.utils.resume_registry import update_resume_status

# Update status and log to pipeline events
update_resume_status(
    updates={resume_name: "new_status"},
    source="context_name",
    time_s=elapsed,
    output_path=str(output_path),
    # ... other metadata
)
```

See `docs/PIPELINE_EVENTS_REFERENCE.md` for event types and fields.

---

## Error Handling Summary

| Error Type | Where Caught | Logging | Registry Update |
|------------|--------------|---------|-----------------|
| Pre-validation (ValueError) | CLI script | None | None |
| Runtime error in pure function | Orchestration function | Tier 1 | Tier 2 (failed status) |
| Unexpected exception | Orchestration function | Tier 1 | Tier 2 (failed status) |

**Pre-validation errors** (raised before logging starts):
- Not registered
- Invalid type/status for operation
- File not found
- Output exists and overwrite not allowed

**Runtime errors** (caught after logging starts):
- Pure function failures
- File system errors
- Validation failures

---

## Alternative: Two-Layer Result Pattern

In some cases, the pure function returns a different type than the orchestration function, or additional processing creates a new result object. This is acceptable when the operation has complex intermediate steps (e.g., roundtrip validation that needs to wrap results).

```python
# Alternative pattern when pure function returns different type
try:
    intermediate = complex_validation(input_file, log_dir)
    result = OperationResult(
        success=intermediate["validation_passed"],
        error=intermediate["error"],
        yaml_diffs=intermediate["yaml_roundtrip"]["num_diffs"],
        # ... transform intermediate to result
    )
except Exception as e:
    result = OperationResult(success=False, error=str(e))
```

**Prefer the single-result pattern** (pure function returns same type, mutate on success) when possible. Use the two-layer pattern only when transformation or complex validation logic requires it.

---

## Reference Implementations

- **Templating:** `archer/contexts/templating/converter.py` - `parse_resume()`, `generate_resume()`
- **Rendering:** `archer/contexts/rendering/compiler.py` - `compile_resume()`
- **Rendering:** `archer/contexts/rendering/validator.py` - `validate_resume()`
- **CLI:** `scripts/convert_template.py` - `parse_command()`, `generate_command()`
- **CLI:** `scripts/compile_pdf.py` - `compile_command()`, `validate_command()`
