#!/bin/bash
set -e

# Fix ownership of mounted volumes
chown -R appuser:appuser /app/data /app/output /app/logs 2>/dev/null || true

# If running cron mode, set up the cron job
if [ "$1" = "cron" ]; then
    # Default: 6:00 AM (in container's timezone, set via TZ env var)
    CRON_SCHEDULE="${CRON_SCHEDULE:-0 6 * * *}"

    # Create environment file for cron job (cron doesn't inherit env vars)
    printenv | grep -E '^(GEMINI_|REDDIT_|TEAMS_|TZ|PLAYWRIGHT_)' > /app/env.sh
    sed -i 's/^/export /' /app/env.sh

    # Create the cron job
    echo "${CRON_SCHEDULE} cd /app && . /app/env.sh && gosu appuser python src/main.py >> /app/logs/cron.log 2>&1" > /etc/cron.d/canvas-rss
    chmod 0644 /etc/cron.d/canvas-rss
    crontab /etc/cron.d/canvas-rss

    echo "Cron scheduled: ${CRON_SCHEDULE} (TZ=${TZ:-UTC})"
    echo "Logs: /app/logs/cron.log"

    # Run once immediately on startup, then start cron
    echo "Running initial aggregation..."
    gosu appuser python src/main.py

    echo "Starting cron daemon..."
    exec cron -f
else
    # One-time run mode
    exec gosu appuser "$@"
fi
