"""
Train the soil image classifier with transfer learning (MobileNetV2).

Input : the clean split made by scripts/prepare_soil_data.py
        data/soil_split/{train,val,test}/<soil_class>/*.jpg
Output: models/soil_classifier.pt          (weights + class names + preprocessing info)
        reports/soil/metrics.json          (test accuracy, macro-F1, per-class report)
        reports/soil/confusion_matrix.png
        reports/soil/training_curves.png
        reports/soil/history.csv

Training happens in two phases:
  Phase 1 (head)     - the pretrained backbone is frozen; only the new last layer learns.
  Phase 2 (finetune) - the last few backbone blocks are unfrozen and trained with a
                       10x smaller learning rate, so the ImageNet knowledge is adjusted
                       gently instead of being destroyed.

The best epoch is chosen on the VALIDATION set (macro-F1). The TEST set is used exactly
once, at the very end, so the reported numbers are an honest estimate.

Quick smoke test (checks everything runs, takes ~1-2 min on CPU):
  python scripts/train_soil_classifier.py --head_epochs 1 --finetune_epochs 1
Full training:
  python scripts/train_soil_classifier.py
"""

import argparse
import copy
import csv
import json
import random
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # save plots to files, never open a window
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score,
                             classification_report, confusion_matrix, f1_score)
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from torchvision.models import MobileNet_V2_Weights, mobilenet_v2

IMG_SIZE = 224
MEAN = [0.485, 0.456, 0.406]  # ImageNet statistics: the backbone was trained with these
STD = [0.229, 0.224, 0.225]


