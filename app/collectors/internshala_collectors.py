import asyncio
from playwright.async_api import async_playwright
from app.models.preferences import UserPreferences
import random

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
            headless=False
        )

        page = await browser.new_page()

        # Creating DB session
        db = SessionLocal()

        # Fetch user preferences
        preferences = db.query(UserPreferences).first()

        if not preferences:
            print("No preferences found.")
            db.close()
            await browser.close()
            return

        # Freshness Filtering
        MAX_JOB_AGE_DAYS = (
            preferences.max_job_age_days
            if preferences.max_job_age_days
            else 14
        )

        url = "https://internshala.com/internships/artificial-intelligence-ai,machine-learning-internship"

        # Open generated page
        await page.goto(
            url,
            wait_until="domcontentloaded"
        )

        delay = random.randint(4000, 7000)

        print(f"Waiting {delay/1000} seconds...")

        await page.wait_for_timeout(delay)

        cards = await page.query_selector_all(
            ".individual_internship"
        )

        #Temporarily adding to check if Auto Scroll is needed or not?
        print(
            "Initial cards loaded:",
            len(cards)
        )

        await page.evaluate(
            "window.scrollTo(0, document.body.scrollHeight)"
        )

        await page.wait_for_timeout(3000)

        cards_after_scroll = await page.query_selector_all(
            ".individual_internship"
        )

        print(
            "Cards after scroll:",
            len(cards_after_scroll)
        )
        # Till here Temp Code
        
        print(f"Found {len(cards)} internship cards")

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
            all_spans = await card.query_selector_all("span")

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

            job_age_days = convert_to_days(posted_date)

            # Freshness Filter
            if job_age_days > MAX_JOB_AGE_DAYS:

                print(
                    f"[SKIPPED - OLD JOB] "
                    f"{title} | Posted: {posted_date}"
                )

                continue

            job_url = ""

            if url_el:

                href = await url_el.get_attribute("href")

                if href:
                    job_url = f"https://internshala.com{href}"

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

            new_job = Job(
                title=title,
                company=company,
                location=location,
                salary=salary,
                skills=skills,
                description=description,
                job_url=job_url,
                posted_date=posted_date,
                source="Internshala"
            )

            db.add(new_job)

            print("Title:", title)
            print("Company:", company)
            print("Location:", location)
            print("Salary:", salary)
            print("Skills:", skills)
            print("Posted:", posted_date)
            print("URL:", job_url)

            print("-" * 40)

        db.commit()
        db.close()

        await browser.close()


asyncio.run(main())