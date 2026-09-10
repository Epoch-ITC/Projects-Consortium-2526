from __future__ import annotations
import os
import json
import base64
from typing import List, Optional, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes: readonly access to Gmail messages
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _get_gmail_service(client_secrets_file: str, token_path: str = "token.json"):
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    # If there are no valid credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    return service


def _extract_text_from_message(msg: Dict[str, Any]) -> str:
    """Extract a best-effort plaintext body from a Gmail message resource."""
    payload = msg.get("payload", {})
    parts = payload.get("parts")
    text_chunks: List[str] = []

    def _decode_part(part: Dict[str, Any]):
        data = part.get("body", {}).get("data")
        if not data:
            return None
        # Gmail uses URL-safe base64
        return base64.urlsafe_b64decode(data.encode("ASCII")).decode("utf-8", errors="ignore")

    if not parts:
        # single-part message
        body = payload.get("body", {}).get("data")
        if body:
            try:
                return base64.urlsafe_b64decode(body.encode("ASCII")).decode("utf-8", errors="ignore")
            except Exception:
                return ""
        return ""

    for part in parts:
        mime = part.get("mimeType", "")
        if mime == "text/plain":
            text = _decode_part(part)
            if text:
                text_chunks.append(text)
        elif part.get("parts"):
            for sub in part.get("parts"):
                if sub.get("mimeType") == "text/plain":
                    text = _decode_part(sub)
                    if text:
                        text_chunks.append(text)

    return "\n\n".join(text_chunks)


class GmailFetcher:
    """Simple Gmail fetcher that lists and fetches messages.

    Usage: create with `GmailFetcher(client_secrets_file)` then call
    `fetch_messages(q=None)`; by default it will fetch all messages.
    """

    def __init__(self, client_secrets_file: str, token_path: str = "token.json"):
        self.client_secrets_file = client_secrets_file
        self.token_path = token_path
        self.service = _get_gmail_service(client_secrets_file, token_path)

    def list_message_ids(self, q: Optional[str] = None, max_results: Optional[int] = None) -> List[str]:
        """Return list of message IDs matching query `q`. 
        
        Args:
            q: Gmail query string.
            max_results: Maximum number of IDs to return (Total limit).
        """
        ids: List[str] = []
        request = self.service.users().messages().list(userId="me", q=q)
        
        while request is not None:
            resp = request.execute()
            batch = resp.get("messages", []) or []
            print(f"  ... found {len(batch)} message IDs (total so far: {len(ids) + len(batch)})")
            
            for m in batch:
                ids.append(m["id"])
                if max_results and len(ids) >= max_results:
                    return ids
            
            request = self.service.users().messages().list_next(request, resp)
        return ids

    def get_message(self, msg_id: str) -> Dict[str, Any]:
        """Fetch the full message resource for `msg_id` and return a dict with selected fields."""
        msg = self.service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        snippet = msg.get("snippet", "")
        body = _extract_text_from_message(msg)
        return {
            "id": msg.get("id"),
            "threadId": msg.get("threadId"),
            "snippet": snippet,
            "headers": headers,
            "body": body,
        }

    def fetch_messages(self, q: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch messages matching `q`. If `q` is None, fetches all messages.

        Returns a list of message dicts with `id`, `threadId`, `snippet`, `headers`, and `body`.
        """
        ids = self.list_message_ids(q=q, max_results=limit)
        results: List[Dict[str, Any]] = []
        for mid in ids:
            try:
                m = self.get_message(mid)
                results.append(m)
            except Exception as e:
                # best-effort: skip messages we can't decode
                print(f"Failed to fetch message {mid}: {e}")
        return results


__all__ = ["GmailFetcher"]
