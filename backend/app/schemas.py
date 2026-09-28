"""Request/response shapes. FastAPI uses these to validate input automatically
and to build the interactive docs at /docs."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

SoilType = Literal["alluvial", "black", "clay", "red"]
Suitability = Literal["good", "possible", "poor"]


class CropRequest(BaseModel):
    # Hard physical limits: anything outside is rejected with HTTP 422.
    # (Values that are possible but unusual only produce a warning - see crop.py.)
    N: float = Field(..., ge=0, le=500, description="Nitrogen in soil (kg/ha)")
    P: float = Field(..., ge=0, le=500, description="Phosphorus in soil (kg/ha)")
    K: float = Field(..., ge=0, le=500, description="Potassium in soil (kg/ha)")
    temperature: float = Field(..., ge=-10, le=60, description="Temperature (deg C)")
    humidity: float = Field(..., ge=0, le=100, description="Relative humidity (%)")
    ph: float = Field(..., ge=0, le=14, description="Soil pH")
    rainfall: float = Field(..., ge=0, le=5000, description="Rainfall (mm)")
    soil_type: Optional[SoilType] = Field(
        None, description="Optional. If given, crops are re-ranked by soil suitability.")

    model_config = {
        "json_schema_extra": {
            "examples": [{"N": 90, "P": 42, "K": 43, "temperature": 20.9,
                          "humidity": 82.0, "ph": 6.5, "rainfall": 202.9,
                          "soil_type": "alluvial"}]
        }
    }


class CropSuggestion(BaseModel):
    crop: str
    probability: float = Field(..., description="ML model probability")
    soil_suitability: Optional[Suitability] = Field(
        None, description="FAO ECOCROP rating for the given soil (null if no soil given)")
    score: float = Field(..., description="probability x soil weight; results are sorted by this")


class CropResponse(BaseModel):
    recommendations: list[CropSuggestion]
    warnings: list[str]
    model: str


class SoilResponse(BaseModel):
    soil_type: str
    confidence: float
    probabilities: dict[str, float]
    low_confidence: bool
