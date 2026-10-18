#!/bin/sh
set -e
export PYTHONPATH="/app/backend:${PYTHONPATH:-/app}"

echo "Running database migrations..."
alembic -c /app/alembic.ini upgrade head
echo "Migrations completed."

# If the command is to run the worker, start Celery
if [ "${CELERY_WORKER:-0}" = "1" ] || echo "$@" | grep -q "celery"; then
    exec celery -A app.worker:celery_app worker --loglevel=INFO
fi

# Default: start the API
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
