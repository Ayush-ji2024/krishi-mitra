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

from backend.app.main import MODEL_DIR, app

# Skip (instead of failing) if the runtime models are missing, e.g. in a fresh
# clone where they were deleted; the ranking and weather tests still run.
_MODELS = [MODEL_DIR / "crop_recommender.joblib", MODEL_DIR / "soil_classifier.onnx"]
if not all(m.exists() for m in _MODELS):
    pytest.skip("trained models not found in models/ - train them first",
                allow_module_level=True)

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
    assert 1 <= len(crops) <= 3        # near-zero crops are hidden
    assert crops[0] == "rice"
    assert all(x["probability"] >= 0.01 for x in body["recommendations"])
    scores = [x["score"] for x in body["recommendations"]]
    assert scores == sorted(scores, reverse=True)
    # Without a soil type there is no re-ranking: score == probability.
    for x in body["recommendations"]:
        assert x["soil_suitability"] is None
        assert x["score"] == x["probability"]
    assert body["warnings"] == []


def test_recommend_with_soil_type(client):
    r = client.post("/recommend-crop", json={**RICE_SAMPLE, "soil_type": "clay"})
    assert r.status_code == 200
    recs = r.json()["recommendations"]
    assert all(x["soil_suitability"] in ("good", "possible", "poor") for x in recs)
    assert recs[0]["crop"] == "rice"   # rice is 'good' on every soil in ECOCROP


def test_unknown_soil_type_is_rejected(client):
    r = client.post("/recommend-crop", json={**RICE_SAMPLE, "soil_type": "sandy"})
    assert r.status_code == 422


def test_out_of_training_range_gives_warning(client):
    r = client.post("/recommend-crop", json={**RICE_SAMPLE, "rainfall": 1000})
    assert r.status_code == 200
    warnings = r.json()["warnings"]
    rain = [w for w in warnings if w["feature"] == "rainfall"]
    assert rain and rain[0]["code"] == "out_of_range"
    assert rain[0]["value"] > rain[0]["max"]


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
    assert isinstance(body["is_soil"], bool)
    assert body["soil_similarity"] is not None   # the reference file is loaded


@pytest.mark.parametrize("color", [(255, 255, 255), (0, 0, 0), (40, 90, 200)])
def test_plain_colour_is_not_soil(client, color):
    # A blank white / black / blue picture must not be called soil.
    r = client.post("/predict-soil", files={"file": ("x.png", _png_bytes(color), "image/png")})
    assert r.status_code == 200
    assert r.json()["is_soil"] is False


def test_screenshot_is_not_soil(client):
    with open("docs/screenshots/home.png", "rb") as f:
        r = client.post("/predict-soil", files={"file": ("home.png", f, "image/png")})
    assert r.json()["is_soil"] is False


def test_predict_soil_on_real_test_image(client):
    folder = Path("data/soil_split/test/red")
    images = sorted(folder.glob("*.jpg")) if folder.exists() else []
    if not images:
        pytest.skip("data/soil_split not found")
    with open(images[0], "rb") as f:
        r = client.post("/predict-soil", files={"file": (images[0].name, f, "image/jpeg")})
    assert r.status_code == 200
    assert r.json()["soil_type"] in ["alluvial", "black", "clay", "red"]
    assert r.json()["is_soil"] is True


def test_non_image_upload_is_rejected(client):
    r = client.post("/predict-soil", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 400
