"""
tests/test_date_parser.py
==========================
Run with: python -m pytest tests/ -v

These tests require no browser — they validate pure Python logic.
Good practice: write these before the scraper so you can verify your
date parsing logic independently of network calls.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.indeed_test.utils.date_parser import parse_days_ago, is_within_freshness_window
from app.indeed_test.utils.url_builder import build_search_url, extract_job_id_from_url


class TestDateParser:
    def test_just_posted(self):
        assert parse_days_ago("Just posted") == 0

    def test_today(self):
        assert parse_days_ago("Today") == 0
        assert parse_days_ago("today") == 0

    def test_one_day_ago(self):
        assert parse_days_ago("1 day ago") == 1

    def test_multiple_days_ago(self):
        assert parse_days_ago("3 days ago") == 3
        assert parse_days_ago("14 days ago") == 14

    def test_thirty_plus(self):
        result = parse_days_ago("30+ days ago")
        assert result > 14, "30+ days should be above the 14-day threshold"

    def test_with_prefix(self):
        # Indeed sometimes says "Active 2 days ago"
        assert parse_days_ago("Active 2 days ago") == 2

    def test_hours_ago_treated_as_today(self):
        assert parse_days_ago("1 hour ago") == 0
        assert parse_days_ago("3 hours ago") == 0

    def test_empty_string(self):
        assert parse_days_ago("") is None

    def test_freshness_window_fresh(self):
        is_fresh, days = is_within_freshness_window("5 days ago", max_days=14)
        assert is_fresh is True
        assert days == 5

    def test_freshness_window_stale(self):
        is_fresh, days = is_within_freshness_window("20 days ago", max_days=14)
        assert is_fresh is False
        assert days == 20

    def test_freshness_boundary(self):
        # Exactly 14 days → should be accepted
        is_fresh, days = is_within_freshness_window("14 days ago", max_days=14)
        assert is_fresh is True
        assert days == 14

    def test_freshness_just_over_boundary(self):
        is_fresh, days = is_within_freshness_window("15 days ago", max_days=14)
        assert is_fresh is False


class TestURLBuilder:
    def test_basic_url(self):
        url = build_search_url("python developer", "India", page=1)
        assert "in.indeed.com" in url
        assert "python+developer" in url or "python%20developer" in url
        assert "fromage=14" in url
        assert "start=0" in url

    def test_pagination_offset(self):
        url_page2 = build_search_url("data scientist", "India", page=2)
        assert "start=10" in url_page2

        url_page3 = build_search_url("data scientist", "India", page=3)
        assert "start=20" in url_page3

    def test_extract_job_id_from_viewjob_url(self):
        url = "https://in.indeed.com/viewjob?jk=abc123def456&from=serp"
        assert extract_job_id_from_url(url) == "abc123def456"

    def test_extract_job_id_from_redirect_url(self):
        url = "https://in.indeed.com/rc/clk?jk=xyz789&q=python&l=India"
        assert extract_job_id_from_url(url) == "xyz789"

    def test_fallback_for_unknown_url(self):
        url = "https://in.indeed.com/some/other/path"
        result = extract_job_id_from_url(url)
        assert isinstance(result, str)
        assert len(result) > 0


if __name__ == "__main__":
    # Run without pytest: python tests/test_date_parser.py
    import traceback

    test_classes = [TestDateParser, TestURLBuilder]
    passed = 0
    failed = 0

    for cls in test_classes:
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        for method_name in methods:
            try:
                getattr(instance, method_name)()
                print(f"  ✓ {cls.__name__}.{method_name}")
                passed += 1
            except AssertionError as e:
                print(f"  ✗ {cls.__name__}.{method_name}: {e}")
                failed += 1
            except Exception as e:
                print(f"  ✗ {cls.__name__}.{method_name}: EXCEPTION: {e}")
                traceback.print_exc()
                failed += 1

    print(f"\n{passed} passed, {failed} failed")
