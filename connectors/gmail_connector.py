"""Lightweight Gmail connector using IMAP.

This module provides helpers to fetch Gmail messages and save them as text
files for ingestion. It uses the Python standard library only, so no extra
dependencies are required.

Environment variables:
- GMAIL_EMAIL
- GMAIL_PASSWORD or GMAIL_APP_PASSWORD
- GMAIL_IMAP_HOST (optional, defaults to imap.gmail.com)
- GMAIL_IMAP_PORT (optional, defaults to 993)
"""

import imaplib
import os
import re
from email import message_from_bytes
from email.header import decode_header
from pathlib import Path
from typing import Dict, List, Optional


def _get_credentials(email_address: Optional[str] = None, password: Optional[str] = None) -> tuple[str, str]:
    email_address = email_address or os.getenv("GMAIL_EMAIL")
    password = password or os.getenv("GMAIL_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD")
    if not email_address or not password:
        raise RuntimeError("GMAIL_EMAIL and GMAIL_PASSWORD (or GMAIL_APP_PASSWORD) must be set in the environment")
    return email_address, password


def _decode_header(value: Optional[bytes] | Optional[str]) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        value = value.encode("utf-8")
    decoded_parts = decode_header(value)
    parts: List[str] = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            try:
                parts.append(part.decode(encoding or "utf-8", errors="replace"))
            except Exception:
                parts.append(part.decode("utf-8", errors="replace"))
        else:
            parts.append(str(part))
    return "".join(parts)


def _normalize_filename(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z._-]+", "_", value)
    return value.strip("_.-") or "message"


def _extract_text_from_message(msg) -> str:
    if msg.is_multipart():
        parts: List[str] = []
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                charset = part.get_content_charset() or "utf-8"
                parts.append(payload.decode(charset, errors="replace"))
        return "\n".join(parts).strip()

    payload = msg.get_payload(decode=True)
    if payload is None:
        return ""

    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace").strip()


def _open_imap(host: Optional[str] = None, port: Optional[int] = None) -> imaplib.IMAP4_SSL:
    host = host or os.getenv("GMAIL_IMAP_HOST", "imap.gmail.com")
    port = port or int(os.getenv("GMAIL_IMAP_PORT", "993"))
    email_address, password = _get_credentials()
    connection = imaplib.IMAP4_SSL(host, port)
    connection.login(email_address, password)
    return connection


def list_messages(label: str = "INBOX", limit: int = 50) -> List[Dict]:
    """Return the latest Gmail messages from the requested label."""
    conn = _open_imap()
    try:
        status, _ = conn.select(label, readonly=True)
        if status != "OK":
            raise RuntimeError(f"Unable to select mailbox label: {label}")

        status, data = conn.search(None, "ALL")
        if status != "OK" or not data or not data[0]:
            return []

        message_ids = data[0].split()
        message_ids = message_ids[-limit:]
        messages: List[Dict] = []

        for msg_id in reversed(message_ids):
            status, msg_data = conn.fetch(msg_id, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            raw_email = msg_data[0][1]
            if raw_email is None:
                continue
            msg = message_from_bytes(raw_email)

            subject = _decode_header(msg.get("Subject"))
            sender = _decode_header(msg.get("From"))
            date = _decode_header(msg.get("Date"))
            body = _extract_text_from_message(msg)
            snippet = " ".join(body.split()[:50])

            messages.append(
                {
                    "id": msg_id.decode("utf-8", errors="replace"),
                    "subject": subject,
                    "from": sender,
                    "date": date,
                    "snippet": snippet,
                    "body": body,
                }
            )
        return messages
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def save_messages_to_files(label: str = "INBOX", out_dir: str = "data", limit: int = 50) -> List[str]:
    """Fetch Gmail messages and save them as text files under `out_dir/gmail/`."""
    from pathlib import Path

    messages = list_messages(label=label, limit=limit)
    target = Path(out_dir) / "gmail"
    target.mkdir(parents=True, exist_ok=True)
    paths: List[str] = []

    for msg in messages:
        subject = _normalize_filename(msg.get("subject", "message"))
        message_id = msg.get("id", "unknown")
        filename = f"gmail_{subject}_{message_id}.txt"
        path = target / filename
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"From: {msg.get('from', '')}\n")
            f.write(f"Subject: {msg.get('subject', '')}\n")
            f.write(f"Date: {msg.get('date', '')}\n\n")
            f.write(msg.get("body", ""))
        paths.append(str(path))

    return paths
