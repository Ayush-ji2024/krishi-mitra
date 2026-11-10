"""
Weather auto-fill using Open-Meteo (free for non-commercial use, no API key).
  Docs: https://open-meteo.com/en/docs/historical-weather-api
        https://open-meteo.com/en/docs/geocoding-api

Farmers rarely know exact temperature / humidity / rainfall numbers, but they
know their village or town. We turn a place name into coordinates (geocoding)
and compute the USUAL weather of each growing season there.

Why seasons, not "the last 30 days":
A crop is chosen for the season it will GROW in, not for the weather of the
past month (asking in November should describe the Rabi winter, not October's
monsoon tail). So we average the last 5 complete years of daily data for each
season:
    Kharif (monsoon)  Jun-Oct    Rabi (winter)  Nov-Mar    Zaid (summer)  Mar-Jun

Rainfall is given as the AVERAGE PER MONTH of that season. The Kaggle crop
dataset documents rainfall only as "mm", without a period, but its values
(about 20-300 mm) match monthly totals, not seasonal or yearly ones (Bihar gets
~1100 mm a year). The farmer can still edit every value.
"""

from datetime import date

import httpx

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
YEARS = 5
TIMEOUT_SECONDS = 20

# Months of each season (Kharif/Rabi/Zaid as commonly used in Indian agriculture).
SEASONS = {
    "kharif": (6, 7, 8, 9, 10),
    "rabi": (11, 12, 1, 2, 3),
    "zaid": (3, 4, 5, 6),
}


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


def upcoming_season(today: date) -> str:
    """The next season a farmer would SOW for, given today's date.
    May-Jul: Kharif sowing; Aug-Dec: Rabi is next; Jan-Apr: Zaid is next."""
    if today.month in (5, 6, 7):
        return "kharif"
    if today.month >= 8:
        return "rabi"
    return "zaid"


def _season_normals(daily: dict) -> dict:
    """Average temperature & humidity and average monthly rainfall for each season."""
    rows = list(zip(daily["time"], daily["temperature_2m_mean"],
                    daily["relative_humidity_2m_mean"], daily["precipitation_sum"]))
    result = {}
    for name, months in SEASONS.items():
        temps, hums, rain_total, rain_months = [], [], 0.0, set()
        for day, t, h, r in rows:
            if int(day[5:7]) not in months:
                continue
            if t is not None:
                temps.append(t)
            if h is not None:
                hums.append(h)
            if r is not None:
                rain_total += r
                rain_months.add(day[:7])  # "2024-07": count each month once
        if not temps or not hums or not rain_months:
            raise WeatherError(f"Not enough weather data for the {name} season here.")
        result[name] = {
            "temperature": round(sum(temps) / len(temps), 1),
            "humidity": round(sum(hums) / len(hums), 1),
            "rainfall": round(rain_total / len(rain_months), 1),
            "months": list(months),
        }
    return result


# Season normals don't change during a year, so each location is fetched once.
# Key: coordinates rounded to ~1 km + the year range. Small and in-memory.
_cache: dict[tuple, dict] = {}
_CACHE_MAX = 500


async def seasonal_weather(latitude: float, longitude: float, today: date | None = None) -> dict:
    """Usual weather of every season at a location, from the last YEARS complete years."""
    today = today or date.today()
    first, last = today.year - YEARS, today.year - 1
    key = (round(latitude, 2), round(longitude, 2), first, last)

    seasons = _cache.get(key)
    if seasons is None:
        data = await fetch_json(ARCHIVE_URL, {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": f"{first}-01-01",
            "end_date": f"{last}-12-31",
            "daily": "temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum",
            "timezone": "auto",
        })
        try:
            seasons = _season_normals(data["daily"])
        except (KeyError, TypeError, ValueError) as e:
            raise WeatherError(f"Unexpected weather data format: {e}") from e
        if len(_cache) >= _CACHE_MAX:
            _cache.pop(next(iter(_cache)))  # drop the oldest entry
        _cache[key] = seasons

    return {
        "default_season": upcoming_season(today),
        "years": {"start": first, "end": last},
        "seasons": seasons,
        "source": "Open-Meteo historical weather (ERA5)",
        "note": (f"Usual weather of each season, averaged over {first}-{last}. "
                 "Rainfall is the average per month of the season. You can edit any value."),
    }
