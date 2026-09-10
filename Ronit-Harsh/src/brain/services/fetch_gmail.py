"""
Demo/test script for Gmail fetching functionality.

This is a standalone script for testing the Gmail fetcher.
For production use, see gmail_service.py which integrates with the API.

Set environment variables or create a `.env` file with:
 - `GOOGLE_CLIENT_SECRETS` -> path to OAuth client_secrets.json
 - `GOOGLE_TOKEN_PATH` -> (optional) path to store token.json
 - `GMAIL_QUERY` -> (optional) Gmail search query; if omitted, fetches all messages

Run: python -m src.brain.services.fetch_gmail
"""
from __future__ import annotations
import os
from dotenv import load_dotenv

from datetime import datetime, timedelta
from ..tools.gmail_fetcher import GmailFetcher
from ..core.classifier import EmailClassifier
from ..utils.text_processor import clean_email_body


def main():
    """Demo script showing how to fetch and classify Gmail messages."""
    load_dotenv()
    client_secrets = os.getenv("GOOGLE_CLIENT_SECRETS")
    token_path = os.getenv("GOOGLE_TOKEN_PATH", "token.json")
    query = os.getenv("GMAIL_QUERY")
    
    # Configure time window
    days_back = 20
    today = datetime.now()
    start_date = (today - timedelta(days=days_back)).strftime("%Y/%m/%d")
    date_filter = f"after:{start_date}"
    
    if query:
        query = f"{query} {date_filter}"
    else:
        query = date_filter
        
    print(f"Querying with: {query}")

    if not client_secrets:
        raise RuntimeError("Set GOOGLE_CLIENT_SECRETS env var pointing to client_secrets.json")

    fetcher = GmailFetcher(client_secrets_file=client_secrets, token_path=token_path)

    print("Listing message ids...")
    msg_ids = fetcher.list_message_ids(q=query, max_results=50)  # Limit for demo
    print(f"Found {len(msg_ids)} messages in the last {days_back} days.")

    # Process messages and show classification
    important_count = 0
    for mid in msg_ids:
        try:
            m = fetcher.get_message(mid)
        except Exception as e:
            print(f"Error fetching message {mid}: {e}")
            continue
            
        # Extract fields
        subject = m["headers"].get("Subject", "(no subject)")
        sender = m["headers"].get("From", "")
        raw_body = m.get("body", "")
        
        # Clean body
        cleaned_body = clean_email_body(raw_body)
        
        # Classify using RULES ONLY (no LLM fallback in this demo)
        category, should_notify, reason = EmailClassifier._classify_via_rules(
            sender, cleaned_body, subject
        )
        
        # Only print important emails
        if category and should_notify:
            important_count += 1
            print(f"\n[{important_count}] IMPORTANT EMAIL")
            print(f"  Subject: {subject[:60]}...")
            print(f"  From: {sender}")
            print(f"  Category: {category}")
            print(f"  Reason: {reason}")
    
    print(f"\n\nSummary: Found {important_count} important emails out of {len(msg_ids)} total.")


if __name__ == "__main__":
    main()
