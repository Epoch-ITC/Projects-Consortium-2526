"""
Gmail Service for fetching and classifying emails.

This service fetches recent emails from Gmail, classifies them using ONLY
rule-based classification, and stores important emails in the database.
"""
from __future__ import annotations
import os
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from ..core.classifier import EmailClassifier
from ..utils.text_processor import clean_email_body
from supabase import Client
import logging

logger = logging.getLogger(__name__)


class GmailService:
    """Service for fetching and classifying Gmail messages."""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        load_dotenv()
        
    def fetch_and_store_important_emails(
        self, 
        user_id: str, 
        days_back: int = 7,
        client_secrets_file: Optional[str] = None,
        token_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch recent emails, classify using rules only, and store important ones.
        
        Args:
            user_id: User's UUID
            days_back: Number of days to look back for emails
            client_secrets_file: Path to OAuth client secrets (optional)
            token_path: Path to token file (optional - NOT USED, tokens from DB)
            
        Returns:
            Dict with counts of fetched, classified, and stored emails
        """
        # Get credentials from user_integrations table
        integration = self.supabase.table("user_integrations")\
            .select("access_token, refresh_token, expires_at")\
            .eq("user_id", user_id)\
            .eq("provider", "gmail")\
            .single()\
            .execute()
            
        if not integration.data:
            raise ValueError("Gmail integration not found for user")
            
        access_token = integration.data.get("access_token")
        refresh_token = integration.data.get("refresh_token")
        expires_at_str = integration.data.get("expires_at")
        
        if not access_token:
            raise ValueError("No access token found for user")

        if not refresh_token:
            raise ValueError(
                "No refresh token found for Gmail. Please reconnect Google Classroom/Gmail to grant offline access."
            )
            
        # Use environment variables or parameters for client secrets
        if not client_secrets_file:
            client_secrets_file = os.getenv("GOOGLE_CLIENT_SECRETS", "credentials/client_secrets.json")
            
        if not os.path.exists(client_secrets_file):
            raise RuntimeError(f"Client secrets file not found: {client_secrets_file}")
        
        # Load client ID and secret from client_secrets file FIRST
        with open(client_secrets_file, 'r') as f:
            client_config = json.load(f)
            if 'installed' in client_config:
                client_id = client_config['installed']['client_id']
                client_secret = client_config['installed']['client_secret']
            elif 'web' in client_config:
                client_id = client_config['web']['client_id']
                client_secret = client_config['web']['client_secret']
            else:
                raise RuntimeError("Invalid client_secrets.json format")
        
        # Create credentials object from stored tokens
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request as GoogleAuthRequest
        from googleapiclient.discovery import build

        # Parse token expiry if stored
        token_expiry = None
        if expires_at_str:
            try:
                # Force to naive UTC for google-auth compatibility
                dt = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                if dt.tzinfo:
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                token_expiry = dt
            except Exception:
                pass
        
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            expiry=token_expiry,
        )
        
        # Refresh the access token if expired (or has no expiry info — be safe and always refresh)
        try:
            if credentials.expired or not credentials.valid:
                logger.info(f"Access token expired for user {user_id}, refreshing...")
                credentials.refresh(GoogleAuthRequest())
                # Persist the new access token back to DB
                self.supabase.table("user_integrations").update({
                    "access_token": credentials.token,
                    "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
                }).eq("user_id", user_id).eq("provider", "gmail").execute()
                logger.info(f"Successfully refreshed Gmail token for user {user_id}")
        except Exception as refresh_err:
            logger.error(f"Failed to refresh Gmail token for user {user_id}: {refresh_err}")
            raise RuntimeError(
                f"Failed to refresh Gmail access token. Please reconnect Gmail: {refresh_err}"
            )
        
        # Build Gmail service
        try:
            service = build('gmail', 'v1', credentials=credentials)
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")
            raise RuntimeError(f"Failed to authenticate with Gmail: {e}")
        
        # Build query for recent emails
        today = datetime.now(timezone.utc)
        start_date = (today - timedelta(days=days_back)).strftime("%Y/%m/%d")
        query = f"after:{start_date}"
        
        logger.info(f"Fetching emails for user {user_id} with query: {query}")
        
        # Fetch message IDs using Gmail API directly
        try:
            results = service.users().messages().list(userId='me', q=query, maxResults=500).execute()
            messages = results.get('messages', [])
            msg_ids = [msg['id'] for msg in messages]
        except Exception as e:
            logger.error(f"Failed to list messages: {e}")
            raise
            
        logger.info(f"Found {len(msg_ids)} messages in the last {days_back} days")
        
        # 🚀 OPTIMIZATION: Check which message IDs already exist in DB
        if msg_ids:
            existing_result = self.supabase.table("important_emails")\
                .select("gmail_message_id")\
                .eq("user_id", user_id)\
                .in_("gmail_message_id", msg_ids)\
                .execute()
            
            existing_msg_ids = {row['gmail_message_id'] for row in existing_result.data}
            new_msg_ids = [msg_id for msg_id in msg_ids if msg_id not in existing_msg_ids]
            
            logger.info(f"Skipping {len(existing_msg_ids)} already-synced emails. Processing {len(new_msg_ids)} new emails.")
        else:
            new_msg_ids = []
        
        important_emails = []
        total_fetched = 0
        rule_matched_count = 0
        
        # Process ONLY NEW messages
        for msg_id in new_msg_ids:
            try:
                total_fetched += 1
                
                # Get full message
                message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
                
                # Extract headers
                headers = {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}
                subject = headers.get('Subject', '(no subject)')
                sender = headers.get('From', '')
                date_str = headers.get('Date', '')
                
                # Extract body
                raw_body = self._extract_body(message.get('payload', {}))
                cleaned_body = clean_email_body(raw_body)
                
                # Classify using RULES ONLY (no LLM)
                category, should_notify, reason = EmailClassifier._classify_via_rules(
                    sender, cleaned_body, subject
                )
                
                # Only store if a rule matched AND should notify
                if category and should_notify:
                    rule_matched_count += 1
                    
                    # Generate Gmail link
                    gmail_link = f"https://mail.google.com/mail/u/0/#inbox/{msg_id}"
                    
                    # Parse date
                    received_at = self._parse_email_date(date_str)
                    
                    email_data = {
                        "user_id": user_id,
                        "gmail_message_id": msg_id,
                        "subject": subject,
                        "sender": sender,
                        "matched_rule": reason or category,
                        "gmail_link": gmail_link,
                        "received_at": received_at.isoformat() if received_at else None
                    }
                    
                    important_emails.append(email_data)
                    logger.info(f"Important email found: {subject[:50]}... (Rule: {reason})")
                    
            except Exception as e:
                logger.error(f"Error processing message {msg_id}: {e}")
                continue
        
        # Batch insert into database (upsert to avoid duplicates)
        stored_count = 0
        if important_emails:
            try:
                result = self.supabase.table("important_emails")\
                    .upsert(important_emails, on_conflict="user_id,gmail_message_id")\
                    .execute()
                stored_count = len(result.data) if result.data else 0
                logger.info(f"Stored {stored_count} important emails for user {user_id}")
            except Exception as e:
                logger.error(f"Error storing emails: {e}")
                raise
        
        # Update user_integrations last_synced_at
        try:
            self.supabase.table("user_integrations")\
                .update({"last_synced_at": datetime.now(timezone.utc).isoformat()})\
                .eq("user_id", user_id)\
                .eq("provider", "gmail")\
                .execute()
        except Exception as e:
            logger.warning(f"Failed to update last_synced_at: {e}")
        
        return {
            "total_fetched": total_fetched,
            "rule_matched": rule_matched_count,
            "stored": stored_count
        }
    
    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract plaintext body from Gmail message payload."""
        import base64
        
        def decode_data(data: str) -> str:
            """Decode base64url data."""
            if not data:
                return ""
            try:
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            except Exception:
                return ""
        
        # Check if this part has body data
        if 'body' in payload and 'data' in payload['body']:
            return decode_data(payload['body']['data'])
        
        # Check parts recursively
        if 'parts' in payload:
            text_parts = []
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain':
                    if 'data' in part.get('body', {}):
                        text_parts.append(decode_data(part['body']['data']))
                elif 'parts' in part:
                    # Recurse for multipart
                    text_parts.append(self._extract_body(part))
            return '\n'.join(text_parts)
        
        return ""
    
    def get_important_emails(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve important emails for a user.
        
        Args:
            user_id: User's UUID
            limit: Maximum number of emails to return
            
        Returns:
            List of important email dicts
        """
        try:
            result = self.supabase.table("important_emails")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("received_at", desc=True)\
                .limit(limit)\
                .execute()
                
            return result.data or []
        except Exception as e:
            logger.error(f"Error fetching important emails: {e}")
            return []
    
    def _parse_email_date(self, date_str: str) -> Optional[datetime]:
        """Parse email date header to datetime object."""
        if not date_str:
            return None
            
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return None
