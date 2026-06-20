#!/bin/bash
set -e

mkdir -p /app/data

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "$SEED_DEMO" = "true" ]; then
    python manage.py seed_demo
fi

python manage.py shell -c "from projects.role_permissions import ensure_system_roles; ensure_system_roles()"
python manage.py repair_user_profiles

exec gunicorn vibe.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --timeout 120