# ----------------------------------------------------------------------------- setup
def set_seed(seed: int):
    """Same seed -> same shuffling, augmentation and init -> reproducible results."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def build_transforms():
    # Augmentation only for training: every epoch the model sees a slightly different
    # version of each photo, which matters a lot with only ~470 training images.
    # Hue jitter is kept tiny because colour is the main clue for soil type.
    train_tf = transforms.Compose([
        transforms.RandomResizedCrop(IMG_SIZE, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),       # soil photos have no "up" direction
        transforms.RandomRotation(20),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1, hue=0.02),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    # Validation / test: no randomness, so the score is the same every run.
    eval_tf = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(IMG_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    return train_tf, eval_tf


def build_loaders(data_dir: Path, batch_size: int, num_workers: int, seed: int):
    train_tf, eval_tf = build_transforms()
    for split in ("train", "val", "test"):
        if not (data_dir / split).is_dir():
            raise SystemExit(f"'{data_dir / split}' not found. Run scripts/prepare_soil_data.py first.")

    train_ds = datasets.ImageFolder(data_dir / "train", transform=train_tf)
    val_ds = datasets.ImageFolder(data_dir / "val", transform=eval_tf)
    test_ds = datasets.ImageFolder(data_dir / "test", transform=eval_tf)
    if not (train_ds.classes == val_ds.classes == test_ds.classes):
        raise SystemExit("train/val/test do not have the same class folders.")

    g = torch.Generator().manual_seed(seed)
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                          num_workers=num_workers, generator=g)
    val_dl = DataLoader(val_ds, batch_size=batch_size, num_workers=num_workers)
    test_dl = DataLoader(test_ds, batch_size=batch_size, num_workers=num_workers)
    return train_ds, train_dl, val_dl, test_dl


def class_weights(train_ds, device):
    """
    Rare classes get a bigger weight in the loss, so a mistake on 'clay'
    (80 images) costs more than a mistake on 'alluvial' (197 images).
    weight_c = total / (num_classes * count_c)
    """
    counts = np.bincount(train_ds.targets, minlength=len(train_ds.classes))
    weights = counts.sum() / (len(counts) * counts)
    return torch.tensor(weights, dtype=torch.float32, device=device), counts


# ----------------------------------------------------------------------------- model
def build_model(num_classes: int, pretrained: bool):
    weights = MobileNet_V2_Weights.DEFAULT if pretrained else None
    model = mobilenet_v2(weights=weights)
    # Replace the 1000-class ImageNet layer with a new layer for our soil classes.
    model.classifier[1] = nn.Linear(model.last_channel, num_classes)
    return model


def freeze_backbone(model, n_trainable_blocks: int):
    """Freeze every backbone block except the last `n_trainable_blocks`."""
    n_blocks = len(model.features)
    for i, block in enumerate(model.features):
        trainable = i >= n_blocks - n_trainable_blocks
        for p in block.parameters():
            p.requires_grad = trainable
    for p in model.classifier.parameters():
        p.requires_grad = True


def set_train_mode(model, n_trainable_blocks: int):
    """
    model.train() also switches BatchNorm layers to 'update statistics' mode.
    Frozen blocks must keep their ImageNet statistics, so they go back to eval().
    """
    model.train()
    n_blocks = len(model.features)
    for i, block in enumerate(model.features):
        if i < n_blocks - n_trainable_blocks:
            block.eval()


# ----------------------------------------------------------------------------- loops
def run_epoch(model, loader, criterion, device, optimizer=None, n_trainable_blocks=0):
    """One pass over `loader`. Trains if an optimizer is given, otherwise evaluates."""
    training = optimizer is not None
    if training:
        set_train_mode(model, n_trainable_blocks)
    else:
        model.eval()

    total_loss, preds, labels = 0.0, [], []
    with torch.set_grad_enabled(training):
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            out = model(x)
            loss = criterion(out, y)
            if training:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            total_loss += loss.item() * x.size(0)
            preds.extend(out.argmax(1).cpu().tolist())
            labels.extend(y.cpu().tolist())

    return {
        "loss": total_loss / len(loader.dataset),
        "acc": accuracy_score(labels, preds),
        "f1": f1_score(labels, preds, average="macro"),
        "preds": preds,
        "labels": labels,
    }


def train_phase(name, model, epochs, lr, n_trainable_blocks, train_dl, val_dl,
                criterion, device, state, patience=None):
    """Train for `epochs`; remember the best epoch (by val macro-F1) in `state`."""
    if epochs <= 0:
        return
    freeze_backbone(model, n_trainable_blocks)
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.Adam(params, lr=lr, weight_decay=1e-4)
    n_params = sum(p.numel() for p in params)
    print(f"\n--- Phase: {name} | trainable params: {n_params:,} | lr: {lr} ---")

    bad_epochs = 0
    for _ in range(epochs):
        state["epoch"] += 1
        t0 = time.time()
        tr = run_epoch(model, train_dl, criterion, device, optimizer, n_trainable_blocks)
        va = run_epoch(model, val_dl, criterion, device)
        state["history"].append({
            "epoch": state["epoch"], "phase": name,
            "train_loss": round(tr["loss"], 4), "train_acc": round(tr["acc"], 4),
            "val_loss": round(va["loss"], 4), "val_acc": round(va["acc"], 4),
            "val_f1": round(va["f1"], 4),
        })

        improved = (va["f1"] > state["best_f1"]) or (
            va["f1"] == state["best_f1"] and va["loss"] < state["best_loss"])
        if improved:
            state.update(best_f1=va["f1"], best_loss=va["loss"], best_epoch=state["epoch"])
            # deepcopy is essential: state_dict() only returns references to tensors
            # that keep changing during training (this was a bug in the old script).
            state["best_weights"] = copy.deepcopy(model.state_dict())
            bad_epochs = 0
        else:
            bad_epochs += 1

        print(f"Epoch {state['epoch']:>2} [{name}] "
              f"train loss {tr['loss']:.3f} acc {tr['acc']:.3f} | "
              f"val loss {va['loss']:.3f} acc {va['acc']:.3f} F1 {va['f1']:.3f} | "
              f"{time.time() - t0:.0f}s {'*best*' if improved else ''}")

        if patience is not None and bad_epochs >= patience:
            print(f"Early stopping: no val improvement for {patience} epochs.")
            break


# ----------------------------------------------------------------------------- reports
def save_reports(report_dir: Path, history, test, class_names, extra):
    report_dir.mkdir(parents=True, exist_ok=True)

    with open(report_dir / "history.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(history[0].keys()))
        writer.writeheader()
        writer.writerows(history)

    report = classification_report(test["labels"], test["preds"], target_names=class_names,
                                   output_dict=True, zero_division=0)
    metrics = {"test_accuracy": round(test["acc"], 4),
               "test_macro_f1": round(test["f1"], 4),
               "per_class": report, **extra}
    with open(report_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    cm = confusion_matrix(test["labels"], test["preds"], labels=list(range(len(class_names))))
    fig, ax = plt.subplots(figsize=(5, 5))
    ConfusionMatrixDisplay(cm, display_labels=class_names).plot(ax=ax, cmap="Greens", colorbar=False)
    ax.set_title(f"Soil classifier - test set\naccuracy {test['acc']:.1%}, macro-F1 {test['f1']:.3f}")
    fig.tight_layout()
    fig.savefig(report_dir / "confusion_matrix.png", dpi=150)
    plt.close(fig)

    epochs = [h["epoch"] for h in history]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    ax1.plot(epochs, [h["train_loss"] for h in history], label="train")
    ax1.plot(epochs, [h["val_loss"] for h in history], label="val")
    ax1.set_title("Loss"); ax1.set_xlabel("epoch"); ax1.legend()
    ax2.plot(epochs, [h["train_acc"] for h in history], label="train acc")
    ax2.plot(epochs, [h["val_acc"] for h in history], label="val acc")
    ax2.plot(epochs, [h["val_f1"] for h in history], label="val macro-F1", linestyle="--")
    ax2.set_title("Accuracy / F1"); ax2.set_xlabel("epoch"); ax2.set_ylim(0, 1); ax2.legend()
    fig.tight_layout()
    fig.savefig(report_dir / "training_curves.png", dpi=150)
    plt.close(fig)

    print("\n========== TEST SET RESULTS ==========")
    print(classification_report(test["labels"], test["preds"], target_names=class_names,
                                digits=3, zero_division=0))
    print("Confusion matrix (rows = true, columns = predicted):")
    print("          " + " ".join(f"{c[:8]:>8}" for c in class_names))
    for name, row in zip(class_names, cm):
        print(f"{name[:8]:>8}  " + " ".join(f"{v:>8}" for v in row))
    print("======================================")


# ----------------------------------------------------------------------------- main
def main():
    parser = argparse.ArgumentParser(description="Train the soil classifier (MobileNetV2 transfer learning).")
    parser.add_argument("--data_dir", default="data/soil_split")
    parser.add_argument("--model_out", default="models/soil_classifier.pt")
    parser.add_argument("--report_dir", default="reports/soil")
    parser.add_argument("--head_epochs", type=int, default=5, help="Phase 1: only the new last layer trains.")
    parser.add_argument("--finetune_epochs", type=int, default=15, help="Phase 2: last backbone blocks train too.")
    parser.add_argument("--unfreeze_blocks", type=int, default=4, help="How many backbone blocks to unfreeze in phase 2.")
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--patience", type=int, default=5, help="Early stopping patience in phase 2.")
    parser.add_argument("--num_workers", type=int, default=0, help="0 is safest on Windows.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no_pretrained", action="store_true", help="Train from scratch (for comparison only).")
    args = parser.parse_args()

    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    train_ds, train_dl, val_dl, test_dl = build_loaders(Path(args.data_dir), args.batch_size,
                                                        args.num_workers, args.seed)
    class_names = train_ds.classes
    weights, counts = class_weights(train_ds, device)
    print("Classes:", class_names)
    print("Train images per class:", dict(zip(class_names, counts.tolist())))
    print("Loss weights per class :", {c: round(w, 2) for c, w in zip(class_names, weights.tolist())})

    model = build_model(len(class_names), pretrained=not args.no_pretrained).to(device)
    criterion = nn.CrossEntropyLoss(weight=weights)
    state = {"epoch": 0, "history": [], "best_f1": -1.0, "best_loss": float("inf"),
             "best_epoch": 0, "best_weights": None}

    train_phase("head", model, args.head_epochs, args.lr, 0,
                train_dl, val_dl, criterion, device, state)
    train_phase("finetune", model, args.finetune_epochs, args.lr / 10, args.unfreeze_blocks,
                train_dl, val_dl, criterion, device, state, patience=args.patience)

    if state["best_weights"] is None:
        raise SystemExit("No epochs were run. Increase --head_epochs or --finetune_epochs.")

    # Load the best epoch (chosen on validation) and test it ONCE.
    model.load_state_dict(state["best_weights"])
    test = run_epoch(model, test_dl, criterion, device)
    print(f"\nBest epoch: {state['best_epoch']} (val macro-F1 {state['best_f1']:.3f})")

    out = Path(args.model_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Save everything the app needs, so nothing has to be hardcoded there.
    torch.save({
        "state_dict": model.state_dict(),
        "arch": "mobilenet_v2",
        "class_names": class_names,
        "img_size": IMG_SIZE,
        "mean": MEAN,
        "std": STD,
    }, out)
    print(f"Model saved to {out}")

    save_reports(Path(args.report_dir), state["history"], test, class_names, {
        "best_epoch": state["best_epoch"],
        "best_val_macro_f1": round(state["best_f1"], 4),
        "train_counts": dict(zip(class_names, counts.tolist())),
        "pretrained": not args.no_pretrained,
        "seed": args.seed,
    })
    print(f"Reports saved to {args.report_dir}/")


if __name__ == "__main__":
    main()