"""
scrapers/indeed_scraper.py
===========================
This is the main scraper. It answers all 5 of your questions:

Q1 → USE PLAYWRIGHT
   Indeed is JavaScript-heavy. Requests+BS4 often gets empty pages because
   the job cards are rendered by JS after the initial HTML loads.
   Playwright waits for the DOM to settle before parsing.

   The JSON/API approach (looking for hidden API calls in DevTools) IS the most
   reliable, but Indeed India does not have a stable public API and the internal
   XHR endpoints change frequently and are protected by tokens.
   Playwright is the best balance of reliability vs maintenance.

Q2 → USE PRE-BUILT SEARCH URLS (not Playwright search box interaction)
   See url_builder.py for the reasoning. Short answer: the `fromage=14`
   URL param does the freshness filtering at the server level before we
   even download a single page.

Q3 → ASYNC BATCH FETCHING WITH CONCURRENCY LIMIT
   Fetching detail pages one-by-one is slow. We use asyncio.Semaphore to
   fetch N pages at once (default 3) without triggering rate limits.
   Each fetch also has a random delay (jitter) to look human.

Q4 → SELECTOR ABSTRACTION LAYER (selectors dict)
   All CSS selectors live in one dictionary at the top of this file.
   When Indeed changes its HTML structure, you update ONE dict, not 20 lines.
   This is the key to maintainability.

Q5 → PROJECT STRUCTURE
   This scraper is one module inside a larger package.
   The main.py at the root orchestrates everything.
   Adding a Naukri scraper later = create scrapers/naukri_scraper.py with the
   same interface (run() → list[JobPosting]).
"""

import asyncio
import logging
import random
from datetime import datetime

from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PWTimeout

from config.settings import (
    HEADLESS, BROWSER_TIMEOUT_MS, USER_AGENT,
    REQUEST_DELAY_MIN, REQUEST_DELAY_MAX,
    MAX_CONCURRENT_DETAIL_FETCHES, MAX_FRESHNESS_DAYS,
    MAX_PAGES_PER_QUERY, SOURCE_NAME, INDEED_BASE_URL
)
from models.job_posting import JobPosting
from utils.date_parser import is_within_freshness_window
from utils.url_builder import build_search_url, extract_job_id_from_url

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# SELECTOR MAP — update this when Indeed changes its HTML
# This is the answer to Q4: maintainability through abstraction.
# ─────────────────────────────────────────────
SELECTORS = {
    # A single job card on the listing page
    "job_card": "div.job_seen_beacon",

    # Fields inside a job card (relative to the card element)
    "card_title":    "h2.jobTitle span[title]",
    "card_company":  "span.companyName",
    "card_location": "div.companyLocation",
    "card_date":     "span.date",
    "card_salary":   "div.metadata.salary-snippet-container span",
    "card_link":     "h2.jobTitle a",

    # Fields on the job detail page
    "detail_description":      "div#jobDescriptionText",
    "detail_salary":           "div#salaryInfoAndJobType span",
    "detail_employment_type":  "div#jobDetailsSection span.attribute_snippet",

    # "No results" indicator — used to stop pagination early
    "no_results": "div.jobsearch-NoResult-messageContainer",
}

# Phrases that indicate a bot/captcha/verification page
BLOCK_PHRASES = [
    "just a moment",
    "access denied",
    "captcha",
    "verify",
    "additional verification",
    "blocked",
]

# Fallback selector chain — tried in order when the primary selector fails.
# Indeed renames CSS classes after redesigns. data-testid is most stable
# because Indeed uses it in their own test suite and rarely removes it.
CARD_SELECTOR_FALLBACKS = [
    "div.job_seen_beacon",
    "div[class*='job_seen_beacon']",
    "li.css-1ac2h1w",
    "div[data-testid='slider_item']",
    "div.resultContent",
]


async def _random_delay():
    """Sleep for a random duration to mimic human browsing pace."""
    await asyncio.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))


async def _setup_browser(playwright) -> Browser:
    """
    Launch a Chromium browser with stealth settings.
    These settings reduce the chance of Indeed detecting us as a bot.
    """
    browser = await playwright.chromium.launch(
        headless=HEADLESS,
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
        ]
    )
    return browser


