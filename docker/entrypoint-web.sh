#!/bin/sh
set -e
cd /app/src

# Preflight: in production (DEBUG=false) refuse to start without a real secret key.
# (settings.py also enforces this, but failing here gives a clearer message.)
_debug=$(printf '%s' "${DJANGO_DEBUG:-true}" | tr '[:upper:]' '[:lower:]')
if [ "$_debug" != "true" ]; then
    if [ -z "${DJANGO_SECRET_KEY}" ] || [ "${DJANGO_SECRET_KEY}" = "dev-secret-key" ]; then
        echo "FATAL: DJANGO_SECRET_KEY must be set to a strong value when DJANGO_DEBUG=false" >&2
        exit 1
    fi
fi

# Gunicorn worker count is tunable via GUNICORN_WORKERS (gunicorn reads WEB_CONCURRENCY).
export WEB_CONCURRENCY="${GUNICORN_WORKERS:-2}"

python manage.py migrate --noinput
exec "$@"
