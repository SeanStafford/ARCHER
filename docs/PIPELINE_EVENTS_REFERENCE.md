# Pipeline Events Reference

**Authoritative documentation for pipeline event types.**

All pipeline events are logged to `outs/logs/resume_pipeline_events.log` in JSON Lines format. Each event includes standard fields (`timestamp`, `event_type`, `resume_name`, `source`) plus event-specific fields.

---

## Standard Event Fields

Every event logged to `resume_pipeline_events.log` contains these fields:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `timestamp` | str (ISO 8601) | When the event occurred | `"2025-11-13T18:27:45.123456"` |
| `event_type` | str | Type of event (see below) | `"status_change"` |
| `resume_name` | str | Resume identifier | `"Res202511"` |
| `source` | str | What generated the event | `"cli"`, `"templating"` |

---

## Event Types

### `registration`

**When**: Resume is registered in the registry for the first time

**Produced by**: `register_resume()` in `archer/utils/resume_registry.py`

**Standard fields**: Yes

**Additional fields**:
- `resume_type` (str): Must be `"historical"` or `"generated"`
- `status` (str)

**Example**:
```json
{
  "timestamp": "2025-11-13T18:27:45.123456",
  "event_type": "registration",
  "resume_name": "Res202507",
  "source": "cli",
  "resume_type": "historical",
  "status": "parsed"
}
```

---

### `status_change`

**When**: Resume status transitions from one state to another

**Produced by**: `update_resume_status()` in `archer/utils/resume_registry.py`

**Standard fields**: Yes

**Additional fields**:
- `old_status` (str): Previous status
- `new_status` (str): New status (see `docs/RESUME_STATUS_REFERENCE.md`)
- `**extra` (any): Context-specific fields passed by caller

**Example**:
```json
{
  "timestamp": "2025-11-13T18:30:12.789012",
  "event_type": "status_change",
  "resume_name": "Res202510",
  "source": "templating",
  "old_status": "normalized",
  "new_status": "parsed",
  "processing_time_s": 1.2
}
```

**Common extra fields by source**:

**From rendering context**:
- `compilation_time_s` (float): Time to compile PDF
- `error_count` (int): Number of LaTeX errors
- `warning_count` (int): Number of LaTeX warnings

**From templating context**:
- `processing_time_s` (float): Time to parse/generate
- `error_message` (str): Error description (if failed)

**From manual updates**:
- `reason` (str): Why status was manually changed

---


## Source Values

Standard sources that produce events:

| Source | Description | Used By |
|--------|-------------|---------|
| `"cli"` | Command-line script execution | `manage_registry.py` |
| `"templating"` | Templating context operations | LaTeX parsing, YAML generation |
| `"targeting"` | Targeting context operations | Content selection, resume analysis |
| `"rendering"` | Rendering context operations | PDF compilation |
| `"manual"` | Manual user intervention | CLI update command with `--reason` |
| `"system"` | Automated system tasks | Scheduled jobs, maintenance scripts |

---

## Adding New Event Types

When adding a new event type:

1. **Document here first** - Add to this file before implementing
2. **Follow naming convention** - Use `snake_case`, past tense for completion events (`_completed`)
3. **Include standard fields** - Always log `timestamp`, `event_type`, `resume_name`, `source`
4. **Document extra fields** - List all additional fields with types and descriptions
5. **Provide example** - Include a complete JSON example

---

