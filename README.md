# AI MVP Scaffold

Minimal FastAPI + Streamlit MVP scaffold integrating Supabase, OpenAI, and LlamaIndex.

Quick start

1. Copy `.env.example` to `.env` and fill keys.
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `OPENAI_API_KEY`
2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Run backend:

```bash
# from project root
python3 -m uvicorn backend.main:app --reload --port 8000
```

4. Run frontend:

```bash
python3 -m streamlit run frontend/streamlit_app.py --server.port 8501
```

The backend `/chat` endpoint now retrieves top document chunks from Supabase and uses OpenAI to answer from those excerpts.

Files created
- `backend/main.py` — FastAPI app with `/chat` endpoint
- `backend/openai_client.py` — OpenAI helper
- `backend/supabase_client.py` — Supabase client wrapper
- `connectors/gmail_connector.py` — Gmail connector skeleton
- `connectors/gdrive_connector.py` — Google Drive connector skeleton
- `scripts/download_gdrive_pdfs.py` — helper script to download PDFs from Drive
- `frontend/streamlit_app.py` — Minimal Streamlit chat UI
- `.env.example`, `requirements.txt`, `.gitignore`

Download PDFs from Google Drive:
1. Set `GOOGLE_APPLICATION_CREDENTIALS` to your service account JSON.
2. Run:

```bash
python scripts/download_gdrive_pdfs.py --folder-id YOUR_FOLDER_ID
```

Downloaded PDFs will be saved to `data/gdrive/` by default.

Gmail messages can be exported to text files via `connectors/gmail_connector.py` and ingested with `python backend/ingest.py --dir ./data`.

Next steps
- Wire backend retrieval flow using Supabase document embeddings.
- Add authentication for the backend.

Supabase table suggestion

Run this SQL in your Supabase SQL editor to create a simple `documents` table used by the ingestion script:

```sql
create table if not exists documents (
	id text primary key,
	content text,
	metadata jsonb,
	embedding jsonb
);
```

If you prefer to use `pgvector` natively (recommended for vector search), create a `vector` column instead:

```sql
create extension if not exists vector;
create table if not exists documents (
	id text primary key,
	content text,
	metadata jsonb,
	embedding vector(1536)
);
```

Note: `text-embedding-3-small` produces 1536-dimension embeddings.
