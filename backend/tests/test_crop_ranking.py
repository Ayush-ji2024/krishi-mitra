"""
Unit tests for the soil re-ranking logic. They use a FAKE model, so they are
fast, need no trained files, and check the maths exactly.

    python -m pytest backend/tests/test_crop_ranking.py -v
"""

import numpy as np

from backend.app.crop import CropRecommender


class FakePipeline:
    """Always returns the same probabilities, whatever the input."""
    classes_ = np.array(["cotton", "watermelon", "rice"])

    def predict_proba(self, x):
        return np.array([[0.30, 0.45, 0.25]])


def make_recommender():
    rec = CropRecommender.__new__(CropRecommender)  # skip __init__ (no files needed)
    rec.pipeline = FakePipeline()
    rec.features = ["N"]
    rec.feature_ranges = {"N": [0, 140]}
    rec.suitability = {
        "black": {"cotton": "good", "watermelon": "poor", "rice": "good"},
    }
    return rec


def test_without_soil_order_follows_model():
    top = make_recommender().recommend({"N": 50}, soil_type=None)
    assert [r["crop"] for r in top] == ["watermelon", "cotton", "rice"]


def test_black_soil_moves_cotton_above_watermelon():
    # watermelon: 0.45 x 0.4 (poor) = 0.18 ; cotton: 0.30 x 1.0 = 0.30 ; rice: 0.25
    top = make_recommender().recommend({"N": 50}, soil_type="black")
    assert [r["crop"] for r in top] == ["cotton", "rice", "watermelon"]
    assert top[2]["score"] == 0.18
    assert top[2]["probability"] == 0.45   # the model's opinion is still reported


def test_near_zero_crops_are_hidden():
    rec = make_recommender()

    class ConfidentPipeline(FakePipeline):
        def predict_proba(self, x):
            return np.array([[0.004, 0.001, 0.995]])  # only rice is a real option

    rec.pipeline = ConfidentPipeline()
    top = rec.recommend({"N": 50})
    assert [r["crop"] for r in top] == ["rice"]


def test_at_least_one_result_is_always_returned():
    rec = make_recommender()

    class UnsurePipeline(FakePipeline):
        def predict_proba(self, x):
            return np.array([[0.004, 0.003, 0.003]])  # nothing above 1%

    rec.pipeline = UnsurePipeline()
    top = rec.recommend({"N": 50})
    assert len(top) == 1 and top[0]["crop"] == "cotton"


def test_out_of_range_warning():
    warnings = make_recommender().out_of_range_warnings({"N": 200})
    assert len(warnings) == 1 and "N=200" in warnings[0]
