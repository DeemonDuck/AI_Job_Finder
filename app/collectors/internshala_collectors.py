import asyncio
from playwright.async_api import async_playwright
from app.models.preferences import UserPreferences
import random

from app.collectors.test_dynamic_navigation import (
    navigate_to_category
)

from app.database import SessionLocal
from app.models.job import Job


def convert_to_days(posted_text):

    if not posted_text:
        return 999

    posted_text = posted_text.lower().strip()

    # Fresh jobs indicators
    fresh_keywords = [
        "just now",
        "today",
        "hour",
        "hours",
        "minute",
        "minutes",
        "few hours ago",
        "actively hiring",
        "early applicant",
        "immediately",
        "recently"
    ]

    if any(keyword in posted_text for keyword in fresh_keywords):
        return 0

    try:

        number = int(posted_text.split()[0])

        if "day" in posted_text:
            return number

        elif "week" in posted_text:
            return number * 7

        elif "month" in posted_text:
            return number * 30

    except Exception as e:

        print(
            f"[DATE PARSE ERROR] "
            f"Text: '{posted_text}' | Error: {e}"
        )

    return 999


async def main():

    async with async_playwright() as pw:

        browser = await pw.chromium.launch(
            channel="msedge",
            headless=False
        )

        page = await browser.new_page(
            viewport={
                "width": 1600,
                "height": 900
            }
        )

        # Database session
        db = SessionLocal()

        # Fetch user preferences
        preferences = db.query(
            UserPreferences
        ).first()

        if not preferences:

            print("No preferences found.")

            db.close()

            await browser.close()

            return

        # Freshness filtering
        MAX_JOB_AGE_DAYS = (
            preferences.max_job_age_days
            if preferences.max_job_age_days
            else 14
        )

        ##Testing Dynamic Navigation Integration with the Extraction Logic
        
        category_name="Machine Learning"

        base_url = await navigate_to_category(
            page,
            category_name
        )
        # Testing code ends here

        # Extract expected internship count
        count_el = await page.query_selector(
            ".internship_seo_heading_container h1"
        )

        expected_count = "Unknown"

        if count_el:

            heading_text = await count_el.inner_text()

            print(
                f"Heading Text: {heading_text}"
            )

            try:

                expected_count = int(
                    heading_text.split()[0]
                )

            except Exception as e:

                print(
                    f"[COUNT PARSE ERROR] {e}"
                )

        print(
            f"Expected internships: "
            f"{expected_count}"
        )

        # Detect total pages dynamically
        pagination_buttons = await page.query_selector_all(
            "a.pagination_block.block"
        )

        total_pages = 1

        for button in pagination_buttons:

            page_number = await button.get_attribute(
                "data-page"
            )

            if page_number:

                total_pages = max(
                    total_pages,
                    int(page_number)
                )

        print(
            f"Total Pages Found: "
            f"{total_pages}"
        )

        # Loop through all pages
        for page_number in range(
            1,
            total_pages + 1
        ):

            # Build URL
            if page_number == 1:

                url = base_url

            else:

                url = (
                    f"{base_url}/"
                    f"page-{page_number}/"
                )

            print(
                f"\nScraping Page "
                f"{page_number}"
            )

            print(f"URL: {url}")

            # Open current page
            await page.goto(
                url,
                wait_until="domcontentloaded"
            )

            print(
                f"Opened Page {page_number}"
            )

            # Human-like delay
            await page.wait_for_timeout(5000)

            
            # Initial extraction
            cards = await page.query_selector_all(
                ".individual_internship"
            )

            print(
                f"Initial cards loaded: "
                f"{len(cards)}"
            )

            # Scroll to last visible internship card
            last_card = cards[-1]
            
            await last_card.scroll_into_view_if_needed()
            
            print(
                "Scrolled to last internship card..."
            )
            
            # Re-fetch cards
            cards = await page.query_selector_all(
                ".individual_internship"
            )

            print(
                f"Cards after scroll: "
                f"{len(cards)}"
            )

            # Process every internship card
            for card in cards:

                title_el = await card.query_selector(
                    ".job-internship-name"
                )

                company_el = await card.query_selector(
                    ".company-name"
                )

                location_el = await card.query_selector(
                    ".row-1-item.locations"
                )

                salary_el = await card.query_selector(
                    ".stipend"
                )

                description_el = await card.query_selector(
                    ".text"
                )

                url_el = await card.query_selector(
                    ".job-title-href"
                )

                skills_elements = await card.query_selector_all(
                    ".job_skill"
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

                salary = (
                    await salary_el.inner_text()
                    if salary_el
                    else "Not Mentioned"
                )

                description = (
                    await description_el.inner_text()
                    if description_el
                    else "No Description"
                )

                # Better posted date extraction
                all_spans = await card.query_selector_all(
                    "span"
                )

                posted_date = "Unknown"

                for span in all_spans:

                    text = await span.inner_text()

                    text = text.strip().lower()

                    if (
                        "ago" in text
                        or "today" in text
                        or "just now" in text
                        or "actively hiring" in text
                        or "early applicant" in text
                    ):

                        posted_date = text

                        break

                # Debug logging
                print(
                    f"[DEBUG] "
                    f"Title: {title} | "
                    f"Posted Text: '{posted_date}'"
                )

                job_age_days = convert_to_days(
                    posted_date
                )

                # Freshness filter
                if (
                    job_age_days >
                    MAX_JOB_AGE_DAYS
                ):

                    print(
                        f"[SKIPPED - OLD JOB] "
                        f"{title} | "
                        f"Posted: {posted_date}"
                    )

                    continue

                job_url = ""

                if url_el:

                    href = await url_el.get_attribute(
                        "href"
                    )

                    if href:

                        job_url = (
                            f"https://internshala.com"
                            f"{href}"
                        )

                skills_list = []

                for skill in skills_elements:

                    skill_text = await skill.inner_text()

                    skills_list.append(skill_text)

                skills = ", ".join(skills_list)

                # Skip invalid cards
                if title == "No Title":

                    print(
                        "[SKIPPED - INVALID CARD]"
                    )

                    continue

                # Duplicate check
                existing_job = db.query(Job).filter(
                    Job.job_url == job_url
                ).first()

                if existing_job:

                    print(
                        f"[SKIPPED - DUPLICATE] "
                        f"{title}"
                    )

                    continue

                # Create new DB entry
                new_job = Job(
                    title=title,
                    company=company,
                    location=location,
                    salary=salary,
                    skills=skills,
                    search_category=category_name,
                    description=description,
                    job_url=job_url,
                    posted_date=posted_date,
                    source="Internshala"
                )

                db.add(new_job)

                # Logging
                print("Title:", title)
                print("Company:", company)
                print("Location:", location)
                print("Salary:", salary)
                print("Skills:", skills)
                print("Posted:", posted_date)
                print("URL:", job_url)

                print("-" * 40)

        print(db.query(Job).count())

        db.commit()

        db.close()

        await browser.close()


asyncio.run(main())