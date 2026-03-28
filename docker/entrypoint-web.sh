#!/bin/sh
set -e
cd /app/src
python manage.py migrate --noinput
exec "$@"
