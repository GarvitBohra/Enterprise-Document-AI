from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.openai_client import chat_completion, embed_text
from backend.supabase_client import get_supabase

app = FastAPI()


class ChatRequest(BaseModel):
    message: str


@app.get("/health")
def health():
    return {"status": "ok"}


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(y * y for y in b) ** 0.5
    return dot / (mag_a * mag_b + 1e-12)


def build_prompt(query: str, documents: list[dict]) -> str:
    context = []
    for idx, doc in enumerate(documents, start=1):
        source = doc.get("metadata", {}).get("source", f"doc-{idx}")
        content = doc.get("content", "")
        context.append(f"Source {idx} ({source}):\n{content}")
    joined = "\n\n".join(context)
    return (
        "You are a helpful AI assistant. Use only the content from the provided document excerpts to answer the question. "
        "If the answer is not present in the excerpts, say that you don\'t know.\n\n"
        f"{joined}\n\n"
        f"Question: {query}\nAnswer:"
    )


async def retrieve_documents(question: str, top_k: int = 5) -> list[dict]:
    supabase = get_supabase()
    if supabase is None:
        raise HTTPException(status_code=500, detail="Supabase is not configured")

    try:
        result = supabase.table("documents").select("id,content,metadata,embedding").execute()
    except Exception as exc:
        message = str(exc)
        if "Could not find the table 'public.documents'" in message:
            raise HTTPException(
                status_code=500,
                detail="Supabase table `documents` not found. Create it in your Supabase project and reload the app.",
            )
        raise HTTPException(status_code=500, detail=message)

    status_code = getattr(result, "status_code", None)
    if status_code is not None and status_code >= 400:
        raise HTTPException(
            status_code=500,
            detail=f"Supabase query failed with status {status_code}",
        )

    if result.data is None:
        raise HTTPException(
            status_code=500,
            detail="Supabase returned no data for the documents query.",
        )

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
        # No documents found — use LLM fallback but mark it as ungrounded.
        system_msg = {
            "role": "system",
            "content": (
                "You are a helpful assistant. If you do not have document-based evidence,"
                " answer succinctly and avoid making up facts. If unsure, say you are not sure."
            ),
        }
        user_msg = {"role": "user", "content": req.message}
        try:
            fallback_reply = await chat_completion([system_msg, user_msg])
        except Exception:
            # If the LLM call fails, return a safe default message.
            return {"reply": "I could not find any relevant documents to answer that question.", "sources": [], "fallback": False}

        return {"reply": fallback_reply, "sources": [], "fallback": True}

    prompt = build_prompt(req.message, docs)
    messages = [
        {"role": "system", "content": "You are a helpful assistant that answers questions using provided document excerpts."},
        {"role": "user", "content": prompt},
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
