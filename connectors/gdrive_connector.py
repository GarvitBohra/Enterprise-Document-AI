"""Google Drive connector helpers.

This module provides simple helpers to list and download files from Google Drive.
It uses `googleapiclient` when available. If not installed, the functions will
raise an informative error pointing at the required packages.
"""
import os
import json
from typing import List, Dict, Union, Optional


def _ensure_google_client():
    try:
        from googleapiclient.discovery import build  # type: ignore
        from google.oauth2 import service_account  # type: ignore
    except Exception:
        raise RuntimeError(
            "Missing Google Drive client libraries. Install: `pip install google-api-python-client google-auth google-auth-httplib2`"
        )
    return build, service_account


def _load_credentials(credentials_json: Union[str, dict, None], scopes: List[str]):
    build, service_account = _ensure_google_client()
    # If no credentials provided, rely on GOOGLE_APPLICATION_CREDENTIALS environment var
    if not credentials_json:
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not creds_path:
            raise RuntimeError("Provide `credentials_json` or set GOOGLE_APPLICATION_CREDENTIALS")
        return service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)

    # If a dict was passed in (already parsed JSON), use it directly
    if isinstance(credentials_json, dict):
        return service_account.Credentials.from_service_account_info(credentials_json, scopes=scopes)

    # If it's a JSON string, try to parse it
    try:
        maybe = json.loads(credentials_json) if isinstance(credentials_json, str) else None
        if isinstance(maybe, dict):
            return service_account.Credentials.from_service_account_info(maybe, scopes=scopes)
    except Exception:
        # Not a JSON string; treat as path
        pass

    # Treat as path to a credentials file
    return service_account.Credentials.from_service_account_file(str(credentials_json), scopes=scopes)


def list_files(folder_id: str, credentials_json: Union[str, dict, None] = None) -> List[Dict]:
    """List files in a Drive folder (returns file metadata list).

    If `credentials_json` is None, the function will use the environment
    variable `GOOGLE_APPLICATION_CREDENTIALS` pointing to a service account JSON.
    """
    build, service_account = _ensure_google_client()
    creds = _load_credentials(credentials_json, scopes=["https://www.googleapis.com/auth/drive.readonly"])
    service = build("drive", "v3", credentials=creds)
    q = f"'{folder_id}' in parents and trashed = false"
    files = []
    page_token = None
    while True:
        resp = service.files().list(q=q, fields="nextPageToken, files(id, name, mimeType)", pageToken=page_token).execute()
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return files


def download_file(file_id: str, dest_path: str, credentials_json: Union[str, dict, None] = None) -> None:
    """Download a file from Drive to `dest_path`.

    For Google Docs (mimeType `application/vnd.google-apps.document`) this
    function will export to plain text.
    """
    build, service_account = _ensure_google_client()
    creds = _load_credentials(credentials_json, scopes=["https://www.googleapis.com/auth/drive.readonly"])
    service = build("drive", "v3", credentials=creds)
    meta = service.files().get(fileId=file_id, fields="mimeType, name").execute()
    mime = meta.get("mimeType")
    if mime == "application/vnd.google-apps.document":
        # export as plain text
        request = service.files().export_media(fileId=file_id, mimeType="text/plain")
        data = request.execute()
        if isinstance(data, str):
            data = data.encode("utf-8")
        with open(dest_path, "wb") as fh:
            fh.write(data)
    else:
        request = service.files().get_media(fileId=file_id)
        data = request.execute()
        with open(dest_path, "wb") as fh:
            fh.write(data)


def upload_file(local_path: str, folder_id: str, file_name: str = None, credentials_json: Optional[str] = None) -> str:
    """Upload a local file to Google Drive.

    Args:
        local_path: local file path to upload
        folder_id: Drive folder ID where the file will be created
        file_name: name for the file in Drive (defaults to basename of local_path)
        credentials_json: path to service account JSON (or use GOOGLE_APPLICATION_CREDENTIALS)

    Returns:
        The file ID of the uploaded file on Google Drive.
    """
    build, service_account = _ensure_google_client()
    creds = _load_credentials(credentials_json, scopes=["https://www.googleapis.com/auth/drive"])
    service = build("drive", "v3", credentials=creds)

    if file_name is None:
        file_name = os.path.basename(local_path)

    # Determine MIME type based on file extension
    import mimetypes
    mime_type, _ = mimetypes.guess_type(local_path)
    if mime_type is None:
        mime_type = "application/octet-stream"

    from googleapiclient.http import MediaFileUpload  # type: ignore

    file_metadata = {"name": file_name, "parents": [folder_id]}
    media = MediaFileUpload(local_path, mimetype=mime_type, resumable=False)
    request = service.files().create(body=file_metadata, media_body=media, fields="id")
    file_obj = request.execute()

    return file_obj.get("id")
