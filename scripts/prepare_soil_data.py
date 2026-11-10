"""
Prepare the soil image dataset for training.

What this script does:
  1. Collects every image from the original Train/ and test/ folders.
  2. Skips files that are not valid images (e.g. .DS_Store, corrupt files).
  3. Finds exact duplicate images (same file content) using an MD5 hash,
     so the same photo can never end up in both train and test.
  4. Finds NEAR-duplicates - the same photo resized, re-compressed, mirrored or
     with a watermark, and burst shots of the same field - with a perceptual
     hash (pHash). Photos whose hashes differ in <= --phash_threshold of 63 bits
     are grouped (also through chains: A~B and B~C puts A, B, C together) and
     only one photo per group is kept. Without this step, 34 of the 101 test
     photos had a near-copy in train: the model scored 100% on those and 86.6%
     on the rest, so the reported accuracy was inflated.
     Two rules, chosen by looking at pairs:
       - distance <= 6: always the same photo / scene;
       - distance 7-10: the same photo only if the average colour also matches
         (max channel difference <= 1.5 of 255). Different soil heaps on a black
         background can reach distance 8-10 but differ in colour (>= 2.2);
         among 400 such pairs this rule merged 326 same-label pairs and no
         different-label pair.
  5. Cleans class names ("Alluvial soil", "Black Soil" -> "alluvial", "black").
  6. Makes a fresh, stratified train / val / test split with a fixed seed.
  7. Writes the images into data/soil_split/ as RGB JPEGs (the original data is
     never touched) and a manifest.csv listing every image and its split.

Usage:
  python scripts/prepare_soil_data.py
  python scripts/prepare_soil_data.py --src data/soil_images --dst data/soil_split --overwrite
"""

import argparse
import csv
import hashlib
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from scipy.fft import dctn
from sklearn.model_selection import train_test_split


def clean_class_name(folder_name: str) -> str:
    """'Alluvial soil' -> 'alluvial', 'Black Soil' -> 'black'."""
    name = folder_name.strip().lower()
    if name.endswith(" soil"):
        name = name[: -len(" soil")]
    return name.strip().replace(" ", "_")


