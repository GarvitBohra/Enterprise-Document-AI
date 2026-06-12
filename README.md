## Enterprise Document AI — Clean dev scaffold

Lightweight FastAPI + Streamlit app for document-grounded question answering. This repo provides:

- FastAPI backend with a `/chat` endpoint that answers using document excerpts stored in Supabase.
- Streamlit frontend for a simple chat UI and an "Ingest Google Drive" action to import files from Drive.
- Ingestion flow that chunks documents, creates OpenAI embeddings, and upserts vectors into Supabase.

Prerequisites
- Python 3.8+ (3.9 recommended)
- A Supabase project with a `documents` table (see schema below)
- An OpenAI API key and a service account JSON for Google Drive access

Environment
1. Copy `.env.example` to `.env` and set values:
	 - `SUPABASE_URL`
	 - `SUPABASE_KEY` (service role recommended for ingestion)
	 - `OPENAI_API_KEY`
	 - Optionally: set `GOOGLE_APPLICATION_CREDENTIALS` to a service account JSON path

Install
```bash
python3 -m pip install -r requirements.txt
```

Run (local development)
```bash
# Start backend (FastAPI)
python3 scripts/run_backend.py

# Start frontend (Streamlit)
python3 scripts/run_frontend.py
```

Usage
- Streamlit UI: open http://localhost:8501. The sidebar contains settings and an "Ingest Google Drive" tool where you can paste a Drive folder ID and either upload a service-account JSON or provide a path to your credentials.
- API: ingest programmatically with:

```bash
curl -X POST http://127.0.0.1:8000/ingest_gdrive \
	-H "Content-Type: application/json" \
	-d '{"folder_id":"<FOLDER_ID>", "credentials_json":"<JSON_STRING or null>", "out_dir":"data"}'
```

Endpoints
- `GET /health` — simple health check
- `POST /chat` — query the index (JSON body `{ "message": "your question" }`)
- `POST /ingest_gdrive` — list & download files from a Drive folder, then ingest them into Supabase

Data and ingestion
- Files downloaded from Drive are saved to `{out_dir}/gdrive/` and then passed through the ingestion flow in `backend/ingest.py` which:
	1. Reads files and chunks text
	2. Computes embeddings via OpenAI
	3. Upserts documents to Supabase `documents` table

Supabase schema suggestions
Create a simple JSON-embedding table:
```sql
create table if not exists documents (
	id text primary key,
	content text,
	metadata jsonb,
	embedding jsonb
);
```

Or use `pgvector` for native vector support:
```sql
create extension if not exists vector;
create table if not exists documents (
	id text primary key,
	content text,
	metadata jsonb,
	embedding vector(1536)
);
```

Notes & recommendations
- Use a service account with Drive access; share folders with the service account email.
- For production, protect ingestion and chat endpoints with authentication.
- Keep your `.env` and service-account JSON out of source control (see `.gitignore`).

Project structure (important files)
- `backend/` — FastAPI app and ingestion logic
- `frontend/` — Streamlit UI
- `connectors/` — Drive connector and other utilities
- `scripts/` — helper run scripts
- `requirements.txt`, `.env.example`, `README.md`

If you want, I can:
- Create a stable release branch and open a PR with these cleanup changes.
- Add a `Makefile` target to run full local setup and linting.
- Add a progress UI to Streamlit showing per-file ingest status.

---
Updated to focus on Google Drive ingest and a streamlined developer experience.
