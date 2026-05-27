import requests
import string
import time

from app.database import SessionLocal
from app.models.internshala_category import (
    InternshalaCategory
)

db = SessionLocal()

all_categories = set()

url = (
    "https://internshala.com/"
    "autocomplete/category_filters"
)

for letter in string.ascii_lowercase:

    payload = {
        "s": letter
    }

    response = requests.post(
        url,
        data=payload
    )

    time.sleep(1)

    data = response.json()

    results = data.get("result", [])

    print(f"\nLetter: {letter}")

    for category in results:

        print(category)

        all_categories.add(category)

# Store categories in DB
for category_name in all_categories:

    existing_category = db.query(
        InternshalaCategory
    ).filter(
        InternshalaCategory.name == category_name
    ).first()

    if existing_category:

        print(
            f"[SKIPPED DUPLICATE] "
            f"{category_name}"
        )

        continue

    new_category = InternshalaCategory(
        name=category_name
    )

    db.add(new_category)

    print(
        f"[ADDED] {category_name}"
    )

db.commit()

db.close()

print(
    f"\nTotal Unique Categories: "
    f"{len(all_categories)}"
)