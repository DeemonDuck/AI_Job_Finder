"""
models/job_posting.py
=====================
The JobPosting dataclass is the ONLY place that defines what a "job" looks like.
Every scraper fills this model. Every storage layer reads this model.

Benefits:
  - Add a new field here once, it propagates everywhere automatically
  - Easy to validate before saving
  - Maps cleanly to a DB table (each field = one column)
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import json


@dataclass
class JobPosting:
    # --- Core identifiers ---
    job_id: str                          # Unique key (extracted from Indeed URL)
    source: str = "indeed_india"         # Which scraper produced this

    # --- What you asked for ---
    title: str = ""                      # Job Title / Role
    company: str = ""                    # Company Name
    location: str = ""                   # Job Location
    job_url: str = ""                    # Full Indeed job URL
    description: str = ""               # Full Job Description text
    salary: Optional[str] = None        # Salary / Stipend — None if not listed
    posted_date_raw: str = ""           # Raw string from Indeed e.g. "3 days ago"
    posted_days_ago: Optional[int] = None  # Converted integer (0 = today, 14 = max)

    # --- Metadata ---
    scraped_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )

    # --- Optional enrichment (add later without breaking anything) ---
    employment_type: Optional[str] = None    # Full-time / Internship / Contract
    experience_required: Optional[str] = None
    skills_mentioned: list = field(default_factory=list)

    def is_fresh(self, max_days: int = 14) -> bool:
        """Returns True only if the job is within the freshness window."""
        if self.posted_days_ago is None:
            return False          # Unknown date → safer to drop it
        return self.posted_days_ago <= max_days

    def to_dict(self) -> dict:
        """Convert to plain dict — used before writing to JSONL or inserting to DB."""
        return asdict(self)

    def to_json(self) -> str:
        """Single-line JSON string — one line in the JSONL output file."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def __repr__(self):
        return (
            f"JobPosting(id={self.job_id!r}, title={self.title!r}, "
            f"company={self.company!r}, days_ago={self.posted_days_ago})"
        )
