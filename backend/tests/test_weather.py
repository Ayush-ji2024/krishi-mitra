"""
Weather tests. They NEVER call the real Open-Meteo API: `fetch_json` is replaced
with a fake ("mock") that returns fixed data. That makes the tests fast,
repeatable (the real weather changes every day) and able to run offline.

    python -m pytest backend/tests/test_weather.py -v
"""

import pytest
from fastapi.testclient import TestClient

from backend.app import weather
from backend.app.main import app

from datetime import date, timedelta


def make_archive(first_year=2021, last_year=2025):
    """Fake daily archive: each season gets clearly different, easy numbers.
    Jul = 30 deg / 80 % / 10 mm a day, Jan = 15 deg / 60 % / 1 mm a day,
    Apr = 35 deg / 40 % / no rain, every other month = 20 deg / 50 % / no rain."""
    by_month = {7: (30.0, 80.0, 10.0), 1: (15.0, 60.0, 1.0), 4: (35.0, 40.0, 0.0)}
    time, temp, hum, rain = [], [], [], []
    d = date(first_year, 1, 1)
    while d <= date(last_year, 12, 31):
        t, h, r = by_month.get(d.month, (20.0, 50.0, 0.0))
        time.append(d.isoformat()); temp.append(t); hum.append(h); rain.append(r)
        d += timedelta(days=1)
    return {"daily": {"time": time, "temperature_2m_mean": temp,
                      "relative_humidity_2m_mean": hum, "precipitation_sum": rain}}


FAKE_PLACES = {
    "results": [
        {"name": "Begusarai", "admin1": "Bihar", "admin2": "Begusarai", "country": "India",
         "latitude": 25.4182, "longitude": 86.1272},
    ]
}


@pytest.fixture
def calls():
    return []


@pytest.fixture
def client(monkeypatch, calls):
    async def fake_fetch_json(url, params):
        calls.append(url)
        if url == weather.GEOCODE_URL:
            return FAKE_PLACES if params["name"].lower().startswith("begu") else {}
        assert params["start_date"].endswith("-01-01") and params["end_date"].endswith("-12-31")
        return make_archive(int(params["start_date"][:4]), int(params["end_date"][:4]))

    monkeypatch.setattr(weather, "fetch_json", fake_fetch_json)
    weather._cache.clear()  # every test starts without cached data
    with TestClient(app) as c:
        yield c


def test_season_normals_from_daily_data():
    seasons = weather._season_normals(make_archive()["daily"])
    # Kharif = Jun..Oct: Jul is 30 deg, the other 4 months 20 deg (weighted by days).
    kharif = seasons["kharif"]
    days = {6: 30, 7: 31, 8: 31, 9: 30, 10: 31}
    assert kharif["temperature"] == round((31 * 30 + (153 - 31) * 20) / 153, 1)
    # Rain: 31 days x 10 mm in July only, spread over the 5 months of the season.
    assert kharif["rainfall"] == round(31 * 10 / 5, 1) == 62.0
    assert kharif["months"] == list(days)
    # Rabi = Nov..Mar: only January has rain (31 x 1 mm), over 5 months.
    assert seasons["rabi"]["rainfall"] == 6.2
    # Zaid = Mar..Jun: dry.
    assert seasons["zaid"]["rainfall"] == 0.0


def test_missing_values_are_skipped():
    daily = make_archive(2025, 2025)["daily"]
    daily["temperature_2m_mean"][200] = None   # a July day
    daily["precipitation_sum"][201] = None
    seasons = weather._season_normals(daily)
    assert seasons["kharif"]["temperature"] > 20


@pytest.mark.parametrize("day, season", [
    (date(2026, 6, 15), "kharif"), (date(2026, 11, 10), "rabi"),
    (date(2026, 8, 1), "rabi"), (date(2026, 2, 20), "zaid"),
])
def test_upcoming_season(day, season):
    assert weather.upcoming_season(day) == season


def test_weather_endpoint_returns_all_seasons(client):
    r = client.get("/weather", params={"lat": 25.42, "lon": 86.13})
    assert r.status_code == 200
    body = r.json()
    assert set(body["seasons"]) == {"kharif", "rabi", "zaid"}
    assert body["default_season"] in body["seasons"]
    years = body["years"]
    assert years["end"] == date.today().year - 1 and years["end"] - years["start"] == weather.YEARS - 1
    assert body["seasons"]["kharif"]["rainfall"] == 62.0


def test_weather_is_cached_per_location(client, calls):
    for _ in range(3):
        assert client.get("/weather", params={"lat": 25.42, "lon": 86.13}).status_code == 200
    assert calls.count(weather.ARCHIVE_URL) == 1   # fetched once, then from the cache
    client.get("/weather", params={"lat": 26.0, "lon": 85.0})
    assert calls.count(weather.ARCHIVE_URL) == 2   # a new place is fetched


def test_weather_rejects_bad_coordinates(client):
    assert client.get("/weather", params={"lat": 200, "lon": 86}).status_code == 422


def test_places_found(client):
    r = client.get("/places", params={"q": "Begusarai"})
    assert r.status_code == 200
    place = r.json()[0]
    assert place["state"] == "Bihar"
    assert round(place["latitude"], 2) == 25.42


def test_places_not_found_returns_empty_list(client):
    r = client.get("/places", params={"q": "xyzxyz"})
    assert r.status_code == 200
    assert r.json() == []


def test_weather_service_down_gives_502(monkeypatch):
    async def broken_fetch(url, params):
        raise weather.WeatherError("Weather service error: timeout")

    monkeypatch.setattr(weather, "fetch_json", broken_fetch)
    weather._cache.clear()
    with TestClient(app) as c:
        r = c.get("/weather", params={"lat": 25.42, "lon": 86.13})
    assert r.status_code == 502
    assert "timeout" in r.json()["detail"]
