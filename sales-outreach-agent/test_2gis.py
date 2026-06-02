"""Run this to debug the 2GIS API connection."""
import httpx
import json
import sys
from dotenv import load_dotenv
import os

load_dotenv()
KEY = os.environ.get("TWOGIS_API_KEY", "")

if not KEY:
    print("ERROR: TWOGIS_API_KEY not found in .env file")
    sys.exit(1)

print(f"Using key: {KEY[:8]}...")

# Step 1: geocode
print("\n--- Step 1: Geocoding 'Tashkent, Uzbekistan' ---")
r = httpx.get(
    "https://catalog.api.2gis.com/3.0/items/geocode",
    params={"q": "Tashkent, Uzbekistan", "fields": "items.point", "key": KEY},
    timeout=10,
)
print(f"Status: {r.status_code}")
data = r.json()
items = data.get("result", {}).get("items", [])
if not items:
    print("ERROR: Could not geocode Tashkent")
    sys.exit(1)
lon = items[0]["point"]["lon"]
lat = items[0]["point"]["lat"]
print(f"Coords: lon={lon}, lat={lat}")

# Step 2: search
print("\n--- Step 2: Searching 'салон красоты' ---")
r2 = httpx.get(
    "https://catalog.api.2gis.com/3.0/items",
    params={
        "q": "салон красоты",
        "location": f"{lon},{lat}",
        "radius": 5000,
        "key": KEY,
        "fields": "items.name,items.address,items.contact_groups",
        "page_size": 5,
        "type": "branch",
    },
    timeout=15,
)
print(f"Status: {r2.status_code}")
data2 = r2.json()
raw_items = data2.get("result", {}).get("items", [])
print(f"Items returned: {len(raw_items)}")
for item in raw_items:
    print(f"  - {item.get('name')} | address_name={item.get('address_name')} | id={item.get('id')}")

# Step 3: call search_businesses directly
print("\n--- Step 3: Calling search_businesses() directly ---")
try:
    from tools.lead_discovery import search_businesses
    results = search_businesses("Tashkent, Uzbekistan", "beauty_salon", max_results=5)
    print(f"Results: {len(results)}")
    for r in results:
        print(f"  - {r['name']} | {r['address']} | phone={r['phone']}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
