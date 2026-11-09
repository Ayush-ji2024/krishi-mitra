"""Crop recommendation: loads the scikit-learn pipeline saved by
scripts/train_crop_recommender.py and returns the top-k crops.

If the user's soil type is known, the ML ranking is adjusted with the FAO ECOCROP
soil suitability table (built by scripts/build_soil_suitability.py):
    final_score = model_probability x soil_weight
This is a SOFT re-ranking: a crop the model is very sure about stays on top even
on a "possible" soil; soil only decides between crops the model finds similar.
"""

import json
from pathlib import Path

import joblib
import pandas as pd

SUITABILITY_FILE = Path(__file__).with_name("soil_suitability.json")
SOIL_WEIGHT = {"good": 1.0, "possible": 0.7, "poor": 0.4}
# Crops the model gives less than 1% are not real suggestions - don't show them.
MIN_PROBABILITY = 0.01


class CropRecommender:
    def __init__(self, model_path: Path, suitability_path: Path = SUITABILITY_FILE):
        bundle = joblib.load(model_path)
        self.pipeline = bundle["pipeline"]
        self.model_name = bundle["model_name"]
        self.features = bundle["features"]
        self.classes = bundle["classes"]
        # min/max of each feature in the training data
        self.feature_ranges = bundle["feature_ranges"]

        with open(suitability_path) as f:
            self.suitability = json.load(f)["ratings"]  # {soil: {crop: rating}}

    @property
    def soil_types(self) -> list[str]:
        return sorted(self.suitability)

    def out_of_range_warnings(self, values: dict) -> list[dict]:
        """
        The model has only seen values inside the training ranges. Outside them
        it still answers, but it is guessing - so we tell the user.

        Each warning is structured (feature, value, min, max) so the frontend can
        show it in the user's language; `message` is an English version for API users.
        """
        warnings = []
        for f in self.features:
            lo, hi = self.feature_ranges[f]
            v = values[f]
            if v < lo or v > hi:
                warnings.append({
                    "code": "out_of_range",
                    "feature": f,
                    "value": v,
                    "min": round(float(lo), 1),
                    "max": round(float(hi), 1),
                    "message": (f"{f}={v:g} is outside the training range ({lo:.1f}-{hi:.1f}); "
                                "the recommendation may be unreliable."),
                })
        return warnings

    def recommend(self, values: dict, soil_type: str | None = None, top_k: int = 3) -> list[dict]:
        # One-row DataFrame with the columns in exactly the training order.
        x = pd.DataFrame([[values[f] for f in self.features]], columns=self.features)
        proba = self.pipeline.predict_proba(x)[0]

        results = []
        for crop, p in zip(self.pipeline.classes_, proba):
            rating = self.suitability[soil_type][crop] if soil_type else None
            weight = SOIL_WEIGHT[rating] if rating else 1.0
            results.append({
                "crop": crop,
                "probability": round(float(p), 4),   # what the ML model says
                "soil_suitability": rating,          # what FAO ECOCROP says (or None)
                "score": round(float(p) * weight, 4) # what we rank by
            })

        results.sort(key=lambda r: r["score"], reverse=True)
        # Drop near-zero crops, but always return at least the best one.
        useful = [r for r in results if r["probability"] >= MIN_PROBABILITY] or results[:1]
        return useful[:top_k]
