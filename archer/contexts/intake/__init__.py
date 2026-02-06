"""
Intake Context

Responsibilities:
- Job description ingestion and parsing
- Normalization into internal structured representation
- Section identification and categorization

Never:
- Makes targeting decisions (which resume content to select)
- Scores resume-job match (that's targeting's job)
- Modifies templates (that's templating's job)

Public API:
- JobListing: Main data structure (use .from_text() or .from_file() to create)
- ParsedJobData: Intermediate parsed data (for advanced use cases)
"""

from archer.contexts.intake.job_data_structure import JobListing
from archer.contexts.intake.job_parser import ParsedJobData, parse_job_text

__all__ = [
    # Primary API
    "JobListing",
    # Intermediate data (advanced use)
    "ParsedJobData",
    "parse_job_text",
]
