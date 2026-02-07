#!/bin/bash
set -e

# Fix ownership of mounted volumes (requires root, done before dropping privileges)
chown -R appuser:appuser /app/data /app/output /app/logs 2>/dev/null || true

# If running cron mode, set up supercronic (non-root cron replacement)
if [ "$1" = "cron" ]; then
    # Default: 6:00 AM (in container's timezone, set via TZ env var)
    CRON_SCHEDULE="${CRON_SCHEDULE:-0 6 * * *}"

    # Create environment file for cron job (quote values to handle special chars)
    printenv | grep -E '^(GEMINI_|REDDIT_|TEAMS_|TZ|PLAYWRIGHT_)' | sed "s/=/='/" | sed "s/$/'/" | sed 's/^/export /' > /tmp/env.sh
    install -o appuser -g appuser -m 600 /tmp/env.sh /app/env.sh
    rm -f /tmp/env.sh

    # Create the crontab file for supercronic
    echo "${CRON_SCHEDULE} cd /app && . /app/env.sh && python -m src.main >> /app/logs/cron.log 2>&1" > /app/crontab
    chown appuser:appuser /app/crontab

    echo "Cron scheduled: ${CRON_SCHEDULE} (TZ=${TZ:-UTC})"
    echo "Logs: /app/logs/cron.log"

    # Run once immediately on startup as appuser
    echo "Running initial aggregation..."
    gosu appuser bash -c "cd /app && . /app/env.sh && python -m src.main"

    echo "Starting supercronic (non-root cron)..."
    # Run supercronic as appuser - no root process needed
    exec gosu appuser supercronic /app/crontab
else
    # One-time run mode
    exec gosu appuser "$@"
fi
