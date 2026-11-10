"""
Export the trained soil classifier (PyTorch) to ONNX for the web API.

Why: the API only needs to RUN the model, not train it. onnxruntime does that
with ~10x less memory than importing PyTorch, so the backend fits on small free
servers (e.g. Render's 512 MB). PyTorch is then only needed for training.

Everything the API needs is stored inside the .onnx file as metadata:
class names, image size and the normalisation mean/std.

Usage (needs the training requirements, i.e. PyTorch):
  python scripts/export_soil_onnx.py
  -> models/soil_classifier.onnx   (checked against PyTorch before saving)
"""

import argparse
import json
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch
import torch.nn as nn
from torchvision.models import mobilenet_v2


def load_torch_model(path: Path):
    ckpt = torch.load(path, map_location="cpu", weights_only=True)
    if ckpt.get("arch") != "mobilenet_v2":
        raise SystemExit(f"Unsupported architecture: {ckpt.get('arch')}")
    model = mobilenet_v2(weights=None)
    model.classifier[1] = nn.Linear(model.last_channel, len(ckpt["class_names"]))
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model, ckpt


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--checkpoint", type=Path, default=Path("models/soil_classifier.pt"))
    parser.add_argument("--out", type=Path, default=Path("models/soil_classifier.onnx"))
    args = parser.parse_args()

    model, ckpt = load_torch_model(args.checkpoint)
    size = ckpt["img_size"]

    # Batch size is dynamic, so the API could score several photos at once.
    dummy = torch.randn(1, 3, size, size)
    torch.onnx.export(
        model, dummy, args.out,
        input_names=["image"], output_names=["logits"],
        dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17, dynamo=False,
    )

    # Store what the API needs to preprocess images and name the classes.
    onnx_model = onnx.load(args.out)
    meta = {
        "arch": ckpt["arch"],
        "class_names": json.dumps(ckpt["class_names"]),
        "img_size": str(size),
        "mean": json.dumps(list(ckpt["mean"])),
        "std": json.dumps(list(ckpt["std"])),
    }
    for key, value in meta.items():
        entry = onnx_model.metadata_props.add()
        entry.key, entry.value = key, value
    onnx.checker.check_model(onnx_model)
    onnx.save(onnx_model, args.out)

    # Sanity check: ONNX must give the same answer as PyTorch.
    session = ort.InferenceSession(str(args.out), providers=["CPUExecutionProvider"])
    x = torch.randn(8, 3, size, size)
    with torch.no_grad():
        expected = model(x).numpy()
    got = session.run(None, {"image": x.numpy()})[0]
    diff = float(np.abs(expected - got).max())
    same_class = bool((expected.argmax(1) == got.argmax(1)).all())
    print(f"Saved {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")
    print(f"Max difference vs PyTorch: {diff:.2e}  |  same predicted class: {same_class}")
    if diff > 1e-3 or not same_class:
        raise SystemExit("ONNX output does not match PyTorch - not safe to use.")


if __name__ == "__main__":
    main()
