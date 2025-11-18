#!/bin/sh
# Use PORT from environment, default to 5000 if not set
PORT=${PORT:-5000}
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 app:app
