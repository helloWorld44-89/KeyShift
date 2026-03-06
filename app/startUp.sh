#!/bin/bash
set -e

echo "$(date):Starting cron..."
# Add docker env to enviroment for cron
printenv > /etc/environment
chmod 644 /etc/cron.d/qrCron
chown root:root /etc/cron.d/qrCron

cron



echo "$(date):Starting Flask app KeyShift with Gunicorn..."

exec gunicorn \
    --workers 4 \
    --bind 0.0.0.0:5000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --preload \
    wsgi:flask_app