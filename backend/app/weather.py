"""
Weather auto-fill using Open-Meteo (free for non-commercial use, no API key).
  Docs: https://open-meteo.com/en/docs  and  https://open-meteo.com/en/docs/geocoding-api

Farmers rarely know exact temperature / humidity / rainfall numbers, but they
know their village or town. We turn a place name into coordinates (geocoding)
and fetch the LAST 30 DAYS of daily weather for those coordinates.

IMPORTANT - rainfall is an approximation:
The Kaggle dataset documents rainfall only as "rainfall in mm", without saying
over which period. Its values (about 20-300 mm) are far below yearly totals in
India (Bihar gets ~1100 mm a year), so they are NOT annual. We use the total of
the last 30 days as a best guess and tell the user it can be edited.
"""

import httpx

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
PERIOD_DAYS = 30
TIMEOUT_SECONDS = 10


class WeatherError(Exception):
    """Raised when the weather service can't be reached or returns bad data."""


async def fetch_json(url: str, params: dict) -> dict:
    """The ONLY function that talks to the internet - tests replace it with a fake."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise WeatherError(f"Weather service error: {e}") from e


async def search_places(query: str, limit: int = 5) -> list[dict]:
    """'Begusarai' -> [{name, state, country, latitude, longitude}, ...] (India only)."""
    data = await fetch_json(GEOCODE_URL, {
        "name": query, "count": limit, "language": "en", "countryCode": "IN", "format": "json",
    })
    return [
        {
            "name": r["name"],
            "state": r.get("admin1"),
            "district": r.get("admin2"),
            "country": r.get("country"),
            "latitude": r["latitude"],
            "longitude": r["longitude"],
        }
        for r in data.get("results", [])  # no "results" key when nothing matches
    ]


def _mean(values):
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


async def recent_weather(latitude: float, longitude: float, days: int = PERIOD_DAYS) -> dict:
    """Average temperature & humidity and total rainfall over the last `days` days."""
    data = await fetch_json(FORECAST_URL, {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum",
        "past_days": days,
        "forecast_days": 1,   # the API also returns today; we drop it below
        "timezone": "auto",
    })
    try:
        daily = data["daily"]
        dates = daily["time"][:days]  # past days come first, today is last
        temps = daily["temperature_2m_mean"][:days]
        hums = daily["relative_humidity_2m_mean"][:days]
        rains = daily["precipitation_sum"][:days]
    except (KeyError, TypeError) as e:
        raise WeatherError(f"Unexpected weather data format: {e}") from e

    temperature, humidity = _mean(temps), _mean(hums)
    rain_values = [r for r in rains if r is not None]
    if temperature is None or humidity is None or not rain_values:
        raise WeatherError("No weather data available for this location.")

    return {
        "temperature": round(temperature, 1),
        "humidity": round(humidity, 1),
        "rainfall": round(sum(rain_values), 1),
        "period": {"days": len(dates), "start": dates[0], "end": dates[-1]},
        "source": "Open-Meteo",
        "note": (f"Averages / total of the last {len(dates)} days. Rainfall is an estimate: "
                 "the training data does not say which period its rainfall covers. "
                 "You can edit any value."),
    }
