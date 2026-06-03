"""
config/settings.py
==================
Central config for the Indeed India scraper.
Change values here — no hunting through code.
"""

# --- Search parameters ---
SEARCH_QUERIES = [
    "machine learning engineer",
    "data scientist",
    "python developer",
    "AI engineer",
    "NLP engineer",
]

SEARCH_LOCATION = "India"          # Indeed India location string
MAX_FRESHNESS_DAYS = 14            # Jobs older than this are dropped immediately
MAX_PAGES_PER_QUERY = 5            # How many listing pages to scrape per query (10 jobs/page)
JOBS_PER_PAGE = 10                 # Indeed default

# --- Concurrency & rate limits ---
# "How many detail pages to fetch at once?"
# Keep this ≤ 3 to avoid triggering Indeed's anti-bot measures.
MAX_CONCURRENT_DETAIL_FETCHES = 2

# Wait range between requests (seconds) — random jitter avoids pattern detection
REQUEST_DELAY_MIN = 1.5
REQUEST_DELAY_MAX = 4.0

# --- Playwright browser settings ---
HEADLESS = False                    # Set False to watch the browser while debugging
BROWSER_TIMEOUT_MS = 30_000        # 30 seconds per page load
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# --- Output settings ---
OUTPUT_DIR = "output"
OUTPUT_FORMAT = "jsonl"            # jsonl = one JSON object per line → easy DB import

# --- Source tag (useful when you add Naukri, LinkedIn scrapers later) ---
SOURCE_NAME = "indeed_india"
INDEED_BASE_URL = "https://in.indeed.com"
