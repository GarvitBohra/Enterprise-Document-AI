"""Lightweight Slack connector using the Web API via `httpx`.

Functions provided:
- `fetch_channel_messages(channel_id, limit=200)` -> list of message dicts
- `save_channel_messages_to_files(channel_id, out_dir='data')` -> list of file paths

Requires `SLACK_BOT_TOKEN` in the environment. This implementation avoids
adding `slack-sdk` as a hard dependency by using simple HTTP calls.
"""
import os
from typing import List, Dict
import httpx

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_API_BASE = "https://slack.com/api"


def _auth_headers():
    token = SLACK_BOT_TOKEN
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN not set in environment")
    return {"Authorization": f"Bearer {token}"}


def fetch_channel_messages(channel_id: str, limit: int = 200) -> List[Dict]:
    """Fetch recent messages from a channel using `conversations.history`.

    Returns a list of message dicts as returned by Slack.
    """
    url = f"{SLACK_API_BASE}/conversations.history"
    params = {"channel": channel_id, "limit": limit}
    r = httpx.get(url, headers=_auth_headers(), params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack API error: {data.get('error')}")
    return data.get("messages", [])


def save_channel_messages_to_files(channel_id: str, out_dir: str = "data") -> List[str]:
    """Fetch messages and save each as a text file under `out_dir/slack/`.

    Returns list of created file paths.
    """
    import pathlib

    msgs = fetch_channel_messages(channel_id)
    target = pathlib.Path(out_dir) / "slack"
    target.mkdir(parents=True, exist_ok=True)
    paths = []
    for m in msgs:
        ts = m.get("ts", "0").replace('.', '_')
        user = m.get("user", "unknown")
        text = m.get("text", "")
        fname = target / f"slack_{channel_id}_{ts}.txt"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(f"user: {user}\n")
            f.write(text)
        paths.append(str(fname))
    return paths


def download_file(url_private: str, dest_path: str) -> None:
    """Download a file from Slack given its `url_private` (requires auth)."""
    r = httpx.get(url_private, headers=_auth_headers(), timeout=60)
    r.raise_for_status()
    with open(dest_path, "wb") as f:
        f.write(r.content)

