FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy controller code
COPY controller/ ./controller/

# Create non-root user
RUN groupadd -r herd && useradd -r -g herd herd
RUN chown -R herd:herd /app
USER herd

# Set Python path
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/healthz', timeout=5)" || exit 1

# Run the controller
CMD ["python", "-m", "controller.main"]
