# DNK Git Research — Standalone Service
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Environment variables (override via .env or docker run)
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Default command: show help
ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
