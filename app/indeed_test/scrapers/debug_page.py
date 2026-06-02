"""
scrapers/debug_page.py
======================
Run this when the main scraper gets 0 jobs.
It opens the browser visibly, loads one search page, and saves:
  - A screenshot: debug_output/screenshot.png
  - The full HTML: debug_output/page.html

Open page.html in your browser and inspect what Indeed actually served.
Look for the real job card class names and update SELECTORS in indeed_scraper.py.

Usage:
    python scrapers/debug_page.py
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from config.settings import INDEED_BASE_URL, USER_AGENT
from utils.url_builder import build_search_url


async def debug():
    url = build_search_url("python developer", "India", page=1)
    print(f"Loading: {url}")

    output_dir = Path("debug_output")
    output_dir.mkdir(exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,   # Visible — watch what Indeed shows you
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 800},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )
        page = await context.new_page()

        await page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)  # Extra wait so JS fully settles

        title = await page.title()
        print(f"Page title: {title!r}")

        # Save screenshot
        screenshot_path = output_dir / "screenshot.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"Screenshot saved: {screenshot_path}")

        # Save HTML
        html_path = output_dir / "page.html"
        html_path.write_text(await page.content(), encoding="utf-8")
        print(f"HTML saved: {html_path}")

        # Try to find job cards and print what classes they actually have
        print("\nSearching for job-like elements...")
        candidates = await page.query_selector_all("div[class*='job'], li[class*='job'], div[data-testid]")
        if candidates:
            print(f"Found {len(candidates)} candidate elements.")
            for el in candidates[:5]:
                cls = await el.get_attribute("class") or ""
                testid = await el.get_attribute("data-testid") or ""
                print(f"  class={cls[:80]!r}  data-testid={testid!r}")
        else:
            print("No job-like elements found at all — likely a bot block page.")

        input("\nPress Enter to close the browser...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug())