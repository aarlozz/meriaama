#!/usr/bin/env bash
# Render build command: bash build.sh
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# If deploying with pgvector backend, enable the extension once:
# python manage.py dbshell -c "CREATE EXTENSION IF NOT EXISTS vector;"
