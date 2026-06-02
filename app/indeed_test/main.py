"""
main.py
=======
The entry point. Run this to start a full scrape.

Usage:
    python main.py

What it does:
    1. Loads search queries and location from config/settings.py
    2. Runs the Playwright scraper for each query
    3. Filters to only fresh jobs (≤ 14 days)
    4. Saves output to a JSONL file in the output/ directory

Logging:
    Set LOG_LEVEL=DEBUG in your env for verbose output, e.g.:
        LOG_LEVEL=DEBUG python main.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to Python path so imports work cleanly
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import SEARCH_QUERIES, SEARCH_LOCATION, OUTPUT_DIR
from scrapers.indeed_scraper import run_scraper
from storage.jsonl_writer import JSONLWriter


def configure_logging():
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


async def main():
    configure_logging()
    logger = logging.getLogger("main")

    logger.info("Starting Indeed India scraper")
    logger.info("Queries: %s", SEARCH_QUERIES)
    logger.info("Location: %s", SEARCH_LOCATION)

    # ── STEP 1: Scrape ────────────────────────────────────────────────
    jobs = await run_scraper(
        queries=SEARCH_QUERIES,
        location=SEARCH_LOCATION,
    )

    if not jobs:
        logger.warning("No fresh jobs collected. Check selectors or network.")
        return

    logger.info("Total fresh jobs collected: %d", len(jobs))

    # ── STEP 2: Print a quick summary ─────────────────────────────────
    logger.info("\n--- Sample jobs ---")
    for job in jobs[:3]:
        logger.info("  %s @ %s | %s | %s days ago",
                    job.title, job.company, job.location, job.posted_days_ago)

    # ── STEP 3: Save to JSONL ─────────────────────────────────────────
    writer = JSONLWriter(output_dir=OUTPUT_DIR)
    output_path = writer.save_jobs(jobs)

    if output_path:
        logger.info("Output saved to: %s", output_path)
        logger.info("To load jobs: python -c \"from storage.jsonl_writer import JSONLWriter; "
                    "jobs = JSONLWriter().load_jobs('%s'); print(len(jobs))\"", output_path)


if __name__ == "__main__":
    asyncio.run(main())
