"""
Script to fetch the last 100 emails, classify them, and save to a JSON file.
Usage: python -m src.brain.services.batch_process_emails
"""
import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv

from ..tools.gmail_fetcher import GmailFetcher
from ..core.classifier import EmailClassifier
from ..utils.text_processor import clean_email_body

OUTPUT_FILE = "emails_classified.json"
LIMIT = 100

def main():
    load_dotenv()
    
    # 1. Setup
    client_secrets = os.getenv("GOOGLE_CLIENT_SECRETS")
    token_path = os.getenv("GOOGLE_TOKEN_PATH", "token.json")
    
    if not client_secrets:
        raise RuntimeError("Set GOOGLE_CLIENT_SECRETS env var")

    fetcher = GmailFetcher(client_secrets_file=client_secrets, token_path=token_path)

    # 2. Fetch IDs
    print(f"Fetching last {LIMIT} message IDs...")
    # fetching IDs is fast, so we can fetch a bit more just in case, or exact limit
    msg_ids = fetcher.list_message_ids(q=None, max_results=LIMIT)
    print(f"Found {len(msg_ids)} messages. Processing...")

    results = []

    # 3. Process Sequentially
    for i, mid in enumerate(msg_ids):
        progress = f"[{i+1}/{len(msg_ids)}]"
        try:
            # Fetch content
            m = fetcher.get_message(mid)
            
            subject = m["headers"].get("Subject", "(no subject)")
            sender = m["headers"].get("From", "")
            raw_body = m.get("body", "")
            cleaned_body = clean_email_body(raw_body)
            snippet = m.get("snippet", "")

            # Unified Classification
            classification, should_notify, reason, source = EmailClassifier.classify_email(sender, subject, cleaned_body)

            print(f"{progress} Classified as: {classification} (via {source})")

            # Data Object
            email_data = {
                "id": m["id"],
                "subject": subject,
                "sender": sender,
                "snippet": snippet,
                "body_preview": cleaned_body[:200],
                "full_body": cleaned_body,
                "classification": {
                    "category": classification,
                    "should_notify": should_notify,
                    "reason": reason,
                    "source": source
                },
                "processed_at": datetime.now().isoformat()
            }
            
            results.append(email_data)
            
            # Optional: Incremental save or sleep to respect rate limits? 
            # Sequential calls usually fine for Gmail API quotas unless massive concurrency.
            
        except Exception as e:
            print(f"{progress} Error processing message {mid}: {e}")
            continue

    # 4. Save to JSON
    print(f"\nSaving {len(results)} classified emails to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("Done!")

if __name__ == "__main__":
    main()
