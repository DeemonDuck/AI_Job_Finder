"""
storage/jsonl_writer.py
=======================
Saves JobPosting objects to a JSONL file (JSON Lines format).

Why JSONL over plain JSON?
  - Each line is one complete JSON object → easy to read line-by-line
  - You can append new jobs without loading the entire file
  - Trivially importable into PostgreSQL, MongoDB, BigQuery, etc.
  - Readable in a text editor line-by-line

Future: When you're ready for a real DB, create storage/postgres_writer.py
with the same interface (save_jobs method), and swap it in main.py.
You can also use an ORM like SQLAlchemy — the JobPosting.to_dict() method
makes mapping to a DB model straightforward.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from app.indeed_test.models.job_posting import JobPosting

logger = logging.getLogger(__name__)


class JSONLWriter:
    """Writes JobPosting objects to a JSONL file."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self) -> Path:
        """
        Auto-generate a timestamped filename so each run has its own file.
        Example: output/indeed_india_2024-05-15_14-30.jsonl
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
        return self.output_dir / f"indeed_india_{timestamp}.jsonl"

    def save_jobs(self, jobs: list[JobPosting], filepath: str | Path | None = None) -> Path:
        """
        Save a list of JobPosting objects to a JSONL file.

        Args:
            jobs:     List of JobPosting objects to save
            filepath: Optional explicit path. If None, auto-generates a timestamped name.

        Returns:
            Path to the file that was written.
        """
        if not jobs:
            logger.warning("No jobs to save.")
            return None

        output_path = Path(filepath) if filepath else self._generate_filename()

        with open(output_path, "w", encoding="utf-8") as f:
            for job in jobs:
                f.write(job.to_json() + "\n")

        logger.info("Saved %d jobs to %s", len(jobs), output_path)
        return output_path

    def load_jobs(self, filepath: str | Path) -> list[JobPosting]:
        """
        Load jobs back from a JSONL file. Useful for testing and reprocessing.
        """
        jobs = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    # Reconstruct JobPosting from dict
                    jobs.append(JobPosting(**{
                        k: v for k, v in data.items()
                        if k in JobPosting.__dataclass_fields__
                    }))
        return jobs


# ─────────────────────────────────────────────────────────────────────
# Future DB adapter template — implement this when you add a database
# ─────────────────────────────────────────────────────────────────────

class BaseStorageAdapter:
    """
    Interface that all storage adapters should implement.
    Swap implementations in main.py without changing scraper code.
    """
    def save_jobs(self, jobs: list[JobPosting]) -> None:
        raise NotImplementedError

    def job_exists(self, job_id: str) -> bool:
        """Check if a job_id already exists — useful for incremental runs."""
        raise NotImplementedError


# class PostgresAdapter(BaseStorageAdapter):
#     """Uncomment and fill in when you add PostgreSQL."""
#     def __init__(self, dsn: str):
#         import psycopg2
#         self.conn = psycopg2.connect(dsn)
#
#     def save_jobs(self, jobs: list[JobPosting]) -> None:
#         with self.conn.cursor() as cur:
#             for job in jobs:
#                 cur.execute("""
#                     INSERT INTO job_postings (job_id, source, title, company, ...)
#                     VALUES (%s, %s, %s, %s, ...)
#                     ON CONFLICT (job_id) DO NOTHING
#                 """, (job.job_id, job.source, job.title, job.company, ...))
#         self.conn.commit()
