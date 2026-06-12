import os
from dotenv import load_dotenv
import requests
import streamlit as st

load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.title("AI Chat (MVP)")

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.form("chat"):
    user_input = st.text_input("You:")
    submitted = st.form_submit_button("Send")
    if submitted and user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        try:
            resp = requests.post(f"{API_URL}/chat", json={"message": user_input}, timeout=30)
            if resp.ok:
                reply = resp.json().get("reply", "")
                sources = resp.json().get("sources", [])
            else:
                reply = f"Error: {resp.status_code} {resp.text}"
                sources = []
        except Exception as e:
            reply = f"Error: {e}"
            sources = []
        st.session_state.messages.append({"role": "assistant", "content": reply, "sources": sources})

for m in st.session_state.messages:
    if m["role"] == "user":
        st.markdown(f"**You:** {m['content']}")
    else:
        st.markdown(f"**AI:** {m['content']}")
        if m.get("sources"):
            with st.expander("Source documents"):
                for source in m["sources"]:
                    src = source.get("source", "unknown")
                    score = source.get("score", 0.0)
                    content = source.get("content", "")
                    st.markdown(f"**{src}** — score: {score:.3f}")
                    st.write(content)
                    st.markdown("---")
