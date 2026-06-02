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
    MAX_PAGES_PER_QUERY, SOURCE_NAME
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
    "card_date":     "span.date",               # e.g. "3 days ago"
    "card_salary":   "div.metadata.salary-snippet-container span",
    "card_link":     "h2.jobTitle a",           # href contains the job URL + jk param

    # Fields on the job detail page
    "detail_description":      "div#jobDescriptionText",
    "detail_salary":           "div#salaryInfoAndJobType span",
    "detail_employment_type":  "div#jobDetailsSection span.attribute_snippet",

    # "No results" indicator — used to stop pagination early
    "no_results": "div.jobsearch-NoResult-messageContainer",
}


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
            "--disable-blink-features=AutomationControlled",  # Key stealth arg
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


async def _parse_listing_page(page: Page, url: str) -> tuple[list[dict], bool]:
    """
    Navigate to a search results page and extract job cards.

    Returns:
        (cards: list of raw card dicts, should_continue: bool)

    The should_continue flag is False when:
        - We find a job older than MAX_FRESHNESS_DAYS on this page
        - There are no results on this page
    Both cases mean we should stop paginating.
    """
    logger.info("Fetching listing page: %s", url)

    try:
        await page.goto(url, wait_until="networkidle")
        
        title = await page.title()
        logger.info("Page title: %s", title)

        if any(x in title.lower() for x in [
            "just a moment",
            "access denied",
            "captcha",
            "verify"
        ]):
            logger.error(
                "Bot protection page detected: %s",
                title
            )
            return [], False

        await _random_delay()
    except PWTimeout:
        logger.error("Timeout loading listing page: %s", url)
        return [], False

    # Check for "no results" before doing any work
    if await page.query_selector(SELECTORS["no_results"]):
        logger.info("No results found on this page — stopping pagination")
        return [], False

    cards_raw = []
    card_elements = await page.query_selector_all(SELECTORS["job_card"])

    if not card_elements:
        logger.warning("No job cards found — selector may be stale: %r", SELECTORS["job_card"])
        return [], False

    should_continue = True

    for card_el in card_elements:
        try:
            # --- Extract date first (cheapest check) ---
            date_el = await card_el.query_selector(SELECTORS["card_date"])
            date_raw = (await date_el.inner_text()).strip() if date_el else ""

            is_fresh, days_ago = is_within_freshness_window(date_raw, MAX_FRESHNESS_DAYS)

            # ── KEY EARLY EXIT ────────────────────────────────────────────
            # Once we see a job older than our window, Indeed's results are
            # sorted newest-first, so ALL subsequent jobs will be older too.
            # Stop processing this page AND don't fetch the next page.
            if not is_fresh:
                logger.info(
                    "Found job with age %r (%s days) — stopping pagination",
                    date_raw, days_ago
                )
                should_continue = False
                break
            # ─────────────────────────────────────────────────────────────

            # Extract remaining card fields
            title_el   = await card_el.query_selector(SELECTORS["card_title"])
            company_el = await card_el.query_selector(SELECTORS["card_company"])
            loc_el     = await card_el.query_selector(SELECTORS["card_location"])
            salary_el  = await card_el.query_selector(SELECTORS["card_salary"])
            link_el    = await card_el.query_selector(SELECTORS["card_link"])

            title   = (await title_el.get_attribute("title") or await title_el.inner_text()) if title_el else ""
            company = await company_el.inner_text() if company_el else ""
            loc     = await loc_el.inner_text() if loc_el else ""
            salary  = await salary_el.inner_text() if salary_el else None
            href    = await link_el.get_attribute("href") if link_el else ""

            from config.settings import INDEED_BASE_URL
            full_url = href if href.startswith("http") else f"{INDEED_BASE_URL}{href}"
            job_id   = extract_job_id_from_url(full_url)

            cards_raw.append({
                "job_id":          job_id,
                "title":           title.strip(),
                "company":         company.strip(),
                "location":        loc.strip(),
                "job_url":         full_url,
                "salary":          salary.strip() if salary else None,
                "posted_date_raw": date_raw,
                "posted_days_ago": days_ago,
            })

        except Exception as e:
            logger.warning("Error parsing card: %s", e)
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
    results: list[JobPosting] = []

    async def fetch_one(card_data: dict) -> JobPosting:
        async with semaphore:
            page = await _new_stealth_page(browser)
            try:
                detail = await _fetch_job_description(page, card_data["job_url"])
            finally:
                await page.context.close()

            # Merge card data + detail data into a JobPosting
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

    # Run all fetch tasks concurrently (limited by semaphore)
    tasks = [fetch_one(card) for card in cards]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out any exceptions that slipped through
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

    # Now fetch full descriptions
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

                # Polite pause between queries
                await asyncio.sleep(random.uniform(3, 6))
        finally:
            await browser.close()

    # Final dedup across all queries (same job can appear for multiple search terms)
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        if job.job_id not in seen:
            seen.add(job.job_id)
            unique_jobs.append(job)

    logger.info("Total unique fresh jobs collected: %d", len(unique_jobs))
    return unique_jobs
