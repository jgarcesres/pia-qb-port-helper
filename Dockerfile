FROM python:3.11-slim

LABEL maintainer="PIA qBittorrent Port Helper"
LABEL description="Automatically updates qBittorrent port from PIA WireGuard"

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .

# Create directory for port file
RUN mkdir -p /app && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set default environment variables
ENV QB_HOST=http://qbittorrent:8080
ENV QB_USERNAME=admin
ENV QB_PASSWORD=adminadmin
ENV PORT_FILE=/app/port.dat
ENV LOG_LEVEL=INFO
ENV CHECK_INTERVAL=10
ENV QB_HEALTHCHECK_PORT=8080

# Health check - uses QB_HEALTHCHECK_PORT environment variable
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests, os; requests.get(f'http://localhost:{os.getenv(\"QB_HEALTHCHECK_PORT\", \"8080\")}', timeout=5)" || exit 1

CMD ["python", "app.py"]
