import logging
import os
from pathlib import Path
from typing import Dict, Any
from supabase import create_client

from src.brain.core.mcp_tool import MCPTool

logger = logging.getLogger(__name__)

class ProfileTool(MCPTool):
    @property
    def name(self) -> str:
        return "get_user_profile"

    @property
    def description(self) -> str:
        return "Fetch the student's profile (name, degree, preferences)."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    def execute(self) -> str:
        try:
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_KEY")
            if not url or not key:
                return "Error: Supabase credentials missing."

            supabase = create_client(url, key)
            
            # For now, we fetch the first profile since there's no auth context in this script
            resp = supabase.table("profiles").select("*").limit(1).execute()
            
            if resp.data:
                return str(resp.data[0])
            else:
                return "No profile found."
        except Exception as e:
            return f"Error fetching profile: {e}"
