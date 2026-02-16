FROM python:3.10-slim

# System level optimizations
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (agar pandas / openpyxl / pillow use karte ho to safe hai)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Cloud Run port
ENV PORT=8080
EXPOSE 8080

# Production server
CMD ["gunicorn", "app:app",
     "--worker-class", "uvicorn.workers.UvicornWorker",
     "--workers", "1",
     "--bind", "0.0.0.0:8080",
     "--timeout", "600",
     "--keep-alive", "120"]
