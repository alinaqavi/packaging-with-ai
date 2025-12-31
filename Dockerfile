# Base image
FROM python:3.10-slim

# Working directory
WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Requirements copy karo
COPY requirements.txt .

# Python dependencies install
RUN pip install --no-cache-dir -r requirements.txt

# Project files copy karo
COPY . .

# Flask environment
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# Port expose
EXPOSE 5000

# Run app
CMD ["python", "app.py"]
