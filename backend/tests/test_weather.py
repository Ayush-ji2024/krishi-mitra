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

# 30 past days + today (the API returns today last; our code must drop it)
FAKE_FORECAST = {
    "daily": {
        "time": [f"2026-09-{d:02d}" for d in range(1, 31)] + ["2026-10-01"],
        "temperature_2m_mean": [30.0] * 15 + [26.0] * 15 + [99.0],   # today = 99 must be ignored
        "relative_humidity_2m_mean": [80.0] * 30 + [5.0],
        "precipitation_sum": [10.0] * 29 + [None] + [500.0],        # one missing day
    }
}

FAKE_PLACES = {
    "results": [
        {"name": "Begusarai", "admin1": "Bihar", "admin2": "Begusarai", "country": "India",
         "latitude": 25.4182, "longitude": 86.1272},
    ]
}


@pytest.fixture
def client(monkeypatch):
    async def fake_fetch_json(url, params):
        if url == weather.GEOCODE_URL:
            return FAKE_PLACES if params["name"].lower().startswith("begu") else {}
        return FAKE_FORECAST

    monkeypatch.setattr(weather, "fetch_json", fake_fetch_json)
    with TestClient(app) as c:
        yield c


def test_weather_averages_last_30_days(client):
    r = client.get("/weather", params={"lat": 25.42, "lon": 86.13})
    assert r.status_code == 200
    body = r.json()
    assert body["temperature"] == 28.0          # mean of 15x30 and 15x26; today's 99 ignored
    assert body["humidity"] == 80.0
    assert body["rainfall"] == 290.0            # 29 x 10 mm; the missing day is skipped
    assert body["period"] == {"days": 30, "start": "2026-09-01", "end": "2026-09-30"}


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
    with TestClient(app) as c:
        r = c.get("/weather", params={"lat": 25.42, "lon": 86.13})
    assert r.status_code == 502
    assert "timeout" in r.json()["detail"]
