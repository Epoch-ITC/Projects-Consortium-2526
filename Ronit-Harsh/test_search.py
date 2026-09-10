import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client
from sentence_transformers import SentenceTransformer

load_dotenv()
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

def test_search():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    supabase = create_client(url, key)
    
    # 1. Get User
    users = supabase.table("user_integrations").select("user_id").execute()
    if not users.data: return
    user_id = users.data[0]['user_id']
    
    # 2. Get Course ID
    courses = supabase.table("courses").select("id").ilike("name", "%MA2150%").execute()
    course_id = courses.data[0]['id'] if courses.data else None
    
    print(f"User: {user_id}")
    print(f"Course: {course_id}")
    
    queries = ["syllabus", "course outline", "metric space"]
    
    for q in queries:
        print(f"\n🔎 Testing Query: '{q}'")
        vec = model.encode(q).tolist()
        
        # Call RPC directly without threshold to see raw scores
        params = {
            "query_embedding": vec,
            "match_threshold": 0.0, # Get EVERYTHING
            "match_count": 5,
            "_user_id": user_id,
            "_course_id": course_id
        }
        res = supabase.rpc("match_embeddings", params).execute()
        
        for item in res.data:
            print(f"   Score: {item['similarity']:.4f} | Title: {item['title']} | Content: {item['content'][:50]}...")

if __name__ == "__main__":
    test_search()
