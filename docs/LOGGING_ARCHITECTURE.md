# ARCHER Logging Architecture

**Authoritative reference for ARCHER's two-tiered logging system.**

This document explains how logging works in ARCHER and how to implement it in new contexts.

---

## Overview: Two-Tier Logging

ARCHER uses two independent logging systems with different purposes:

| Tier | Purpose | Format | Location | When to Use |
|------|---------|--------|----------|-------------|
| **Tier 1** | Detailed execution logs | Loguru text | `outs/logs/{context}_TIMESTAMP/` | Within-context debugging |
| **Tier 2** | Pipeline coordination | JSON Lines | `outs/logs/resume_pipeline_events.log` | Cross-context state tracking |

**Key principle**: Tier 1 answers "what happened during this operation?" while Tier 2 answers "where is this resume in the pipeline?"

---

## Tier 1: Detailed Logging with Loguru

### Purpose

Capture detailed execution traces for debugging within a single context. Includes provenance (script, command, working directory), debug messages, errors, and full diagnostic output.

### Characteristics

- **Format**: Human-readable text with timestamps
- **Library**: Loguru (automatic timestamps, levels, colors)
- **Location**: Timestamped directories (`outs/logs/render_20251114_123456/render.log`)
- **Lifetime**: Permanent (one directory per session)
- **Scope**: Single context, single execution
- **Audience**: Developers debugging issues

### Example Log

```
2025-11-14 12:34:56 | INFO    | ================================================================================
2025-11-14 12:34:56 | INFO    | Script: scripts/render_resume.py
2025-11-14 12:34:56 | INFO    | Command: python scripts/render_resume.py resume.tex
2025-11-14 12:34:56 | INFO    | Working directory: /home/sean/ARCHER
2025-11-14 12:34:56 | INFO    | Python: 3.10.12
2025-11-14 12:34:56 | INFO    | LaTeX compiler: pdflatex
2025-11-14 12:34:56 | INFO    | ================================================================================
2025-11-14 12:34:56 | INFO    | [render] Starting compilation: Res202511_Role_CompanyA
2025-11-14 12:34:56 | DEBUG   | [render]   Source: /path/to/resume.tex
2025-11-14 12:34:56 | DEBUG   | [render]   Passes: 2
2025-11-14 12:34:59 | SUCCESS | [render] Compilation succeeded.
2025-11-14 12:34:59 | SUCCESS | [render] Res202511_Role_CompanyA: 3 warnings (3.2s)
```

### When to Use Tier 1

✅ **Use for:**
- Complex operations needing debug traces
- Operations with multiple steps
- Capturing stdout/stderr from external tools
- Provenance tracking (reproducibility)

❌ **Don't use for:**
- Simple single-step operations
- Cross-context coordination
- Analytics/monitoring

---

## Tier 2: Pipeline Event Logging (JSON Lines)

### Purpose

Track resume state transitions across the pipeline. Provides audit trail and enables cross-context coordination.

### Characteristics

- **Format**: JSON Lines (one event per line)
- **Library**: None (plain JSON)
- **Location**: Single master file (`outs/logs/resume_pipeline_events.log`)
- **Lifetime**: Append-only, archived periodically
- **Scope**: Entire pipeline, all contexts, all resumes
- **Audience**: System monitoring, analytics, orchestration

### Example Events

```json
{"timestamp": "2025-11-14T12:34:56.123456", "event_type": "registration", "resume_name": "Res202511", "source": "cli", "resume_type": "historical", "status": "parsed"}
{"timestamp": "2025-11-14T12:35:10.789012", "event_type": "status_change", "resume_name": "Res202511", "source": "rendering", "old_status": "templating_completed", "new_status": "rendering", "compilation_time_s": 3.2}
{"timestamp": "2025-11-14T12:35:14.345678", "event_type": "status_change", "resume_name": "Res202511", "source": "rendering", "old_status": "rendering", "new_status": "rendering_completed", "warning_count": 3}
```

### When to Use Tier 2

✅ **Use for:**
- All registry mutations (status changes, registrations)
- State transitions between contexts
- Lightweight coordination events
- Analytics data

❌ **Don't use for:**
- Verbose debug output
- Multi-line logs
- Human-readable diagnostics

---

## Architecture

### Module Organization

```
archer/
├── utils/
│   ├── event_logging.py      # Tier 2: Pipeline events (JSON Lines)
│   └── logger.py              # Tier 1: Generic loguru setup
└── contexts/
    ├── rendering/
    │   └── logger.py          # Tier 1: Rendering wrapper ([render] prefix)
    ├── templating/
    │   └── logger.py          # Tier 1: Templating wrapper ([template] prefix)
    └── targeting/
        └── logger.py          # Tier 1: Targeting wrapper ([target] prefix)
```

### Design Pattern

**Generic utilities** (`utils/logger.py`, `utils/event_logging.py`):
- Reusable across all contexts
- No context-specific knowledge
- Pure infrastructure

