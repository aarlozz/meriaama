#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py ensure_superuser

# Idempotent -- matches on `code`
python manage.py seed_wellness_tips wellness_tips.json

# Idempotent -- matches on (start_week, end_week)
python manage.py seed_baby_facts baby_facts.json

# Idempotent -- matches on `code`
python manage.py seed_insight_suggestions insight_suggestions.json

# ⚠️ Held back until ingest_chunks() is confirmed to upsert rather than
# blind-add -- otherwise every deploy this week duplicates your knowledge
# base chunks in the vector store.
# python manage.py ingest_knowledge knowledge_chunks.json