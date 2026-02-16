FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

# ✅ CRITICAL CHANGES:
# - Use sync workers (not uvicorn)
# - Increase timeout to 900s
# - Use /dev/shm for temp files (faster)
CMD ["gunicorn", "app:app", \
     "--workers", "2", \
     "--threads", "2", \
     "--worker-class", "sync", \
     "--bind", "0.0.0.0:8080", \
     "--timeout", "900", \
     "--keep-alive", "120", \
     "--worker-tmp-dir", "/dev/shm"]
