# backend/Dockerfile
FROM python:3.11-slim

# Install system dependencies (for psycopg/asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
# (The 'backend' directory code is copied into /app in the container)

# Expose the API port
EXPOSE 8000

# Default command: run Uvicorn server (overridden in docker-compose to run migrations first)
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
