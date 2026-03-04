#!/bin/bash
set -e

echo "Starting cron..."
cron 

echo "Starting Flask app KeyShift with Gunicorn..."

exec gunicorn \
    --workers 4 \
    --bind 0.0.0.0:5000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --preload \
    wsgi:flask_app