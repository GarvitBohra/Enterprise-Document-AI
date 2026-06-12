"""Simple ingestion script: read files, compute OpenAI embeddings, upsert to Supabase.

Usage:
    python backend/ingest.py --dir ./data

This is a lightweight scaffold — replace with LlamaIndex flows later.
"""
import os
import json
import uuid
import argparse
from typing import List

from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import create_client
except Exception:
    create_client = None

from openai import OpenAI


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


def read_files(directory: str) -> List[dict]:
    # Prefer LlamaIndex reader when available for richer parsing (PDFs, docs)
    try:
        from llama_index import SimpleDirectoryReader

        reader = SimpleDirectoryReader(directory)
        ld_docs = reader.load_data()
        docs = []
        for d in ld_docs:
            # LlamaIndex Document may have .get_text() or .text
            text = d.get_text() if hasattr(d, "get_text") else getattr(d, "text", str(d))
            meta = getattr(d, "extra_info", {}) or {}
            path = meta.get("file_path") or meta.get("source") or getattr(d, "source", None) or "unknown"
            docs.append({"path": path, "text": text, "meta": meta})
        return docs
    except Exception:
        docs = []
        for root, _, files in os.walk(directory):
            for fn in files:
                if fn.startswith("."):
                    continue
                path = os.path.join(root, fn)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        text = f.read()
                except Exception:
                    # skip binaries
                    continue
                docs.append({"path": path, "text": text, "meta": {"file_name": fn}})
        return docs


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def embed_texts(texts: List[str]) -> List[List[float]]:
    # Use OpenAI batch embeddings
    resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [r.embedding for r in resp.data]


def get_supabase_client():
    if not create_client:
        return None
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as exc:
        print(f"Supabase client init failed: {exc}")
        return None


def upsert_documents(supabase, rows: List[dict]):
    # Upsert into `documents` table. Table schema suggestion in README.
    if supabase is None:
        raise RuntimeError("Supabase client not configured - set SUPABASE_URL and SUPABASE_KEY")
    res = supabase.table("documents").upsert(rows).execute()
    return res


def ingest_directory(directory: str):
    docs = read_files(directory)
    all_rows = []
    for d in docs:
        chunks = chunk_text(d["text"])
        embeddings = embed_texts(chunks)
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            doc_id = str(uuid.uuid4())
            row = {
                "id": doc_id,
                "content": chunk,
                "metadata": {"source": d["path"], "chunk": i, **d.get("meta", {})},
                "embedding": emb,
            }
            all_rows.append(row)

    supabase = get_supabase_client()
    if supabase is None:
        print("Supabase client not available. Set SUPABASE_URL and SUPABASE_KEY and install supabase package.")
        return

    print(f"Upserting {len(all_rows)} vector rows to Supabase...")
    res = upsert_documents(supabase, all_rows)
    print("Upsert result:", res)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="Directory with files to ingest")
    args = parser.parse_args()
    ingest_directory(args.dir)


if __name__ == "__main__":
    main()
