FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY SOUL.md .

# Create non-root user
RUN useradd -m -u 1000 chimera && \
    chown -R chimera:chimera /app
USER chimera

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Default command (can be overridden)
CMD ["python", "-m", "src.main"]
