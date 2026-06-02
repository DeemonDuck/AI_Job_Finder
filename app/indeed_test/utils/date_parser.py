"""
utils/date_parser.py
====================
Indeed uses human-friendly relative dates like:
  "Just posted", "Today", "1 day ago", "3 days ago", "30+ days ago"

This module converts ALL of those to an integer (days_ago).
The freshness filter in the scraper uses this integer to drop stale jobs EARLY.

Why early filtering matters:
  - Indeed listing pages show ~10 jobs each
  - If page 1 already has jobs > 14 days old, no need to fetch page 2 at all
  - Each detail page fetch = 1 network request + ~2s wait, so skipping them saves real time
"""

import re
import logging

logger = logging.getLogger(__name__)


def parse_days_ago(raw_text: str) -> int | None:
    """
    Convert Indeed's relative date string into an integer number of days.

    Args:
        raw_text: Raw date string from Indeed, e.g. "3 days ago", "Just posted"

    Returns:
        Integer days (0 = today, 14 = two weeks), or None if unparseable.

    Examples:
        >>> parse_days_ago("Just posted")   -> 0
        >>> parse_days_ago("Today")         -> 0
        >>> parse_days_ago("1 day ago")     -> 1
        >>> parse_days_ago("3 days ago")    -> 3
        >>> parse_days_ago("30+ days ago")  -> 31   (above our 14-day max, will be dropped)
        >>> parse_days_ago("Active 2 days ago") -> 2
    """
    if not raw_text:
        return None

    text = raw_text.lower().strip()

    # "Just posted" or "Today" → 0 days ago
    if any(phrase in text for phrase in ["just posted", "today", "just now"]):
        return 0

    # "30+ days ago" → treat as 31 (above the 14-day threshold, will be filtered out)
    if "30+" in text or "30 +" in text:
        return 31

    # Extract the first integer found: "3 days ago" → 3, "Active 2 days ago" → 2
    match = re.search(r"(\d+)", text)
    if match:
        days = int(match.group(1))
        # Sanity check: Indeed occasionally shows "1 hour ago" → treat as 0
        if "hour" in text or "minute" in text:
            return 0
        return days

    # Could not parse — log it so you can improve this function over time
    logger.warning("Could not parse date string: %r", raw_text)
    return None


def is_within_freshness_window(raw_text: str, max_days: int = 14) -> tuple[bool, int | None]:
    """
    Convenience wrapper used by the freshness filter.

    Returns:
        (is_fresh: bool, days_ago: int | None)

    Usage in scraper:
        fresh, days = is_within_freshness_window(card_date_text, max_days=14)
        if not fresh:
            break  # Stop paginating — no point fetching more pages
    """
    days_ago = parse_days_ago(raw_text)
    if days_ago is None:
        return False, None
    return days_ago <= max_days, days_ago
