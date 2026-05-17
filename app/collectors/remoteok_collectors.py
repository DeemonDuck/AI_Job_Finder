import requests
from bs4 import BeautifulSoup

from app.database import SessionLocal
from app.models.preferences import UserPreferences
print("Collector started...")

# Create database session
db = SessionLocal()

# Fetch latest user preferences
preferences = db.query(UserPreferences).first()

# Stop if no preferences exist
if not preferences:
    print("No user preferences found.")
    exit()


# Build search keyword dynamically
search_keyword = preferences.preferred_role.lower().replace(" ", "-")

url = f"https://remoteok.com/remote-{search_keyword}-jobs"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers)

print("Status Code:", response.status_code)
print("Scraping URL:", url)

soup = BeautifulSoup(response.text, "html.parser")

# Find job cards
jobs = soup.find_all("tr", class_="job")

print(f"Found {len(jobs)} jobs")


# Print first 5 jobs
for job in jobs[:5]:

    title = job.get("data-search")

    company = job.get("data-company")

    print("Job Title:", title)
    print("Company:", company)

    print("-" * 40)