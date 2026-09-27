"""Crop recommendation: loads the scikit-learn pipeline saved by
scripts/train_crop_recommender.py and returns the top-k crops."""

from pathlib import Path

import joblib
import pandas as pd


class CropRecommender:
    def __init__(self, model_path: Path):
        bundle = joblib.load(model_path)
        self.pipeline = bundle["pipeline"]
        self.model_name = bundle["model_name"]
        self.features = bundle["features"]
        self.classes = bundle["classes"]
        # min/max of each feature in the training data
        self.feature_ranges = bundle["feature_ranges"]

    def out_of_range_warnings(self, values: dict) -> list[str]:
        """
        The model has only seen values inside the training ranges. Outside them
        it still answers, but it is guessing - so we tell the user.
        """
        warnings = []
        for f in self.features:
            lo, hi = self.feature_ranges[f]
            v = values[f]
            if v < lo or v > hi:
                warnings.append(
                    f"{f}={v:g} is outside the training range ({lo:.1f}-{hi:.1f}); "
                    "the recommendation may be unreliable."
                )
        return warnings

    def recommend(self, values: dict, top_k: int = 3) -> list[dict]:
        # One-row DataFrame with the columns in exactly the training order.
        x = pd.DataFrame([[values[f] for f in self.features]], columns=self.features)
        proba = self.pipeline.predict_proba(x)[0]
        order = proba.argsort()[::-1][:top_k]
        return [
            {"crop": self.pipeline.classes_[i], "probability": round(float(proba[i]), 4)}
            for i in order
        ]
