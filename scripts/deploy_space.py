"""
Deploy the backend to a Hugging Face Space (Docker SDK, free CPU hardware).

The trained models are not in git, so they are uploaded from your local models/
folder together with the backend code and the Dockerfile. Hugging Face then
builds the image and starts the API at  https://<user>-<space>.hf.space

One-time setup:
  1. Create a free account at https://huggingface.co
  2. Create a token with "write" access: https://huggingface.co/settings/tokens
  3. pip install -r requirements-dev.txt

Usage (from the project root):
  # Windows PowerShell:  $env:HF_TOKEN="hf_..."      macOS/Linux:  export HF_TOKEN=hf_...
  python scripts/deploy_space.py --space <your-hf-username>/krishi-mitra-api

  # only build the upload folder and show what would be sent:
  python scripts/deploy_space.py --space <user>/krishi-mitra-api --dry-run

After the first deploy, set the CORS variable in the Space settings
(Settings -> Variables and secrets -> New variable):
  ALLOWED_ORIGINS = https://<your-site>.vercel.app
"""

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Exactly what the Docker image needs (see Dockerfile and .dockerignore).
FILES = ["Dockerfile", "requirements.txt", "backend/__init__.py"]
APP_DIR = "backend/app"
MODELS = ["models/crop_recommender.joblib", "models/soil_classifier.pt"]

# The Space's README: the YAML header tells Hugging Face how to run it.
SPACE_README = """---
title: Krishi Mitra API
emoji: 🌾
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
short_description: Soil type from a photo and crop recommendations (FastAPI)
---

# Krishi Mitra API

Backend of [Krishi Mitra](https://github.com/Ayush-ji2024/krishi-mitra): a FastAPI
service with a MobileNetV2 soil classifier and a Random Forest crop recommender.

Interactive API docs: open `/docs` on this Space's URL.

This Space is deployed from the GitHub repository with `scripts/deploy_space.py`;
edit the code there, not here.
"""


def build_folder(dest: Path) -> list[str]:
    missing = [m for m in MODELS if not (ROOT / m).exists()]
    if missing:
        sys.exit(f"Missing trained models: {missing}. Train them first (see README).")

    for rel in FILES + MODELS:
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dest / rel)
    shutil.copytree(ROOT / APP_DIR, dest / APP_DIR,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (dest / "README.md").write_text(SPACE_README, encoding="utf-8")
    return sorted(str(p.relative_to(dest)).replace("\\", "/") for p in dest.rglob("*") if p.is_file())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--space", required=True, help="Space id, e.g. ayush-ji2024/krishi-mitra-api")
    parser.add_argument("--private", action="store_true", help="create the Space as private")
    parser.add_argument("--dry-run", action="store_true", help="build the folder, upload nothing")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        files = build_folder(Path(tmp))
        size = sum((Path(tmp) / f).stat().st_size for f in files) / 1e6
        print(f"{len(files)} files, {size:.1f} MB:")
        for f in files:
            print("  ", f)
        if args.dry_run:
            print("Dry run - nothing uploaded.")
            return

        token = os.getenv("HF_TOKEN")
        if not token:
            sys.exit("Set HF_TOKEN to a Hugging Face token with write access first.")

        from huggingface_hub import HfApi  # imported here: only needed for a real deploy

        api = HfApi(token=token)
        api.create_repo(args.space, repo_type="space", space_sdk="docker",
                        private=args.private, exist_ok=True)
        # delete_patterns removes files that no longer exist locally.
        api.upload_folder(repo_id=args.space, repo_type="space", folder_path=tmp,
                          commit_message="Deploy from GitHub repo", delete_patterns="*")

    user, name = args.space.split("/")
    print(f"\nUploaded. Hugging Face is now building the image (a few minutes):")
    print(f"  Build logs : https://huggingface.co/spaces/{args.space}")
    print(f"  API        : https://{user.lower()}-{name.lower().replace('_', '-')}.hf.space/health")


if __name__ == "__main__":
    main()