def file_md5(path: Path) -> str:
    """Fingerprint of the file's bytes. Identical files -> identical hash."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_valid_image(path: Path) -> bool:
    """True if Pillow can open and verify the file as an image."""
    try:
        with Image.open(path) as img:
            img.verify()
        return True
    except Exception:
        return False


def collect_images(src: Path):
    """Walk src/<split>/<class>/<file> and return (records, skipped_files)."""
    records = []   # dicts: path, label, source
    skipped = []
    split_dirs = [d for d in sorted(src.iterdir()) if d.is_dir()]
    if not split_dirs:
        raise FileNotFoundError(f"No folders found inside '{src}'. Expected Train/ and test/.")

    for split_dir in split_dirs:
        for class_dir in sorted(d for d in split_dir.iterdir() if d.is_dir()):
            label = clean_class_name(class_dir.name)
            for file in sorted(p for p in class_dir.rglob("*") if p.is_file()):
                if file.name.startswith(".") or not is_valid_image(file):
                    skipped.append(file)
                    continue
                records.append({"path": file, "label": label, "source": split_dir.name})
    return records, skipped


def remove_duplicates(records):
    """
    Keep one copy of each unique image.
    If the same image appears under two DIFFERENT labels we can't trust
    either label, so every copy of it is dropped.
    """
    by_hash = defaultdict(list)
    for r in records:
        r["hash"] = file_md5(r["path"])
        by_hash[r["hash"]].append(r)

    unique, n_dupes, conflicts = [], 0, []
    for h, group in by_hash.items():
        labels = {r["label"] for r in group}
        if len(labels) > 1:
            conflicts.append((h, sorted(labels), [str(r["path"]) for r in group]))
            continue
        unique.append(group[0])
        n_dupes += len(group) - 1
    return unique, n_dupes, conflicts


def phash(img: Image.Image) -> np.ndarray:
    """Perceptual hash: 63 bits describing the image's coarse structure.
    Grayscale 32x32 -> 2-D DCT -> top-left 8x8 low frequencies (without the
    overall-brightness term) -> 1 where above the median. Resizing, JPEG
    compression and small edits barely change it."""
    g = np.asarray(img.convert("L").resize((32, 32), Image.LANCZOS), dtype=np.float64)
    low = dctn(g, norm="ortho")[:8, :8].flatten()[1:]
    return low > np.median(low)


def remove_near_duplicates(records, threshold, loose_threshold=10, max_colour_diff=1.5):
    """
    Group near-duplicate photos (pHash distance <= threshold, or <= loose_threshold
    with the same average colour; mirrored copies count too) and keep one photo per
    group - the largest one. Groups that mix labels
    are dropped completely, like exact duplicates with conflicting labels.
    """
    hashes, mirrored, colours, sizes = [], [], [], []
    for r in records:
        with Image.open(r["path"]) as img:
            img = img.convert("RGB")
            hashes.append(phash(img))
            mirrored.append(phash(ImageOps.mirror(img)))
            colours.append(np.asarray(img.resize((8, 8), Image.BOX), dtype=np.float32).reshape(-1, 3).mean(0))
            sizes.append(img.width * img.height)
    h, hm, col = np.array(hashes), np.array(mirrored), np.array(colours)
    dist = np.minimum((h[:, None] != h[None]).sum(2), (h[:, None] != hm[None]).sum(2))
    colour_diff = np.abs(col[:, None] - col[None]).max(2)
    same = (dist <= threshold) | ((dist <= loose_threshold) & (colour_diff <= max_colour_diff))

    # Union-find: put every close pair into the same group.
    parent = list(range(len(records)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in zip(*np.where(np.triu(same, 1)), strict=True):
        parent[find(a)] = find(b)
    groups = defaultdict(list)
    for i in range(len(records)):
        groups[find(i)].append(i)

    kept, n_near, conflicts = [], 0, []
    for members in groups.values():
        labels = {records[i]["label"] for i in members}
        if len(labels) > 1:
            conflicts.append((sorted(labels), [str(records[i]["path"]) for i in members]))
            continue
        kept.append(records[max(members, key=lambda i: sizes[i])])
        n_near += len(members) - 1
    return kept, n_near, conflicts


def split_records(records, val_size, test_size, seed):
    """Stratified split: every split keeps the same class proportions."""
    labels = [r["label"] for r in records]
    train, temp = train_test_split(
        records, test_size=val_size + test_size, stratify=labels, random_state=seed
    )
    temp_labels = [r["label"] for r in temp]
    val, test = train_test_split(
        temp, test_size=test_size / (val_size + test_size),
        stratify=temp_labels, random_state=seed,
    )
    return {"train": train, "val": val, "test": test}


def save_as_jpeg(src: Path, out_path: Path):
    """
    Save every image as an RGB JPEG. The raw data mixes .jpg, .jpeg, .png, .webp
    and .gif, and PyTorch's ImageFolder silently SKIPS .gif files. Converting
    everything to one format means no image is lost and the model always gets
    3-channel RGB input (PNG/WebP can have a 4th transparency channel).
    """
    with Image.open(src) as img:
        img.convert("RGB").save(out_path, format="JPEG", quality=95)


def copy_split(splits, dst: Path):
    """Write images to dst/<split>/<label>/<hash>.jpg and a manifest.csv."""
    rows = []
    for split_name, items in splits.items():
        for r in items:
            out_dir = dst / split_name / r["label"]
            out_dir.mkdir(parents=True, exist_ok=True)
            # Name by hash: unique (duplicates are gone) and no filename clashes.
            out_path = out_dir / f"{r['hash'][:16]}.jpg"
            save_as_jpeg(r["path"], out_path)
            rows.append({
                "file": out_path.relative_to(dst).as_posix(),
                "label": r["label"],
                "split": split_name,
                "original": r["path"].as_posix(),
            })
    with open(dst / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "label", "split", "original"])
        writer.writeheader()
        writer.writerows(rows)


def print_report(total_found, skipped, n_dupes, conflicts, n_near, near_conflicts, splits):
    print("\n========== SOIL DATASET REPORT ==========")
    print(f"Files found (valid images) : {total_found}")
    print(f"Skipped (not images)       : {len(skipped)}")
    for s in skipped[:10]:
        print(f"    - {s}")
    print(f"Exact duplicates removed   : {n_dupes}")
    print(f"Conflicting-label images   : {len(conflicts)} (all copies dropped)")
    for _hash, labels, paths in conflicts[:10]:
        print(f"    - labels {labels}: {paths}")
    print(f"Near-duplicates removed    : {n_near}")
    print(f"Near-dup. label conflicts  : {len(near_conflicts)} groups, "
          f"{sum(len(p) for _, p in near_conflicts)} images (all dropped)")
    for labels, paths in near_conflicts[:10]:
        print(f"    - labels {labels}: {paths}")

    classes = sorted({r["label"] for items in splits.values() for r in items})
    counts = {name: Counter(r["label"] for r in items) for name, items in splits.items()}
    print(f"\n{'class':<12}{'train':>8}{'val':>8}{'test':>8}{'total':>8}")
    for c in classes:
        row = [counts[s][c] for s in ("train", "val", "test")]
        print(f"{c:<12}{row[0]:>8}{row[1]:>8}{row[2]:>8}{sum(row):>8}")
    totals = [len(splits[s]) for s in ("train", "val", "test")]
    print(f"{'TOTAL':<12}{totals[0]:>8}{totals[1]:>8}{totals[2]:>8}{sum(totals):>8}")
    print("=========================================\n")


def main():
    parser = argparse.ArgumentParser(description="Clean, de-duplicate and split the soil image dataset.")
    parser.add_argument("--src", default="data/soil_images", help="Original dataset (contains Train/ and test/).")
    parser.add_argument("--dst", default="data/soil_split", help="Where to write train/val/test folders.")
    parser.add_argument("--val_size", type=float, default=0.15)
    parser.add_argument("--test_size", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--phash_threshold", type=int, default=6,
                        help="Max pHash distance (of 63 bits) for two photos to count as near-duplicates.")
    parser.add_argument("--overwrite", action="store_true", help="Delete --dst first if it already exists.")
    args = parser.parse_args()

    src, dst = Path(args.src), Path(args.dst)
    if not src.is_dir():
        raise SystemExit(f"Source folder not found: {src}")
    if dst.exists():
        if not args.overwrite:
            raise SystemExit(f"'{dst}' already exists. Run again with --overwrite to rebuild it.")
        shutil.rmtree(dst)

    print(f"Scanning {src} ...")
    records, skipped = collect_images(src)
    unique, n_dupes, conflicts = remove_duplicates(records)
    print("Looking for near-duplicates (perceptual hash) ...")
    unique, n_near, near_conflicts = remove_near_duplicates(unique, args.phash_threshold)
    splits = split_records(unique, args.val_size, args.test_size, args.seed)

    print(f"Copying images to {dst} ...")
    copy_split(splits, dst)
    print_report(len(records), skipped, n_dupes, conflicts, n_near, near_conflicts, splits)
    print(f"Done. Manifest written to {dst / 'manifest.csv'}")


if __name__ == "__main__":
    main()
