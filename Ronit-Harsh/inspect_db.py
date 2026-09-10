import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def inspect():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    supabase = create_client(url, key)
    
    print("--- 🔍 Inspecting Embeddings ---")
    
    # 1. Check total count
    count = supabase.table("embeddings").select("id", count="exact").execute()
    print(f"Total Embeddings: {count.count}")
    
    # 2. Check for PDF content
    # We look for the marker we added: "[FILE CONTENT:"
    res = supabase.table("embeddings")\
        .select("content, item_id")\
        .ilike("content", "%FILE CONTENT:%")\
        .limit(5)\
        .execute()
        
    if res.data:
        print(f"\n✅ Found {len(res.data)} chunks with PDF content!")
        for item in res.data:
            print(f"-- Chunk --\n{item['content'][:200]}...\n")
    else:
        print("\n❌ NO PDF CONTENT FOUND in embeddings!")
        print("Possible causes:")
        print("1. Ingestion failed to download the PDF.")
        print("2. PDF was not text-selectable (image scan).")
        print("3. Ingestion loop didn't trigger for the file.")

if __name__ == "__main__":
    inspect()
