from typing import Any, Dict, List
import asyncio
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.openai_client import chat_completion, embed_text
from backend.supabase_client import get_supabase

from connectors.gdrive_connector import list_files as gdrive_list_files, download_file as gdrive_download_file
import backend.ingest as ingest_module

app = FastAPI()


class ChatRequest(BaseModel):
    message: str


@app.get("/health")
def health():
    return {"status": "ok"}


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(y * y for y in b) ** 0.5
    return dot / (mag_a * mag_b + 1e-12)


def build_prompt(query: str, documents: List[Dict]) -> str:
    context = []
    for idx, doc in enumerate(documents, start=1):
        source = doc.get("metadata", {}).get("source", f"doc-{idx}")
        content = doc.get("content", "")
        context.append(f"Source {idx} ({source}):\n{content}")
    joined = "\n\n".join(context)
    return (
        "You are a helpful AI assistant. Use only the content from the provided document excerpts to answer the question. "
        "If the answer is not present in the excerpts, say that you don't know.\n\n"
        f"{joined}\n\n"
        f"Question: {query}\nAnswer:"
    )


async def retrieve_documents(question: str, top_k: int = 5) -> List[Dict[str, Any]]:
    supabase = get_supabase()
    if supabase is None:
        return []

    try:
        result = supabase.table("documents").select("id,content,metadata,embedding").execute()
    except Exception as exc:
        message = str(exc)
        if "Could not find the table 'public.documents'" in message:
            raise HTTPException(
                status_code=500,
                detail="Supabase table `documents` not found. Create it in your Supabase project and reload the app.",
            )
        return []

    status_code = getattr(result, "status_code", None)
    if status_code is not None and status_code >= 400:
        return []

    if result.data is None:
        return []

    query_embedding = await embed_text(question)
    documents = []
    for row in result.data or []:
        embedding = row.get("embedding")
        score = cosine_similarity(query_embedding, embedding or [])
        documents.append({"score": score, **row})

    documents.sort(key=lambda item: item["score"], reverse=True)
    return documents[:top_k]


@app.post("/chat")
async def chat(req: ChatRequest):
    docs = await retrieve_documents(req.message, top_k=5)
    if not docs:
        system_msg = {
            "role": "system",
            "content": (
                "You are a helpful assistant. Answer clearly and concisely. "
                "If you do not have enough evidence, say so instead of guessing."
            ),
        }
        user_msg = {"role": "user", "content": req.message}
        try:
            fallback_reply = await chat_completion([system_msg, user_msg])
            return {"reply": fallback_reply, "sources": [], "fallback": True}
        except Exception:
            return {
                "reply": "I could not find any relevant documents to answer that question.",
                "sources": [],
                "fallback": False,
            }

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that answers questions using provided document excerpts only.",
        },
        {"role": "user", "content": build_prompt(req.message, docs)},
    ]
    reply = await chat_completion(messages)
    sources = [
        {
            "source": doc.get("metadata", {}).get("source", f"doc-{idx}"),
            "content": doc.get("content", ""),
            "score": doc.get("score", 0.0),
        }
        for idx, doc in enumerate(docs, start=1)
    ]
    return {"reply": reply, "sources": sources}


from typing import Optional


class IngestGDriveRequest(BaseModel):
    folder_id: str
    credentials_json: Optional[str] = None
    out_dir: str = "data"


@app.post("/ingest_gdrive")
async def ingest_gdrive(req: IngestGDriveRequest):
    """List files in a Google Drive folder, download them locally, and ingest.

    Downloads are saved under `{out_dir}/gdrive/` and then the existing
    `ingest_directory` flow is called to compute embeddings and upsert to
    the Supabase `documents` table.
    """
    target_dir = os.path.join(req.out_dir, "gdrive")
    os.makedirs(target_dir, exist_ok=True)

    try:
        files_meta = await asyncio.to_thread(gdrive_list_files, req.folder_id, req.credentials_json)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Drive list failed: {exc}")

    saved_paths = []
    for meta in files_meta:
        file_id = meta.get("id")
        name = meta.get("name") or f"file_{file_id}"
        # sanitize name: replace path separators
        name = name.replace(os.sep, "_")
        dest_path = os.path.join(target_dir, f"{name}")
        try:
            await asyncio.to_thread(gdrive_download_file, file_id, dest_path, req.credentials_json)
            saved_paths.append(dest_path)
        except Exception as exc:
            # continue on individual download errors but record them
            saved_paths.append({"id": file_id, "name": name, "error": str(exc)})

    try:
        await asyncio.to_thread(ingest_module.ingest_directory, target_dir)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {exc}")

    return {"status": "ok", "files": saved_paths}
