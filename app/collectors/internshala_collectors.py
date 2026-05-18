import asyncio
from playwright.async_api import async_playwright


async def main():

    async with async_playwright() as pw:

        browser = await pw.chromium.launch(
            headless=False
        )

        page = await browser.new_page()

        await page.goto(
            "https://internshala.com/internships/work-from-home-ai-ml-internships/",
            wait_until="domcontentloaded"
        )

        await page.wait_for_timeout(5000)

        cards = await page.query_selector_all(
            ".individual_internship"
        )

        print(f"Found {len(cards)} internship cards")

        for card in cards[:5]:

            title_el = await card.query_selector(
                ".job-internship-name"
            )

            company_el = await card.query_selector(
                ".company-name"
            )

            location_el = await card.query_selector(
                ".row-1-item.locations"
            )

            title = (
                await title_el.inner_text()
                if title_el
                else "No Title"
            )

            company = (
                await company_el.inner_text()
                if company_el
                else "No Company"
            )

            location = (
                await location_el.inner_text()
                if location_el
                else "No Location"
            )

            # Skip invalid cards
            if title == "No Title":
                continue

            print("Title:", title)
            print("Company:", company)
            print("Location:", location)

            print("-" * 40)

        await browser.close()

asyncio.run(main())