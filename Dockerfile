FROM python:3.11-slim

# System deps for OpenCV/MediaPipe
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cached layer)
COPY test-backend/requirements-deploy.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY test-backend/ test-backend/
COPY asl-detector/ asl-detector/

WORKDIR /app/test-backend

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
