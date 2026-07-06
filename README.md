# Meri Aama — Django Backend

## What's here

A working Django + DRF skeleton for all 8 modules described in your report:

| Module | App | Key endpoint |
|---|---|---|
| Auth / accounts | `accounts` | `POST /api/accounts/register/`, `POST /api/auth/login/` |
| User Health Profile | `health_profile` | `GET/PATCH /api/health-profile/me/` |
| Psychometric Stress Test | `psychometric` | `GET/POST /api/psychometric/tests/` |
| Weekly Tracker | `tracker` | `GET /api/tracker/weeks/` |
| Daily Mood Check-in | `mood` | `GET/POST /api/mood/entries/` |
| Community Forum | `forum` | `GET/POST /api/forum/posts/`, `POST /api/forum/comments/` |
| Wellness RAG Engine | `wellness_rag` | `POST /api/wellness/recommend/`, `GET /api/wellness/history/` |
| PDF Health Insight | `pdf_insight` | `POST /api/pdf-insight/reports/` (multipart, field `file`) |
| Hospital Portal | `hospital_portal` | Django admin (`/admin/`) + `GET/POST /api/hospital/records/` |

Doctor Chat isn't scaffolded here — it's typically a thin real-time layer (e.g. Django Channels + WebSocket, or even a simple polling model) sitting on top of `accounts` + `health_profile`. Happy to build that next once the rest is running, since it depends on how "real-time" you want it (WebSocket vs simple message list).

## 1. Local setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # then edit .env: add your real GROQ_API_KEY
python manage.py migrate
python manage.py createsuperuser # make yourself an admin to use /admin/
python manage.py runserver
```

Visit `http://127.0.0.1:8000/admin/` to log in and create hospital staff accounts (set their `role` to doctor/nurse/data_entry and tick `is_staff`).

## 2. Testing the RAG pipeline end-to-end

1. **Prepare your scraped data.** Run your own BeautifulSoup scraper against WHO/PubMed/NHS pages, chunk the text (~200-400 tokens per chunk), and write it to a JSON file like this:

```json
[
  {
    "id": "who-antenatal-001",
    "text": "Pregnant women should attend at least eight antenatal contacts to reduce perinatal deaths...",
    "source_url": "https://www.who.int/news-room/fact-sheets/detail/antenatal-care",
    "source_name": "WHO"
  }
]
```

2. **Ingest it:**
```bash
python manage.py ingest_knowledge path/to/chunks.json
```
This embeds each chunk with `all-MiniLM-L6-v2` and stores it in ChromaDB (local dev default) at `CHROMA_PERSIST_DIR`.

3. **Test retrieval + generation** via the API:
```bash
# get a token
curl -X POST http://127.0.0.1:8000/api/auth/login/ -d "username=yourname&password=yourpass"

# ask for a recommendation
curl -X POST http://127.0.0.1:8000/api/wellness/recommend/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "what should I eat this week"}'
```

4. **Things to actually check while testing** (this is your evaluation checklist, useful for the report too):
   - Does retrieval return chunks that are *topically relevant* to the query, not just superficially similar wording?
   - Does the Groq response only use facts present in the retrieved chunks (spot-check a few answers against the source text)?
   - What happens when no relevant chunks exist (e.g. ask an unrelated question) — does it say so instead of hallucinating?
   - Does `gestational_week` context actually change the answer (ask the same question with different weeks set on the health profile)?
   - Response latency — Groq should feel close to instant; if it's slow, check you're using `openai/gpt-oss-20b` or `120b`, not a deprecated model name.

## 3. Switching to pgvector for deployment

Locally you're on Chroma (fast to iterate). Before deploying to Render:

1. Set `VECTOR_STORE_BACKEND=pgvector` in your environment.
2. Make sure the Postgres instance has the extension enabled once:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Re-run `python manage.py ingest_knowledge path/to/chunks.json` against the deployed database (or re-ingest via a one-off shell/management command on Render) — Chroma and Postgres are separate stores, so switching backends means re-ingesting.

## 4. Deploying to Render (free tier)

1. Push this project to a GitHub repo.
2. On Render: **New → Web Service** → connect the repo.
3. Build command: `bash build.sh`
4. Start command: `gunicorn config.wsgi`
5. Add a **PostgreSQL** instance (Render → New → PostgreSQL, free tier), copy its **Internal Database URL** into the web service's `DATABASE_URL` env var.
6. Add the rest of your `.env` values as environment variables in the Render dashboard (`GROQ_API_KEY`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` set to your `*.onrender.com` domain, `VECTOR_STORE_BACKEND=pgvector`).
7. Deploy. First request after idle will be slow (~30-60s cold start) — normal on the free tier, mention it if demoing live.

## Notes / things intentionally simplified for the prototype

- PDF summarization runs synchronously in the request (fine for demo scale; move to Celery/RQ if this becomes real).
- Forum moderation is a boolean flag with no review queue yet.
- `WeeklyUpdate` generic content (`fetal_development_note`) isn't seeded — you'll want a small fixture/seed script with ~40 weeks of content, or generate it once via Groq and store it (cheaper than generating on every request).
