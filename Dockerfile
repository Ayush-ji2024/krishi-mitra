# Krishi Mitra API - production image.
# Used by Hugging Face Spaces (see scripts/deploy_space.py), but works on any
# Docker host: it listens on $PORT (default 7860, the port Spaces expects).
#
#   docker build -t krishi-mitra-api .
#   docker run -p 7860:7860 -e ALLOWED_ORIGINS=http://localhost:5173 krishi-mitra-api
#
# The trained models must exist in models/ before building (they are not in git).
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860

# Spaces runs containers as user 1000; use the same user everywhere.
RUN useradd --create-home --uid 1000 user
WORKDIR /app

# Dependencies first, so code changes don't reinstall them.
# CPU-only PyTorch: the default Linux wheel adds ~2 GB of CUDA we never use.
COPY requirements.txt .
RUN pip install torch==2.14.0 torchvision==0.29.0 --index-url https://download.pytorch.org/whl/cpu \
 && pip install -r requirements.txt

COPY backend/ backend/
COPY models/ models/

USER user
EXPOSE 7860
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
