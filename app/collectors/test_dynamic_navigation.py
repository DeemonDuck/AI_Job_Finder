import asyncio

from playwright.async_api import (
    async_playwright
)


async def navigate_to_category(
    page,
    category_name
):

    # Open Internshala internships page
    await page.goto(
        "https://internshala.com/internships/",
        wait_until="domcontentloaded"
    )

    print("Opened Internshala")

    # Handle popup safely
    try:

        await page.click(
            "#close_popup",
            timeout=10000
        )

        print("Popup closed")

    except Exception:

        print("Popup did not appear")

    # Wait before interaction
    await page.wait_for_timeout(5000)

    # Wait for search input
    await page.wait_for_selector(
        ".chosen-search-input"
    )

    print("Search input found")

    # Click search input
    await page.click(
        ".chosen-search-input"
    )

    print("Clicked search input")

    # Type category
    await page.keyboard.type(
        category_name,
        delay=150
    )

    print("Typed category")

    # Press Enter
    await page.keyboard.press("Enter")

    print("Pressed Enter")

    # Wait for internships page to load
    await page.wait_for_timeout(5000)

    base_url = page.url

    print(
        f"Dynamic Base URL: "
        f"{base_url}"
    )

    return base_url