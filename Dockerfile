# Krishi Mitra API - production image (optional: Render uses render.yaml instead).
# No PyTorch: the soil model runs with onnxruntime, so the image is small.
#
#   docker build -t krishi-mitra-api .
#   docker run -p 8000:8000 -e ALLOWED_ORIGINS=http://localhost:5173 krishi-mitra-api
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

RUN useradd --create-home --uid 1000 user
WORKDIR /app

# Dependencies first, so code changes don't reinstall them.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ backend/
COPY models/crop_recommender.joblib models/soil_classifier.onnx models/

USER user
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
