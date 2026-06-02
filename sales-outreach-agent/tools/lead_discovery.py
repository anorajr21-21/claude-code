import googlemaps
from config import GOOGLE_MAPS_API_KEY

_gmaps = None


def _client() -> googlemaps.Client:
    global _gmaps
    if _gmaps is None:
        _gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    return _gmaps


# Business types most relevant for Too Good To Go
TGTG_RELEVANT_TYPES = [
    "restaurant",
    "cafe",
    "bakery",
    "meal_takeaway",
    "food",
    "supermarket",
    "grocery_or_supermarket",
    "convenience_store",
]


def search_businesses(city: str, category: str = "restaurant", radius_m: int = 5000, max_results: int = 20) -> list[dict]:
    """Search Google Maps for food businesses in a city not yet on Too Good To Go."""
    gmaps = _client()

    geocode = gmaps.geocode(city)
    if not geocode:
        raise ValueError(f"Could not geocode city: {city}")
    loc = geocode[0]["geometry"]["location"]

    results = []
    page_token = None

    while len(results) < max_results:
        kwargs = dict(
            location=loc,
            radius=radius_m,
            type=category,
            language="es",
        )
        if page_token:
            kwargs["page_token"] = page_token

        resp = gmaps.places_nearby(**kwargs)
        for place in resp.get("results", []):
            if len(results) >= max_results:
                break
            results.append(_normalize(place, city, category))

        page_token = resp.get("next_page_token")
        if not page_token:
            break

    return results


def get_place_details(place_id: str) -> dict:
    gmaps = _client()
    fields = [
        "name", "formatted_address", "formatted_phone_number",
        "international_phone_number", "website", "rating",
        "opening_hours", "types",
    ]
    resp = gmaps.place(place_id=place_id, fields=fields, language="es")
    result = resp.get("result", {})
    return {
        "phone": result.get("international_phone_number") or result.get("formatted_phone_number"),
        "website": result.get("website"),
        "opening_hours": result.get("opening_hours", {}).get("weekday_text", []),
    }


def _normalize(place: dict, city: str, category: str) -> dict:
    return {
        "place_id": place.get("place_id"),
        "name": place.get("name"),
        "address": place.get("vicinity"),
        "phone": None,  # requires details call
        "category": category,
        "rating": place.get("rating"),
        "website": None,
        "city": city,
    }