async def _new_stealth_page(browser: Browser) -> Page:
    """
    Create a new browser page with a realistic user agent and extra
    JavaScript patches to hide Playwright's fingerprint.
    """
    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1280, "height": 800},
        locale="en-IN",
        timezone_id="Asia/Kolkata",
    )

    # Remove the webdriver property that sites use to detect automation
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)

    page = await context.new_page()
    page.set_default_timeout(BROWSER_TIMEOUT_MS)
    return page


async def _handle_verification(page: Page) -> bool:
    """
    Check if the current page is a bot/captcha/verification page.
    If yes, pause and wait for the human to solve it.

    Returns:
        True  → page is clean, scraper can continue
        False → still blocked after human attempted to solve it
    """
    title = await page.title()
    logger.info("Page title: %r", title)

    if not any(phrase in title.lower() for phrase in BLOCK_PHRASES):
        return True  # No verification needed, all good

    # Verification detected — prompt the human
    print("\n" + "=" * 55)
    print("  HUMAN VERIFICATION REQUIRED")
    print("  Please solve the verification in the browser window.")
    print("  Once the jobs page loads normally, come back here")
    print("  and press Enter to continue...")
    print("=" * 55 + "\n")

    # run_in_executor prevents input() from blocking the async event loop
    await asyncio.get_event_loop().run_in_executor(
        None, input, "  >>> Press Enter when done: "
    )

    # Re-check title after human solved it
    title = await page.title()
    if any(phrase in title.lower() for phrase in BLOCK_PHRASES):
        logger.error("Verification still not solved. Skipping this page.")
        return False

    logger.info("Verification solved! Resuming scraper...")
    return True


async def _parse_listing_page(page: Page, url: str) -> tuple[list[dict], bool]:
    """
    Navigate to a search results page and extract job cards directly from
    Indeed's embedded JSON blob (window.mosaic.providerData).

    This avoids all CSS selector fragility for listing-page data — the JSON
    blob contains formattedRelativeTime, title, company, location, salary,
    jobkey, and link for every card on the page.

    Returns:
        (cards: list of raw card dicts, should_continue: bool)
    """
    logger.info("Fetching listing page: %s", url)

    try:
        await page.goto(url, wait_until="networkidle", timeout=BROWSER_TIMEOUT_MS)
    except PWTimeout:
        logger.error("Timeout loading listing page: %s", url)
        return [], False

    page_clean = await _handle_verification(page)
    if not page_clean:
        return [], False

    await _random_delay()

    if await page.query_selector(SELECTORS["no_results"]):
        logger.info("No results found on this page — stopping pagination")
        return [], False

    # ── Pull job data directly from Indeed's embedded JSON ────────────
    results = await page.evaluate("""
        () => {
            try {
                const data = window.mosaic.providerData["mosaic-provider-jobcards"];
                return data.metaData.mosaicProviderJobCardsModel.results;
            } catch(e) {
                return null;
            }
        }
    """)

    if not results:
        logger.warning("Could not extract JSON blob from page — mosaic data unavailable")
        return [], False

    logger.info("Found %d cards in JSON blob", len(results))

    cards_raw = []
    should_continue = True

    for job in results:
        try:
            date_raw = job.get("formattedRelativeTime", "")
            is_fresh, days_ago = is_within_freshness_window(date_raw, MAX_FRESHNESS_DAYS)

            if not is_fresh:
                logger.info("Found job with age %r (%s days) — stopping pagination", date_raw, days_ago)
                should_continue = False
                break

            job_id  = job.get("jobkey", "")
            title   = job.get("displayTitle") or job.get("title", "")
            company = job.get("company", "")
            loc     = job.get("formattedLocation", "")
            href    = job.get("link", "")
            salary  = job.get("salarySnippet", {}).get("text") or None

            full_url = href if href.startswith("http") else f"{INDEED_BASE_URL}{href}"

            cards_raw.append({
                "job_id":          job_id,
                "title":           title.strip(),
                "company":         company.strip(),
                "location":        loc.strip(),
                "job_url":         full_url,
                "salary":          salary,
                "posted_date_raw": date_raw,
                "posted_days_ago": days_ago,
            })

        except Exception as e:
            logger.warning("Error parsing card from JSON: %s", e)
            continue

    return cards_raw, should_continue


