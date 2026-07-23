import requests
import re
import json

url = "https://apps.apple.com/in/app/blinkit-groceries-more/id1044431526"
html = requests.get(url).text

# Find the token
match = re.search(r'token%22%3A%22([^%]+)%22', html)
if not match:
    match = re.search(r'token":"([^"]+)"', html)
    
if match:
    token = match.group(1)
    print("Found token:", token[:20] + "...")
    
    api_url = "https://amp-api.apps.apple.com/v1/catalog/IN/apps/1044431526/reviews?l=en-GB&offset=0&limit=20"
    headers = {
        "Authorization": f"Bearer {token}",
        "Origin": "https://apps.apple.com"
    }
    resp = requests.get(api_url, headers=headers)
    print("API Status:", resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        print("Fetched reviews:", len(data.get("data", [])))
        if data.get("data"):
            print("First review:", data["data"][0]["attributes"]["review"])
    else:
        print("Failed to fetch API:", resp.text[:100])
else:
    print("Could not find token in HTML.")