**Context wrappers** (`contexts/{context}/logger.py`):
- Wrap generic utilities with context-specific defaults
- Add automatic context prefix (e.g., `[render]`)
- Provide high-level logging helpers
- Context modules import from here, never from utils directly

---

## Implementation Guide

### Adding Logging to a New Context

Follow this pattern (see `contexts/rendering/logger.py` as reference):

#### 1. Create Context Logger Wrapper

```python
# contexts/templating/logger.py

import os
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv
from archer.utils.logger import setup_logger as _setup_logger

load_dotenv()

CONTEXT_PREFIX = "[template]"

def setup_templating_logger(log_dir: Path) -> Path:
    """Setup logger for templating context."""
    return _setup_logger(
        context_name="template",
        log_dir=log_dir,
        extra_provenance={
            "Config path": os.getenv("TEMPLATING_CONTEXT_PATH")
            # Add any context-specific provenance
        }
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

# High-level context-specific helpers
def log_parsing_start(resume_name: str, tex_file: Path) -> None:
    """Log start of parsing."""
    _log_info(f"Starting parse: {resume_name}")
    _log_debug(f"  Source: {tex_file}")
```

#### 2. Use in Context Modules

Varies with use case. See `archer/contexts/templating/parser.py` for example.

---

## Provenance Tracking

Every Tier 1 log session automatically includes a provenance header:

```
Script: scripts/render_resume.py
Command: python scripts/render_resume.py --batch resume1.tex resume2.tex
Working directory: /home/sean/ARCHER
Python: 3.10.12
LaTeX compiler: pdflatex  # Context-specific (from extra_provenance)
```

**Why provenance matters:**
- Enables reproducibility (know exactly how to re-run)
- Debugging aid (environment context)
- Audit trail (who ran what, when, where)

---

## Registry Integration

The resume registry (`outs/logs/resume_registry.csv`) automatically logs all mutations to Tier 2:

```python
from archer.utils.resume_registry import update_resume_status

# This AUTOMATICALLY logs to resume_pipeline_events.log
update_resume_status(
    updates={"Res202511": "rendering_completed"},
    source="rendering",
    compilation_time_s=3.2  # Extra fields go into event
)
```

**Event produced:**
```json
{
  "timestamp": "2025-11-14T12:35:14.345678",
  "event_type": "status_change",
  "resume_name": "Res202511",
  "source": "rendering",
  "old_status": "rendering",
  "new_status": "rendering_completed",
  "compilation_time_s": 3.2
}
```

---

## Log Output Locations

### Tier 1 (Detailed Logs)

```
outs/logs/
├── render_20251114_123456/
│   ├── render.log                    # Loguru output with provenance
│   ├── Res202511_Role_CompanyA/       # Resume-specific artifacts
│   │   ├── resume.tex
│   │   ├── resume.log                # pdflatex raw output
│   │   └── resume.pdf
│   └── Res202512_Position_CompanyB/
│       └── ...
└── template_20251114_134521/
    └── template.log
```

### Tier 2 (Pipeline Events)

```
outs/logs/
└── resume_pipeline_events.log        # Append-only JSON Lines
```

---

## Viewing Logs

### Tier 1 (Detailed)

```bash
# View specific session log
less outs/logs/render_20251114_123456/render.log

# Search across sessions
grep "ERROR" outs/logs/render_*/render.log
```

### Tier 2 (Pipeline Events)

```bash
# Last 10 events
make logs

# Last 10 events for specific resume
make logs RESUME=Res202511

# Status history timeline
make track RESUME=Res202511

# Raw access
tail -n 20 outs/logs/resume_pipeline_events.log | jq
```

---

## Design Decisions

### Why Two Tiers?

**Single tier insufficient:**
- Detailed logs are too verbose for analytics
- Event logs lack debugging detail

**Separation of concerns:**
- Debugging requires detail + provenance
- Monitoring requires lightweight state tracking
- Different audiences, different formats

### Why Context Wrappers?

**Benefits:**
- Generic utils stay reusable
- Automatic prefixes prevent mistakes
- Easy pattern to copy
- Context modules isolated from infrastructure

**Pattern ensures:**
- `[render]` prefix automatic in rendering context
- `[template]` prefix automatic in templating context
- Consistent format across all contexts

---

## Reference Files

**Implemented:**
- `archer/utils/event_logging.py` - Tier 2 event logging
- `archer/utils/logger.py` - Tier 1 generic setup
- `archer/contexts/rendering/logger.py` - Example context wrapper
- `docs/RESUME_STATUS_REFERENCE.md` - Status definitions
- `docs/PIPELINE_EVENTS_REFERENCE.md` - Event schema
- `scripts/tail_log.py` - Shows how to read Tier 2 events

---

## Quick Reference

**Need to log detailed execution?** → Tier 1 (loguru)
**Need to track pipeline state?** → Tier 2 (events) - usually automatic via registry

**Starting a new context?** → Copy `contexts/rendering/logger.py` pattern

**Debugging?** → Check `outs/logs/{context}_TIMESTAMP/{context}.log`

**Monitoring pipeline?** → Use `make logs` or `make track RESUME=...`
