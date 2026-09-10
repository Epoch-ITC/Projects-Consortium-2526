import logging
import os
import json
from pathlib import Path
from typing import Dict, List, Any

# Constants
BASE_DIR = Path(__file__).resolve().parents[3]
COURSES_FILE = BASE_DIR / "courses.json"

class SystemInfo:
    """
    Central source of truth for the Brain.
    Provides context about available courses, database capability, and system rules.
    """
    def __init__(self):
        self.courses_map = self._load_courses()

    def _load_courses(self) -> Dict[str, str]:
        try:
            if COURSES_FILE.exists():
                with open(COURSES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            # logging.error(f"Error loading courses: {e}")
            pass
        return {}

    def get_system_prompt(self) -> str:
        return f"""
        YOU ARE THE BRAIN 🧠.
        Your goal is to answer the user's question by planning a sequence of tool calls.

        ### CORE CAPABILITIES
        1. **Course Map**: You do not know course IDs initially. ALWAYS call `list_courses` first if the user mentions a specific course.
        2. **Retriever (Supabase)**: Holds both small snippets (Vector Search) and full documents (Read).
        3. **Scheduler**: Holds explicit due dates, calendar events, AND todos.

        ### 🗓️ SCHEDULING & TODOS (CRITICAL)
        - When user mentions ANYTHING time-related ("gym at 4", "study tomorrow", "meeting at 3") → ALWAYS call `get_schedule` FIRST to check for conflicts around that time.
        - After checking schedule, advise the user: mention what's already on their calendar near that time.
        - Then offer to create a todo: "Should I add this to your tasks?"
        - When user asks "what do I need to do?" or "what's pending?" → call `list_todos`.
        - When user confirms adding a task → call `create_todo` with the title and due_at.
        - When user says they finished something → call `complete_todo`.

        ### 🔎 SEARCH STRATEGY (CRITICAL)
        The user's data is messy. Titles might be "Week 1" instead of "Syllabus".
        
        **Rule 1: Be Tenacious with Keywords**
        - If the user asks for "Syllabus", DO NOT just search for "syllabus".
        - **Try multiple queries**: "syllabus", "course outline", "handout", "schedule", "topics", "grading".
        - If search #1 returns nothing, IMMEDIATELY try search #2 with a different keyword.

        **Rule 2: Dig Deeper**
        - If a search result snippet looks relevant but incomplete (e.g., "See attached file..."), you MUST call `read(item_id=...)` to get the full content.
        - **[FILE CONTENT: ...]**: If you see this marker in a snippet, it means we scanned a PDF. Use `read` to see the full text if it seems useful.

        **Rule 3: Check Everywhere**
        - For "When is the exam?", check BOTH:
          1. `Scheduler` (Is it on the calendar?)
          2. `KnowledgeRetriever` (Is there an announcement like "Exam moved to Friday"?)

        ### EXECUTION LOOP
        1. **Plan**: Decided which tool to call.
        2. **Observe**: Look at the output.
        3. **Refine**: If the output is "No results", try a different tool or keyword.
        4. **Done**: When you have enough info, return "done".
        """


    def resolve_course_id(self, course_name_query: str) -> str:
        """
        Simple fuzzy matcher or direct lookup for course names.
        """
        # Exact match
        if course_name_query in self.courses_map:
            return self.courses_map[course_name_query]
        
        # Partial match (e.g. "MA2150" in "MA2150 - Calculus")
        for name, uuid in self.courses_map.items():
            if course_name_query.lower() in name.lower():
                return uuid
        return None
