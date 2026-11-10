"""
Calibrate the "is this a soil photo?" check of the soil classifier.

Method (deep k-nearest-neighbours, Sun et al., ICML 2022):
  1. Every TRAINING soil photo is turned into the model's 1280-number feature
     "fingerprint" (L2-normalised). These form the reference bank.
  2. A new photo's score = cosine similarity to its k-th most similar
     reference photo. Soil photos sit close to other soil photos; a selfie,
     a building or a screenshot does not.
  3. The threshold is chosen on the VALIDATION soil photos only, so that
     (100 - reject_pct)% of real soil photos pass.
  4. It is then measured, once, on the TEST soil photos and on non-soil photos.

Choosing the method without fooling ourselves: the non-soil photos are
de-duplicated and split in two halves (by a hash, so the split is fixed).
The method was chosen on validation soil photos + the SELECTION half (57 photos),
caught = share of non-soil photos rejected at the same 98% soil pass rate:
    kNN k=1  AUROC 0.983, caught 91%  |  kNN k=5  AUROC 0.981, caught 79%
    Mahalanobis on normalised features (class means, Ledoit-Wolf)  AUROC 0.990, caught 93%
k=1 was kept: nearly as good as Mahalanobis, much simpler to explain and a
smaller file. The reported numbers use only the EVALUATION half.

For comparison it also reports how well the classifier's own confidence
(max softmax probability) separates soil from non-soil - the naive approach.

Non-soil photos for evaluation (not used to pick the threshold):
  data/ood/**  - any images, e.g. random photos from https://picsum.photos
  + generated images (plain colours, noise) and the app's own screenshots.

Usage:
  python scripts/calibrate_soil_ood.py
  -> models/soil_reference.npz      (used by the API)
  -> reports/soil/ood_metrics.json  and  reports/soil/ood_scores.png
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.soil import SoilClassifier  # noqa: E402  - same preprocessing as the API

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def images_in(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.suffix.lower() in IMAGE_EXT)


def synthetic_images(seed: int = 0) -> list[Image.Image]:
    """Things a phone camera might send that are clearly not soil."""
    rng = np.random.default_rng(seed)
    out = [Image.new("RGB", (400, 300), c) for c in
           [(255, 255, 255), (0, 0, 0), (40, 90, 200), (30, 160, 60), (220, 30, 30), (128, 128, 128)]]
    out += [Image.fromarray(rng.integers(0, 256, (300, 400, 3), dtype=np.uint8)) for _ in range(4)]
    gradient = np.tile(np.linspace(0, 255, 400, dtype=np.uint8), (300, 1))
    out.append(Image.fromarray(np.stack([gradient, gradient[::-1], np.full_like(gradient, 120)], axis=2)))
    return out


def embed(clf: SoilClassifier, images) -> tuple[np.ndarray, np.ndarray]:
    """Features (L2-normalised) and max softmax probability of each image."""
    feats, msp = [], []
    for img in images:
        if isinstance(img, Path):
            img = Image.open(img)
        logits, f = clf.run(img)
        p = np.exp(logits - logits.max())
        msp.append(float((p / p.sum()).max()))
        feats.append(f / (np.linalg.norm(f) + 1e-12))
    return np.array(feats, dtype=np.float32), np.array(msp)


def knn_score(bank: np.ndarray, feats: np.ndarray, k: int) -> np.ndarray:
    sims = feats @ bank.T
    return np.sort(sims, axis=1)[:, -k]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split-dir", type=Path, default=Path("data/soil_split"))
    parser.add_argument("--ood-dir", type=Path, default=Path("data/ood"))
    parser.add_argument("--model", type=Path, default=Path("models/soil_classifier.onnx"))
    parser.add_argument("--out", type=Path, default=Path("models/soil_reference.npz"))
    parser.add_argument("--reports", type=Path, default=Path("reports/soil"))
    parser.add_argument("--k", type=int, default=1)
    parser.add_argument("--reject-pct", type=float, default=2.0,
                        help="% of validation soil photos allowed to be rejected (default 2)")
    args = parser.parse_args()

    clf = SoilClassifier(args.model)  # no reference yet: we are building it
    split = {s: images_in(args.split_dir / s) for s in ("train", "val", "test")}
    if not all(split.values()):
        raise SystemExit(f"Soil split not found in {args.split_dir} - run prepare_soil_data.py first.")

    ood_sets = {
        "random photos (data/ood)": images_in(args.ood_dir),
        "generated (colours, noise)": synthetic_images(),
        "app screenshots": images_in(Path("docs/screenshots")),
    }
    ood_sets = {name: imgs for name, imgs in ood_sets.items() if imgs}
    print("Images: " + ", ".join(f"{s} {len(v)}" for s, v in split.items())
          + " | non-soil: " + ", ".join(f"{n} {len(v)}" for n, v in ood_sets.items()))

    bank, _ = embed(clf, split["train"])
    val_f, val_msp = embed(clf, split["val"])
    test_f, test_msp = embed(clf, split["test"])
    ood = {name: embed(clf, imgs) for name, imgs in ood_sets.items()}

    val_s = knn_score(bank, val_f, args.k)
    threshold = float(np.percentile(val_s, args.reject_pct))
    test_s = knn_score(bank, test_f, args.k)
    ood_s = {name: knn_score(bank, f, args.k) for name, (f, _) in ood.items()}

    # De-duplicate the non-soil photos and keep only the EVALUATION half (see docstring).
    keep, seen = {}, set()
    for name, (f, _) in ood.items():
        rows = []
        for i, row in enumerate(f):
            key = hashlib.md5(np.round(row, 3).tobytes()).hexdigest()
            if key not in seen and int(key, 16) % 2 == 1:
                rows.append(i)
            seen.add(key)
        keep[name] = np.array(rows, dtype=int)
    ood_s = {name: s[keep[name]] for name, s in ood_s.items() if len(keep[name])}
    all_ood_s = np.concatenate(list(ood_s.values()))
    all_ood_msp = np.concatenate([ood[name][1][keep[name]] for name in ood_s])
    labels = np.r_[np.ones(len(test_s)), np.zeros(len(all_ood_s))]  # 1 = soil

    metrics = {
        "method": f"cosine similarity to the k-th nearest training photo (k={args.k})",
        "threshold": round(threshold, 4),
        "threshold_rule": f"{args.reject_pct}th percentile of validation soil scores",
        "train_reference_photos": len(bank),
        "test_soil_accepted": round(float((test_s >= threshold).mean()), 3),
        "non_soil_rejected": {name: round(float((s < threshold).mean()), 3) for name, s in ood_s.items()},
        "non_soil_rejected_overall": round(float((all_ood_s < threshold).mean()), 3),
        "auroc_knn": round(float(roc_auc_score(labels, np.r_[test_s, all_ood_s])), 4),
        "auroc_max_softmax_baseline": round(float(roc_auc_score(labels, np.r_[test_msp, all_ood_msp])), 4),
        "non_soil_photos_evaluated": {name: len(s) for name, s in ood_s.items()},
        "note": "non-soil numbers use only the de-duplicated evaluation half (see script docstring)",
    }
    print(json.dumps(metrics, indent=2))

    np.savez_compressed(args.out, features=bank.astype(np.float16), k=args.k, threshold=threshold)
    print(f"Saved {args.out} ({args.out.stat().st_size / 1e6:.2f} MB)")

    args.reports.mkdir(parents=True, exist_ok=True)
    (args.reports / "ood_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(7, 3.6))
    bins = np.linspace(min(all_ood_s.min(), test_s.min()) - 0.02, 1.0, 40)
    ax.hist(test_s, bins=bins, alpha=0.75, label=f"soil (test, n={len(test_s)})", color="#8a5a2b")
    ax.hist(all_ood_s, bins=bins, alpha=0.6, label=f"not soil (held-out, n={len(all_ood_s)})", color="#4a7bd0")
    ax.axvline(threshold, color="black", linestyle="--", label=f"threshold {threshold:.3f}")
    ax.set_xlabel("similarity to the most similar training soil photo" if args.k == 1
                  else f"similarity to the {args.k}th most similar training soil photo")
    ax.set_ylabel("photos")
    ax.set_title("Is it a soil photo?")
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.reports / "ood_scores.png", dpi=130)
    print(f"Saved {args.reports / 'ood_scores.png'}")


if __name__ == "__main__":
    main()
