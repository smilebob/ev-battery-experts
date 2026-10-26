# Multi-stage lightweight production Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SOH_DATA_DIR=/app/data

# Working directory
WORKDIR /app

# Install system dependencies (curl for healthcheck, ca-certificates)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and source code
COPY pyproject.toml README.md /app/
COPY *.py /app/
COPY templates /app/templates

# Install Python dependencies using standard pip
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Create persistent data directories
RUN mkdir -p /app/data /root/.config/ev-battery-soh/keys

# Expose web server port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Default command: launch FastAPI web server with Uvicorn
CMD ["uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", "8000"]
