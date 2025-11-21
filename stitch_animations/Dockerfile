FROM python:3.12-slim

# Minimal OS deps; tzdata lets TZ work
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user with stable UID/GID 1000 (matches host chown)
RUN groupadd -g 1000 appuser && useradd -m -u 1000 -g 1000 appuser

WORKDIR /app

# Only third-party Python deps go here
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Your app code
COPY . .

# Run as non-root
USER appuser

