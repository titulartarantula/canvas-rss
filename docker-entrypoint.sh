#!/bin/bash
set -e

# Fix ownership of mounted volumes (runs as root initially)
chown -R appuser:appuser /app/data /app/output /app/logs 2>/dev/null || true

# Switch to appuser and run the command
exec gosu appuser "$@"
