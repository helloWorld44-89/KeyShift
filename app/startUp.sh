#!/bin/bash
set -e

echo "Starting cron..."
cron 

echo "starting Flask app Keyshift..."
flask run --host  0.0.0.0 --port 5000

echo "Startup script complete. Tailing logs..."
tail -f /var/log/syslog