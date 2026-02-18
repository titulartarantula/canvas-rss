# Frontend build stage
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Main Python application stage
FROM python:3.11-slim

# Install system dependencies for Playwright/Chromium and supercronic
# Using supercronic instead of cron - runs as non-root user
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    gosu \
    && rm -rf /var/lib/apt/lists/* \
    && SUPERCRONIC_URL="https://github.com/aptible/supercronic/releases/download/v0.2.29/supercronic-linux-amd64" \
    && SUPERCRONIC_SHA1SUM="cd48d45c4b10f3f0bfdd3a57d054cd05ac96812b" \
    && wget -q "$SUPERCRONIC_URL" -O /usr/local/bin/supercronic \
    && echo "${SUPERCRONIC_SHA1SUM}  /usr/local/bin/supercronic" | sha1sum -c - \
    && chmod +x /usr/local/bin/supercronic

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
RUN mkdir -p /app/data /app/output /app/logs /opt/playwright /app/frontend/dist && \
    chown -R appuser:appuser /app /opt/playwright

# Install Playwright browsers as appuser
USER appuser
RUN playwright install chromium
USER root

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY VERSION .

# Copy frontend build from frontend-builder stage
COPY --from=frontend-builder /frontend/dist /app/frontend/dist

RUN chown -R appuser:appuser /app

# Copy and set up entrypoint (handles volume permissions and cron)
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["cron"]
