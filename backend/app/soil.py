"""Soil classification: runs the MobileNetV2 model exported to ONNX by
scripts/export_soil_onnx.py and predicts the soil type of a photo.

The API uses onnxruntime instead of PyTorch: same answers, ~10x less memory,
so the backend fits on small free servers. PyTorch is only needed for training.
"""

import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

# Below this confidence we ask the user to retake the photo or pick the soil manually.
LOW_CONFIDENCE = 0.60


class SoilClassifier:
    def __init__(self, model_path: Path):
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1  # small free servers have ~1 CPU
        self.session = ort.InferenceSession(str(model_path), options, providers=["CPUExecutionProvider"])

        # Class names and preprocessing settings are stored inside the .onnx file.
        meta = self.session.get_modelmeta().custom_metadata_map
        if meta.get("arch") != "mobilenet_v2":
            raise ValueError(f"Unsupported architecture: {meta.get('arch')}")
        self.class_names = json.loads(meta["class_names"])
        self.size = int(meta["img_size"])
        self.resize_to = round(self.size / 0.875)  # 224 -> 256, as in training
        self.mean = np.array(json.loads(meta["mean"]), dtype=np.float32).reshape(3, 1, 1)
        self.std = np.array(json.loads(meta["std"]), dtype=np.float32).reshape(3, 1, 1)
        self.input_name = self.session.get_inputs()[0].name

    def preprocess(self, image: Image.Image) -> np.ndarray:
        """EXACTLY the validation/test preprocessing used in training, without torchvision:
        Resize(256) on the shorter side -> CenterCrop(224) -> scale to 0..1 -> Normalize."""
        image = image.convert("RGB")
        w, h = image.size
        short, long = (w, h) if w <= h else (h, w)
        new_short, new_long = self.resize_to, int(self.resize_to * long / short)
        new_w, new_h = (new_short, new_long) if w <= h else (new_long, new_short)
        image = image.resize((new_w, new_h), Image.BILINEAR)

        top = int(round((new_h - self.size) / 2.0))
        left = int(round((new_w - self.size) / 2.0))
        image = image.crop((left, top, left + self.size, top + self.size))

        x = np.asarray(image, dtype=np.float32).transpose(2, 0, 1) / 255.0  # HWC -> CHW
        x = (x - self.mean) / self.std
        return x[np.newaxis]  # add batch dimension

    def predict(self, image: Image.Image) -> dict:
        logits = self.session.run(None, {self.input_name: self.preprocess(image)})[0][0]
        exp = np.exp(logits - logits.max())  # softmax, numerically stable
        probs = exp / exp.sum()
        best = int(probs.argmax())
        confidence = float(probs[best])
        return {
            "soil_type": self.class_names[best],
            "confidence": round(confidence, 4),
            "probabilities": {c: round(float(p), 4) for c, p in zip(self.class_names, probs)},
            "low_confidence": confidence < LOW_CONFIDENCE,
        }
