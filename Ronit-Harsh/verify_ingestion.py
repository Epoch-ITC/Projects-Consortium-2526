import os
from supabase import create_client
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Initialize Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Use service role to bypass RLS for checking

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not found in .env")
    exit(1)

supabase = create_client(url, key)

def verify():
    print("--- 🔍 Verifying Ingestion Data ---")

    # 1. Check Integrations
    integrations = supabase.table("user_integrations").select("*").execute()
    print(f"\n✅ User Integrations Found: {len(integrations.data)}")
    for i in integrations.data:
        print(f"   - User: {i['user_id']} | Status: {i['sync_status']} | Progress: {i['sync_progress']}%")

    if not integrations.data:
        print("❌ No integrations found. Did you connect Google Classroom?")
        return

    user_id = integrations.data[0]['user_id']

    # 2. Check Courses
    courses = supabase.table("courses").select("*").eq("user_id", user_id).execute()
    print(f"\n📚 Courses Found: {len(courses.data)}")
    for c in courses.data:
        print(f"   - {c['name']} (ID: {c['classroom_id']})")

    # 3. Check Inbox Items (Assignments/Announcements)
    items = supabase.table("inbox_items").select("*").eq("user_id", user_id).execute()
    print(f"\n📝 Inbox Items Found: {len(items.data)}")
    
    # Check for attachments
    items_with_files = [i for i in items.data if i['files_data']]
    print(f"   - Items with Attachments: {len(items_with_files)}")
    
    if items_with_files:
        sample = items_with_files[0]
        print(f"   - Sample Attachment Data ({sample['title']}):")
        print(json.dumps(sample['files_data'], indent=4))

    # 4. Check Embeddings (Vector Store)
    # listing just count for now
    embeddings = supabase.table("embeddings").select("id", count="exact").eq("user_id", user_id).execute()
    count = embeddings.count
    print(f"\n🧠 Embeddings Found: {count}")
    
    if count > 0:
        print("   ✅ Vector store is being populated!")
    else:
        print("   ⚠️ No embeddings found. Ingestion might still be in progress or failed.")

if __name__ == "__main__":
    verify()
