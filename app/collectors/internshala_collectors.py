import asyncio
from playwright.async_api import async_playwright
from app.models.preferences import UserPreferences

from app.database import SessionLocal
from app.models.job import Job

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
            return
        
        # Generate dynamic Internshala URL
        role_slug = (
            preferences.preferred_role
            .lower()
            .replace(" ", "-")
        )
        
        location_slug = (
            preferences.preferred_location
            .lower()
            .replace(" ", "-")
        )
        
        url = (
            f"https://internshala.com/internships/"
            f"{location_slug}-{role_slug}-internships/"
        )
        
        print("Generated URL:", url)
        
        # Open generated page
        await page.goto(
            url,
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
            
            salary_el = await card.query_selector(
                ".stipend"
            )

            description_el = await card.query_selector(
                ".text"
            )

            posted_el = await card.query_selector(
                ".detail-row-2"
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

            posted_date = (
                await posted_el.inner_text()
                if posted_el
                else "Unknown"
            )

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
                continue

            existing_job = db.query(Job).filter(
                Job.job_url == job_url
            ).first()

            if existing_job:
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