async def _fetch_job_description(page: Page, job_url: str) -> dict:
    """
    Navigate to a single job detail page and extract the full description.

    Returns:
        dict with 'description', 'salary' (if found on detail page),
        and 'employment_type'
    """
    try:
        await page.goto(job_url, wait_until="domcontentloaded")
        await _random_delay()

        desc_el   = await page.query_selector(SELECTORS["detail_description"])
        salary_el = await page.query_selector(SELECTORS["detail_salary"])
        type_el   = await page.query_selector(SELECTORS["detail_employment_type"])

        description     = (await desc_el.inner_text()).strip() if desc_el else ""
        detail_salary   = (await salary_el.inner_text()).strip() if salary_el else None
        employment_type = (await type_el.inner_text()).strip() if type_el else None

        return {
            "description":     description,
            "salary_detail":   detail_salary,
            "employment_type": employment_type,
        }
    except PWTimeout:
        logger.warning("Timeout fetching detail page: %s", job_url)
        return {"description": "", "salary_detail": None, "employment_type": None}
    except Exception as e:
        logger.warning("Error fetching detail %s: %s", job_url, e)
        return {"description": "", "salary_detail": None, "employment_type": None}


async def _fetch_all_details(browser: Browser, cards: list[dict]) -> list[JobPosting]:
    """
    Fetch detail pages for all cards using a Semaphore for concurrency control.

    This answers Q3: we don't fetch one-by-one (too slow) or all at once
    (too aggressive / gets blocked). We fetch MAX_CONCURRENT_DETAIL_FETCHES at a time.

    Think of the Semaphore as a gate: only N workers can be inside at once.
    When one finishes, the next one enters.
    """
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DETAIL_FETCHES)

    async def fetch_one(card_data: dict) -> JobPosting:
        async with semaphore:
            page = await _new_stealth_page(browser)
            try:
                detail = await _fetch_job_description(page, card_data["job_url"])
            finally:
                await page.context.close()

            salary = detail["salary_detail"] or card_data.get("salary")

            return JobPosting(
                job_id           = card_data["job_id"],
                source           = SOURCE_NAME,
                title            = card_data["title"],
                company          = card_data["company"],
                location         = card_data["location"],
                job_url          = card_data["job_url"],
                description      = detail["description"],
                salary           = salary,
                posted_date_raw  = card_data["posted_date_raw"],
                posted_days_ago  = card_data["posted_days_ago"],
                employment_type  = detail["employment_type"],
            )

    tasks = [fetch_one(card) for card in cards]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    clean_results = []
    for r in results:
        if isinstance(r, Exception):
            logger.error("Detail fetch failed: %s", r)
        else:
            clean_results.append(r)

    return clean_results


async def scrape_query(query: str, location: str, browser: Browser) -> list[JobPosting]:
    """
    Scrape all fresh jobs for a single search query.

    This is the main function for one query. It:
    1. Paginates through listing pages (stopping early if stale jobs appear)
    2. Collects raw card data
    3. Deduplicates by job_id
    4. Fetches full descriptions in batches
    """
    all_cards: list[dict] = []
    seen_ids: set[str] = set()

    page = await _new_stealth_page(browser)

    try:
        for page_num in range(1, MAX_PAGES_PER_QUERY + 1):
            url = build_search_url(query, location, page=page_num)
            cards, should_continue = await _parse_listing_page(page, url)

            for card in cards:
                if card["job_id"] not in seen_ids:
                    seen_ids.add(card["job_id"])
                    all_cards.append(card)

            if not should_continue:
                logger.info("Stopping pagination for query %r at page %d", query, page_num)
                break

    finally:
        await page.context.close()

    logger.info("Found %d fresh cards for query %r", len(all_cards), query)

    if not all_cards:
        return []

    job_postings = await _fetch_all_details(browser, all_cards)
    return job_postings


async def run_scraper(queries: list[str], location: str) -> list[JobPosting]:
    """
    Top-level async entry point. Runs all queries sequentially
    (to be gentler on Indeed's servers) and returns a flat list of JobPostings.
    """
    all_jobs: list[JobPosting] = []

    async with async_playwright() as p:
        browser = await _setup_browser(p)

        try:
            for query in queries:
                logger.info("=" * 50)
                logger.info("Scraping query: %r in %r", query, location)
                jobs = await scrape_query(query, location, browser)
                all_jobs.extend(jobs)
                logger.info("Collected %d jobs for %r", len(jobs), query)

                await asyncio.sleep(random.uniform(3, 6))
        finally:
            await browser.close()

    # Final dedup across all queries
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        if job.job_id not in seen:
            seen.add(job.job_id)
            unique_jobs.append(job)

    logger.info("Total unique fresh jobs collected: %d", len(unique_jobs))
    return unique_jobs