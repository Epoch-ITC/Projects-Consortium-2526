import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from huggingface_hub import InferenceClient

from src.brain.core.mcp_tool import MCPTool

logger = logging.getLogger(__name__)

# Hugging Face model (same model, 768-dim vectors)
HF_EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

# Constants
BASE_DIR = Path(__file__).resolve().parents[3]

class KnowledgeRetriever(MCPTool):
    def __init__(self):
        self._supabase = None
        self._hf_token = None
        self._hf_client = None

    def set_hf_token(self, token: str):
        """Set the Hugging Face token for embedding API calls."""
        self._hf_token = token
        self._hf_client = None  # Reset client so it gets recreated with new token

    def _get_hf_client(self) -> InferenceClient:
        if self._hf_client is None:
            if not self._hf_token:
                raise ValueError("Hugging Face token not configured. Please add it in Settings.")
            self._hf_client = InferenceClient(provider="hf-inference", api_key=self._hf_token)
        return self._hf_client

    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text via Hugging Face Inference API."""
        client = self._get_hf_client()
        result = client.feature_extraction(text, model=HF_EMBEDDING_MODEL)
        # Result is a numpy array or nested list — convert to list
        if hasattr(result, 'tolist'):
            return result.tolist()
        return result

    @property
    def name(self) -> str:
        return "knowledge_retriever"

    @property
    def description(self) -> str:
        return (
            "Access the student knowledge base. Three modes:\n"
            "1. List Courses: Get a map of Course Name -> Course ID. ALWAYS call this first if filtering by course.\n"
            "2. Search: Find relevant snippets (chunks) from course materials using a query.\n"
            "3. Read: Get the FULL text content of a specific item (assignment/file) by its ID."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search", "read", "list_courses"],
                    "description": "Action to perform: 'list_courses' (to find IDs), 'search' (to find content), or 'read' (to get full details)."
                },
                "query": {
                    "type": "string",
                    "description": "Required for 'search'."
                },
                "course_id": {
                    "type": "string",
                    "description": "Optional for 'search'. The UUID of the course to filter by."
                },
                "item_id": {
                    "type": "string",
                    "description": "Required for 'read'. The UUID of the item to fetch full content for."
                },
                "n_results": {
                    "type": "integer",
                    "default": 10,
                    "description": "For search: Number of chunks to return."
                }
            },
            "required": ["action"]
        }

    def _get_supabase(self) -> Client:
        if self._supabase:
            return self._supabase
        
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Use Service Role for backend agent actions
        if not url or not key:
            raise ValueError("Supabase credentials missing.")
            
        self._supabase = create_client(url, key)
        return self._supabase

    def execute(self, action: str, user_id: str = None, query: str = None, course_id: str = None, item_id: str = None, n_results: int = 5) -> str:
        if not user_id:
            return "Error: user_id is required for all knowledge operations."

        try:
            if action == "search":
                return self._search(user_id, query, course_id, n_results)
            elif action == "read":
                return self._read_item(user_id, item_id)
            elif action == "list_courses":
                return self._list_courses(user_id)
            else:
                return "Invalid action."
        except Exception as e:
            logger.error(f"Error in KnowledgeRetriever: {e}")
            return f"Error: {e}"

    def _list_courses(self, user_id: str) -> str:
        sb = self._get_supabase()
        resp = sb.table("courses").select("id, name, classroom_id").eq("user_id", user_id).execute()
        
        if not resp.data:
            return "No courses found for this user."
            
        # Format as a clear list for the LLM
        output = ["=== AVAILABLE COURSES ==="]
        for c in resp.data:
            output.append(f"- Name: {c['name']} | ID: {c['id']} | ClassroomID: {c['classroom_id']}")
        
        return "\n".join(output)

    def _search(self, user_id: str, query: str, course_id: str, n_results: int) -> str:
        if not query:
            return "Error: 'query' is required for search."

        # Generate Embedding via Hugging Face API
        query_vector = self._get_embedding(query)
        
        # Prepare RPC params
        params = {
            "query_embedding": query_vector,
            "match_threshold": 0.15, # Lowered to capture broad semantic matches
            "match_count": n_results,
            "_user_id": user_id,
            "_course_id": course_id if course_id else None
        }
        
        # Execute RPC
        sb = self._get_supabase()
        resp = sb.rpc("match_embeddings", params).execute()
        
        results = resp.data
        if not results:
            return f"No relevant information found for '{query}'."

        formatted = []
        for i, item in enumerate(results):
            similarity = item.get('similarity', 0)
            formatted.append(
                f"--- Result {i+1} (Similarity: {similarity:.2f}) ---\n"
                f"Title: {item['title']}\n"
                f"Type: {item['type']}\n"
                f"Item ID: {item['item_id']} (Use this ID to 'read' full text)\n"
                f"Content Snippet: {item['content']}...\n"
            )
        
        return "\n".join(formatted)

    def _read_item(self, user_id: str, item_id: str) -> str:
        if not item_id:
            return "Error: 'item_id' is required for read."

        sb = self._get_supabase()
        
        # Fetch from Supabase with user_id check for security
        resp = sb.table("inbox_items").select("*").eq("id", item_id).eq("user_id", user_id).execute()
        
        if not resp.data:
            return "Item not found or access denied."
            
        item = resp.data[0]
        
        title = item.get("title")
        description = item.get("description", "")
        files_data = item.get("files_data", [])

        # Format Full Content
        output = [f"=== FULL CONTENT: {title} ===\n"]
        
        if description:
            output.append(f"## Description:\n{description}\n")

        if files_data:
            output.append("## Attached Files:")
            for f in files_data:
                f_title = f.get("title")
                f_url = f.get("url")
                
                output.append(f"\n- {f_title}")
                if f_url:
                    output.append(f"  Link: {f_url}")
                output.append("-" * 30)

        return "\n".join(output)
