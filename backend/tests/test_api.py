"""
API tests. They use the REAL trained models in models/, so train both first.

Run from the project root:
    python -m pytest backend/tests -v
"""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.main import app

# First row of the Kaggle dataset - a textbook "rice" sample.
RICE_SAMPLE = {"N": 90, "P": 42, "K": 43, "temperature": 20.88,
               "humidity": 82.0, "ph": 6.5, "rainfall": 202.9}


@pytest.fixture(scope="module")
def client():
    # "with" runs the lifespan function, so the models get loaded.
    with TestClient(app) as c:
        yield c


def test_health_both_models_loaded(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok", body


def test_meta_lists_crops_and_soils(client):
    body = client.get("/meta").json()
    assert len(body["crops"]) == 22
    assert body["soil_types"] == ["alluvial", "black", "clay", "red"]
    assert set(body["features"]) == set(RICE_SAMPLE)


def test_recommend_rice_sample(client):
    r = client.post("/recommend-crop", json=RICE_SAMPLE)
    assert r.status_code == 200
    body = r.json()
    crops = [x["crop"] for x in body["recommendations"]]
    assert len(crops) == 3
    assert "rice" in crops
    probs = [x["probability"] for x in body["recommendations"]]
    assert probs == sorted(probs, reverse=True)
    assert body["warnings"] == []


def test_out_of_training_range_gives_warning(client):
    r = client.post("/recommend-crop", json={**RICE_SAMPLE, "rainfall": 1000})
    assert r.status_code == 200
    assert any("rainfall" in w for w in r.json()["warnings"])


def test_impossible_ph_is_rejected(client):
    r = client.post("/recommend-crop", json={**RICE_SAMPLE, "ph": 20})
    assert r.status_code == 422


def test_missing_field_is_rejected(client):
    body = dict(RICE_SAMPLE)
    body.pop("N")
    assert client.post("/recommend-crop", json=body).status_code == 422


def _png_bytes(color=(150, 90, 60)):
    buf = io.BytesIO()
    Image.new("RGB", (300, 300), color).save(buf, format="PNG")
    return buf.getvalue()


def test_predict_soil_returns_valid_shape(client):
    r = client.post("/predict-soil", files={"file": ("soil.png", _png_bytes(), "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert body["soil_type"] in body["probabilities"]
    assert abs(sum(body["probabilities"].values()) - 1) < 0.01
    assert 0 <= body["confidence"] <= 1


def test_predict_soil_on_real_test_image(client):
    folder = Path("data/soil_split/test/red")
    images = sorted(folder.glob("*.jpg")) if folder.exists() else []
    if not images:
        pytest.skip("data/soil_split not found")
    with open(images[0], "rb") as f:
        r = client.post("/predict-soil", files={"file": (images[0].name, f, "image/jpeg")})
    assert r.status_code == 200
    assert r.json()["soil_type"] in ["alluvial", "black", "clay", "red"]


def test_non_image_upload_is_rejected(client):
    r = client.post("/predict-soil", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 400
