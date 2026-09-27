"""Soil classification: loads the MobileNetV2 checkpoint saved by
scripts/train_soil_classifier.py and predicts the soil type of a photo."""

from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from torchvision.models import mobilenet_v2

# Below this confidence we ask the user to retake the photo or pick the soil manually.
LOW_CONFIDENCE = 0.60


class SoilClassifier:
    def __init__(self, model_path: Path):
        # weights_only=True: only load tensors and plain data, never run code
        # from the file (safer; the checkpoint contains nothing else).
        ckpt = torch.load(model_path, map_location="cpu", weights_only=True)
        if ckpt.get("arch") != "mobilenet_v2":
            raise ValueError(f"Unsupported architecture: {ckpt.get('arch')}")

        self.class_names = ckpt["class_names"]
        model = mobilenet_v2(weights=None)
        model.classifier[1] = nn.Linear(model.last_channel, len(self.class_names))
        model.load_state_dict(ckpt["state_dict"])
        model.eval()
        self.model = model

        # EXACTLY the same preprocessing as the validation/test data in training.
        size = ckpt["img_size"]
        self.transform = transforms.Compose([
            transforms.Resize(round(size / 0.875)),  # 224 -> 256, as in training
            transforms.CenterCrop(size),
            transforms.ToTensor(),
            transforms.Normalize(ckpt["mean"], ckpt["std"]),
        ])

    @torch.no_grad()
    def predict(self, image: Image.Image) -> dict:
        x = self.transform(image.convert("RGB")).unsqueeze(0)  # add batch dimension
        probs = torch.softmax(self.model(x), dim=1)[0]
        best = int(probs.argmax())
        confidence = float(probs[best])
        return {
            "soil_type": self.class_names[best],
            "confidence": round(confidence, 4),
            "probabilities": {c: round(float(p), 4) for c, p in zip(self.class_names, probs)},
            "low_confidence": confidence < LOW_CONFIDENCE,
        }
