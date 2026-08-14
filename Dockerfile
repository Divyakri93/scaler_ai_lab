# Production-ready Dockerfile for PII Redactor API
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Install build dependencies for compiling (just in case of native wheels fallback)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a secure non-root user and home directory
RUN useradd --create-home appuser

# Copy requirements and install dependencies
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt && \
    python -m pip install --no-cache-dir "numpy<2.0.0" click && \
    python -m spacy download en_core_web_sm

# Copy the rest of the application code
COPY src/ ./src/
COPY tests/ ./tests/
COPY evaluation/ ./evaluation/

# Fix directory ownership for the secure user
RUN mkdir -p input output evaluation/reports && \
    chown -R appuser:appuser /app

# Switch to the non-root execution context
USER appuser

# Expose default HTTP port
EXPOSE 8000

# Start Uvicorn web server, dynamically binding to Render's $PORT env variable
CMD ["sh", "-c", "uvicorn pii_redactor.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
