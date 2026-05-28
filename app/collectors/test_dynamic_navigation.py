import asyncio

from playwright.async_api import (
    async_playwright
)


async def main():

    async with async_playwright() as pw:

        browser = await pw.chromium.launch(
            channel="msedge",
            headless=False
        )
        #Forcing it to open using only Desktop Viewport
        page = await browser.new_page(
            viewport={
                "width": 1600,
                "height": 900
            }
        )
        # Open Internshala homepage
        await page.goto(
            "https://internshala.com/internships/",
            wait_until="domcontentloaded"
        )

        print("Opened Internshala")
        
        try:
                
            await page.click(
                "#close_popup",
                timeout=10000
            )

            print("Popup closed")

        except Exception:
        
            print("Popup did not appear")

        # Wait for page load
        await page.wait_for_timeout(5000)

        await page.wait_for_selector(
            ".chosen-search-input"
        )

        print("Search input found")

        await page.click(
            ".chosen-search-input"
        )

        print("Clicked search input")

        await page.keyboard.type(
            "Machine Learning",
            delay=150
        )

        await page.keyboard.press("Enter")

        print("Pressed Enter")

        print("Typed category")
        # Till here Debugging

        # Wait for dropdown suggestions
        await page.wait_for_timeout(3000)

        print(
            "Check manually if dropdown appeared"
        )

        # Keep browser open temporarily
        await page.wait_for_timeout(5000)

        await browser.close()


asyncio.run(main())