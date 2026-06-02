"""
utils/url_builder.py
====================
Answers your Q2: Use pre-generated search URLs, NOT Playwright search box interaction.

Reason: The `fromage=14` parameter in Indeed's URL tells the server to only return
jobs from the last 14 days. This means:
  - Less data to download in the first place
  - Faster scraping (fewer pages to process)
  - More reliable than typing in a search box with Playwright (UI can change)

Indeed's URL structure for India:
  https://in.indeed.com/jobs?q=<role>&l=<location>&fromage=<days>&start=<offset>

  q        = search query (URL-encoded)
  l        = location string (e.g. "India", "Bangalore", "Remote")
  fromage  = "from age" — max age of results in days (14 = last 2 weeks)
  start    = pagination offset (0 = page 1, 10 = page 2, 20 = page 3...)
"""

from urllib.parse import urlencode, quote_plus
from app.indeed_test.config.settings import INDEED_BASE_URL, MAX_FRESHNESS_DAYS


def build_search_url(query: str, location: str, page: int = 1, max_days: int = MAX_FRESHNESS_DAYS) -> str:
    """
    Build a fully-formed Indeed India search URL.

    Args:
        query:    Job role to search for, e.g. "machine learning engineer"
        location: Location string, e.g. "India" or "Bangalore"
        page:     Page number (1-indexed)
        max_days: Maximum job age in days — baked into the URL as fromage=N

    Returns:
        Full URL string ready to navigate to.

    Example:
        >>> build_search_url("data scientist", "India", page=2)
        "https://in.indeed.com/jobs?q=data+scientist&l=India&fromage=14&start=10"
    """
    params = {
        "q": query,
        "l": location,
        "fromage": max_days,
        "start": (page - 1) * 10,  # Indeed uses offset=0,10,20... for pagination
    }
    return f"{INDEED_BASE_URL}/jobs?{urlencode(params)}"


def extract_job_id_from_url(url: str) -> str:
    """
    Extract a stable unique ID from an Indeed job URL.

    Indeed job URLs look like:
      https://in.indeed.com/viewjob?jk=abc123def456
      or
      https://in.indeed.com/rc/clk?jk=abc123def456&...

    We extract the `jk` parameter as the unique job ID.
    This is important because the same job can appear in multiple search results.
    Using jk as the ID lets us deduplicate before hitting the database.

    Args:
        url: Any Indeed job-related URL

    Returns:
        The jk value, or the full URL if jk not found (fallback)
    """
    from urllib.parse import urlparse, parse_qs

    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    if "jk" in params:
        return params["jk"][0]

    # Fallback: use a hash of the URL as the ID
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()[:16]


def build_job_detail_url(job_id: str) -> str:
    """Build the canonical detail page URL from a job ID."""
    return f"{INDEED_BASE_URL}/viewjob?jk={job_id}"
