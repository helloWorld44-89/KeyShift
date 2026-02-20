#!/bin/bash
set -e

echo "Starting cron..."
cron 

echo "Starting Flask app KeyShift with Gunicorn..."
# Start Gunicorn with:
# - 4 worker processes (adjust based on your CPU cores: 2-4 x num_cores)
# - Bind to all interfaces on port 5000
# - Set worker timeout to 120 seconds
# - Enable access logging
# - Point to your Flask app (app:app means app.py file, app variable)
exec gunicorn \
    --workers 4 \
    --bind 0.0.0.0:5000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    wsgi:flask_app