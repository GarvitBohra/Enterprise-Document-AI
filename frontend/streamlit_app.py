import os
from dotenv import load_dotenv
import requests
import streamlit as st
from typing import Any, Dict, List

load_dotenv()

DEFAULT_API_URL = "http://localhost:8000"


def get_api_url() -> str:
    return os.getenv("API_URL", DEFAULT_API_URL)


def render_message(message: Dict[str, Any]) -> None:
    role = message.get("role", "user")
    content = message.get("content", "")
    sources = message.get("sources") or []

    with st.chat_message(role):
        st.markdown(content)
        if role == "assistant" and sources:
            with st.expander("Sources"):
                for source in sources:
                    st.markdown(
                        f"**{source.get('source', 'unknown')}** · score {source.get('score', 0.0):.3f}"
                    )
                    st.write(source.get("content", ""))
                    st.divider()


st.set_page_config(page_title="AI Chat", page_icon="💬", layout="centered")
st.title("AI Chat")
st.caption("A lightweight document-grounded chat interface.")

with st.sidebar:
    st.header("Settings")
    api_url = st.text_input("API URL", value=get_api_url())
    if st.button("Clear conversation"):
        st.session_state.messages = []
    st.divider()
    st.subheader("Ingest")
    gdrive_folder = st.text_input("Drive folder ID", value="")
    gdrive_creds = st.text_input("Credentials JSON path (optional)", value="")
    creds_file = st.file_uploader("Or upload credentials JSON", type=["json"])
    gdrive_out_dir = st.text_input("Ingest output dir", value="data")
    if st.button("Ingest Google Drive"):
        if not gdrive_folder:
            st.error("Provide a Drive folder ID to ingest from.")
        else:
            with st.spinner("Downloading files and ingesting to vector DB..."):
                try:
                    credentials_payload = gdrive_creds or None
                    if creds_file is not None:
                        try:
                            credentials_payload = creds_file.read().decode("utf-8")
                        except Exception:
                            credentials_payload = None

                    resp = requests.post(
                        f"{api_url.rstrip('/')}/ingest_gdrive",
                        json={
                            "folder_id": gdrive_folder,
                            "credentials_json": credentials_payload,
                            "out_dir": gdrive_out_dir,
                        },
                        timeout=300,
                    )
                    resp.raise_for_status()
                    result = resp.json()
                    files = result.get("files", [])
                    st.success(f"Ingest completed; downloaded {len(files)} items")
                except Exception as exc:
                    st.error(f"Ingest failed: {exc}")


if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    render_message(message)


def post_question(question: str, api_url: str) -> Dict[str, Any]:
    try:
        resp = requests.post(f"{api_url.rstrip('/')}/chat", json={"message": question}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        return {"reply": f"Request error: {exc}", "sources": [], "error": True}
    except Exception as exc:  # fallback for unexpected errors
        return {"reply": f"Unexpected error: {exc}", "sources": [], "error": True}


user_input = st.chat_input("Ask a question")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    render_message({"role": "user", "content": user_input})

    payload = post_question(user_input, api_url)
    reply = payload.get("reply", "")
    sources = payload.get("sources", [])

    st.session_state.messages.append({"role": "assistant", "content": reply, "sources": sources})
    render_message({"role": "assistant", "content": reply, "sources": sources})
