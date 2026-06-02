"""Run this to debug the 2GIS API connection."""
import httpx
import json
from dotenv import load_dotenv
import os

load_dotenv()
KEY = os.environ.get("TWOGIS_API_KEY", "")

if not KEY:
    print("ERROR: TWOGIS_API_KEY not found in .env file")
    exit(1)

print(f"Using key: {KEY[:8]}...")

# Step 1: geocode Tashkent
print("\n--- Step 1: Geocoding Tashkent ---")
r = httpx.get(
    "https://catalog.api.2gis.com/3.0/items/geocode",
    params={"q": "Tashkent", "fields": "items.point", "key": KEY},
    timeout=10,
)
print(f"Status: {r.status_code}")
data = r.json()
print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])

items = data.get("result", {}).get("items", [])
if not items:
    print("\nERROR: Could not geocode Tashkent")
    exit(1)

lon = items[0]["point"]["lon"]
lat = items[0]["point"]["lat"]
print(f"\nTashkent coords: lon={lon}, lat={lat}")

# Step 2: search for beauty salons
print("\n--- Step 2: Searching for beauty salons ---")
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
print(json.dumps(data2, indent=2, ensure_ascii=False)[:2000])
