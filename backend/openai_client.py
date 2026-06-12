import os
from typing import Dict, List
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def embed_text(text: str) -> List[float]:
    """Return an OpenAI text embedding for a single string."""
    def _call():
        resp = client.embeddings.create(model="text-embedding-3-small", input=text)
        return resp.data[0].embedding

    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _call)

async def chat_completion(messages: List[Dict]) -> str:
    """Call OpenAI chat completion in a thread to avoid blocking event loop."""
    def _call():
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.0,
        )
        return resp.choices[0].message.content

    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _call)
