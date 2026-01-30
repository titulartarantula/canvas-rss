FROM python:3.11-slim

# Install system dependencies for Playwright/Chromium, gosu, and cron
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    gosu \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright system dependencies first
RUN playwright install-deps chromium

# Non-root user for security
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m appuser

# Create directories for data persistence and playwright
RUN mkdir -p /app/data /app/output /app/logs /opt/playwright && \
    chown -R appuser:appuser /app /opt/playwright

# Install Playwright browsers as appuser
USER appuser
RUN playwright install chromium
USER root

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
RUN chown -R appuser:appuser /app

# Copy and set up entrypoint (handles volume permissions and cron)
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["cron"]
