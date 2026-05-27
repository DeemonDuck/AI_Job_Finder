import requests
import string
import time

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

print("\nTotal Unique Categories:")

print(len(all_categories))