FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["gunicorn", "app:app", \
     "--bind", "0.0.0.0:8080", \
     "--worker-class", "gevent", \
     "--workers", "1", \
     "--worker-connections", "10", \
     "--timeout", "0", \
     "--graceful-timeout", "0", \
     "--keep-alive", "300", \
     "--worker-tmp-dir", "/dev/shm"]
```

**Key change: `--worker-class gevent`** — yeh async hai, blocking calls pe worker kill nahi hoga!

---

### **2. requirements.txt mein add karo:**
```
gevent==23.9.1
greenlet==3.0.3
