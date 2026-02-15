"""
sharepoint.py — Upload files to SharePoint via Microsoft Graph API
using MSAL (client-credentials flow).

This module is only called when the user enables the SharePoint toggle
in the UI.  If credentials are missing it raises a clear error.
"""

from __future__ import annotations

import logging
from pathlib import Path

import httpx
import msal

from config import (
    AZURE_CLIENT_ID,
    AZURE_CLIENT_SECRET,
    AZURE_TENANT_ID,
    SHAREPOINT_DRIVE_ID,
    SHAREPOINT_FOLDER,
    SHAREPOINT_SITE_ID,
)

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPES = ["https://graph.microsoft.com/.default"]


def _get_access_token() -> str:
    """Acquire an access token using MSAL client-credentials flow."""
    if not all([AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID]):
        raise RuntimeError(
            "SharePoint credentials are not configured. "
            "Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID "
            "in your .env file."
        )

    app = msal.ConfidentialClientApplication(
        client_id=AZURE_CLIENT_ID,
        client_credential=AZURE_CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{AZURE_TENANT_ID}",
    )

    result = app.acquire_token_for_client(scopes=SCOPES)
    if "access_token" not in result:
        error = result.get("error_description", result.get("error", "Unknown error"))
        raise RuntimeError(f"Failed to acquire SharePoint token: {error}")

    return result["access_token"]


async def upload_file(file_path: str | Path, remote_filename: str | None = None) -> str:
    """
    Upload a single file to the configured SharePoint folder.

    For files <= 4 MB this uses a simple PUT.  For larger files a
    resumable upload session is created automatically.

    Returns the SharePoint web URL of the uploaded file.
    """
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    token = _get_access_token()
    remote_name = remote_filename or file_path.name
    folder = SHAREPOINT_FOLDER.strip("/")

    # Build the upload URL
    upload_url = (
        f"{GRAPH_BASE}/sites/{SHAREPOINT_SITE_ID}"
        f"/drives/{SHAREPOINT_DRIVE_ID}"
        f"/root:/{folder}/{remote_name}:/content"
    )

    file_bytes = file_path.read_bytes()
    file_size = len(file_bytes)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        if file_size <= 4 * 1024 * 1024:
            # Simple upload for small files
            resp = await client.put(upload_url, content=file_bytes, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("webUrl", "")
        else:
            # Resumable upload session for large files
            session_url = (
                f"{GRAPH_BASE}/sites/{SHAREPOINT_SITE_ID}"
                f"/drives/{SHAREPOINT_DRIVE_ID}"
                f"/root:/{folder}/{remote_name}:/createUploadSession"
            )
            session_resp = await client.post(
                session_url,
                headers={"Authorization": f"Bearer {token}"},
                json={"item": {"name": remote_name}},
            )
            session_resp.raise_for_status()
            upload_session_url = session_resp.json()["uploadUrl"]

            # Upload in 4 MB chunks
            chunk_size = 4 * 1024 * 1024
            for start in range(0, file_size, chunk_size):
                end = min(start + chunk_size, file_size)
                chunk = file_bytes[start:end]
                chunk_headers = {
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {start}-{end - 1}/{file_size}",
                }
                resp = await client.put(
                    upload_session_url, content=chunk, headers=chunk_headers
                )
                resp.raise_for_status()

            data = resp.json()
            return data.get("webUrl", "")


async def upload_files(file_paths: list[Path], log_callback=None) -> list[str]:
    """
    Upload multiple files and return a list of SharePoint URLs.

    *log_callback* is an optional async callable(str) for progress messages.
    """
    urls: list[str] = []
    for i, fp in enumerate(file_paths, 1):
        if log_callback:
            await log_callback(f"Uploading {fp.name} ({i}/{len(file_paths)})...")
        url = await upload_file(fp)
        urls.append(url)
        if log_callback:
            await log_callback(f"  ✓ Uploaded → {url}")
    return urls
