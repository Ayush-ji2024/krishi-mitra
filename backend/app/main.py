"""
Krishi Mitra API.

Run from the project root:
    uvicorn backend.app.main:app --reload
Then open http://127.0.0.1:8000/docs
"""

import io
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError

from . import weather
from .schemas import CropRequest, CropResponse, Place, SoilResponse, WeatherResponse

logger = logging.getLogger("krishi-mitra")

MODEL_DIR = Path(os.getenv("MODEL_DIR", "models"))
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
# Which websites may call this API from the browser (the React dev server by default).
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")


def _load(name: str, loader):
    """Load one model. If it fails, keep the server running and report it in /health."""
    try:
        model = loader()
        logger.info("Loaded %s", name)
        return model, None
    except Exception as e:  # noqa: BLE001 - we want to report any failure
        logger.exception("Could not load %s", name)
        return None, f"{type(e).__name__}: {e}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs ONCE when the server starts: models are loaded a single time and
    # reused for every request (loading per request would be very slow).
    def load_crop():
        from .crop import CropRecommender
        return CropRecommender(MODEL_DIR / "crop_recommender.joblib")

    def load_soil():
        from .soil import SoilClassifier  # imports torch only when needed
        return SoilClassifier(MODEL_DIR / "soil_classifier.pt")

    app.state.crop, app.state.crop_error = _load("crop model", load_crop)
    app.state.soil, app.state.soil_error = _load("soil model", load_soil)
    yield


app = FastAPI(
    title="Krishi Mitra API",
    description="Soil type from a photo, and crop recommendations from soil and weather values.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _require(request: Request, name: str):
    model = getattr(request.app.state, name, None)
    if model is None:
        error = getattr(request.app.state, f"{name}_error", "not loaded")
        raise HTTPException(status_code=503, detail=f"{name} model unavailable ({error})")
    return model


@app.get("/health")
def health(request: Request):
    s = request.app.state
    return {
        "status": "ok" if (s.crop and s.soil) else "degraded",
        "crop_model": "loaded" if s.crop else s.crop_error,
        "soil_model": "loaded" if s.soil else s.soil_error,
    }


@app.get("/meta")
def meta(request: Request):
    """Everything the frontend needs to build its form."""
    crop = _require(request, "crop")
    soil = request.app.state.soil
    return {
        "features": crop.features,
        "feature_ranges": crop.feature_ranges,
        "crops": crop.classes,
        "soil_types": soil.class_names if soil else crop.soil_types,
        "soil_suitability": crop.suitability,
    }


@app.post("/predict-soil", response_model=SoilResponse)
async def predict_soil(request: Request, file: UploadFile = File(...)):
    soil = _require(request, "soil")

    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image is larger than 5 MB.")
    try:
        image = Image.open(io.BytesIO(data))
        image.load()  # actually decode it, so broken files fail here
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image.")

    return soil.predict(image)


@app.post("/recommend-crop", response_model=CropResponse)
def recommend_crop(body: CropRequest, request: Request):
    crop = _require(request, "crop")
    values = body.model_dump()
    return {
        "recommendations": crop.recommend(values, soil_type=body.soil_type, top_k=3),
        "warnings": crop.out_of_range_warnings(values),
        "model": crop.model_name,
    }


@app.get("/places", response_model=list[Place])
async def places(q: str = Query(..., min_length=2, max_length=100, description="Village / town / city name")):
    """Find a place in India by name, to get its coordinates."""
    try:
        return await weather.search_places(q)
    except weather.WeatherError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/weather", response_model=WeatherResponse)
async def recent_weather(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
):
    """Last 30 days of weather for a location, ready to fill the crop form."""
    try:
        return await weather.recent_weather(lat, lon)
    except weather.WeatherError as e:
        # 502 Bad Gateway = "a service I depend on failed", not the user's fault.
        raise HTTPException(status_code=502, detail=str(e))
