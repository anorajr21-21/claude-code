import httpx
from typing import Optional
from config import TWOGIS_API_KEY

BASE_URL = "https://catalog.api.2gis.com/3.0/items"
GEOCODE_URL = "https://catalog.api.2gis.com/3.0/items/geocode"

CATEGORY_QUERIES = {
    "beauty_salon": ["салон красоты", "парикмахерская"],
    "car_wash":     ["автомойка"],
    "barbershop":   ["барбершоп"],
    "spa":          ["spa", "спа"],
}


def _geocode_city(city: str):
    resp = httpx.get(
        GEOCODE_URL,
        params={"q": city, "fields": "items.point", "key": TWOGIS_API_KEY},
        timeout=10,
    )
    resp.raise_for_status()
    items = resp.json().get("result", {}).get("items", [])
    if not items:
        raise ValueError(f"Could not geocode: {city}")
    point = items[0]["point"]
    return point["lon"], point["lat"]


def search_businesses(city: str, category: str = "beauty_salon", radius_m: int = 5000, max_results: int = 20) -> list[dict]:
    lon, lat = _geocode_city(city)
    queries = CATEGORY_QUERIES.get(category, [category])

    seen = set()
    results = []

    for query in queries:
        if len(results) >= max_results:
            break

        resp = httpx.get(
            BASE_URL,
            params={
                "q": query,
                "location": f"{lon},{lat}",
                "radius": radius_m,
                "key": TWOGIS_API_KEY,
                "fields": "items.name,items.address,items.contact_groups",
                "page_size": min(max_results - len(results), 10),
                "type": "branch",
            },
            timeout=15,
        )
        resp.raise_for_status()
        items = resp.json().get("result", {}).get("items", [])

        for item in items:
            place_id = item.get("id")
            if not place_id or place_id in seen:
                continue
            seen.add(place_id)
            results.append(_normalize(item, city, category))

    return results[:max_results]


def get_place_details(place_id: str) -> dict:
    resp = httpx.get(
        BASE_URL,
        params={
            "id": place_id,
            "key": TWOGIS_API_KEY,
            "fields": "items.contact_groups,items.address",
        },
        timeout=10,
    )
    resp.raise_for_status()
    items = resp.json().get("result", {}).get("items", [])
    if not items:
        return {}
    item = items[0]
    return {"phone": _extract_phone(item), "website": _extract_website(item)}


def _extract_phone(item: dict) -> Optional[str]:
    for group in item.get("contact_groups", []):
        for contact in group.get("contacts", []):
            if contact.get("type") == "phone":
                return contact.get("value")
    return None


def _extract_website(item: dict) -> Optional[str]:
    for group in item.get("contact_groups", []):
        for contact in group.get("contacts", []):
            if contact.get("type") in ("website", "url"):
                return contact.get("value")
    return None


def _normalize(item: dict, city: str, category: str) -> dict:
    # 2GIS returns the human-readable address as top-level "address_name"
    return {
        "place_id": item.get("id"),
        "name": item.get("name"),
        "address": item.get("address_name"),
        "phone": _extract_phone(item),
        "category": category,
        "rating": None,
        "website": _extract_website(item),
        "city": city,
    }
