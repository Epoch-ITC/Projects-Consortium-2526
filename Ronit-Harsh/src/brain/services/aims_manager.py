import logging
from src.brain.services.load_aims import get_grades
from supabase import Client

logger = logging.getLogger(__name__)

class AimsManager:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client

    async def sync_user_grades(self, user_id: str, username: str, password: str):
        """
        Fetches grades from AIMS and syncs them to Supabase.
        Runs the synchronous Playwright code in a separate thread.
        """
        import asyncio
        
        try:
            logger.info(f"Fetching AIMS data for user {user_id}...")
            
            # 1. Fetch data in a separate thread to avoid blocking asyncio loop
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, lambda: get_grades(username, password))
            
            # Temporary: dump raw AIMS data to file for inspection
            import json
            with open("aims_debug_output.json", "w") as f:
                json.dump(data, f, indent=2, default=str)
            logger.info("AIMS data dumped to aims_debug_output.json")
            
            if not data or "grades" not in data:
                raise ValueError("Invalid data received from AIMS")

            # 2. Clear old data for a clean resync
            self.supabase.table("student_grades").delete().eq("user_id", user_id).execute()
            self.supabase.table("student_gpa").delete().eq("user_id", user_id).execute()
            logger.info(f"Cleared previous AIMS data for user {user_id}")

            # 3. Process and insert Grades
            grades_payload = []
            for g in data.get("grades", []):
                grades_payload.append({
                    "user_id": user_id,
                    "course_code": g.get("courseCd"),
                    "course_name": g.get("courseName"),
                    "credits": float(g.get("credits", 0)),
                    "grade": g.get("gradeDesc"),
                    "semester": g.get("periodName"),
                    "segment": g.get("segment"),
                    "course_type": g.get("courseElectiveTypeDesc"),
                    "instructor": g.get("instructorName"),
                    "registration_type": g.get("courseRegTypeDesc")
                })

            if grades_payload:
                self.supabase.table("student_grades").insert(grades_payload).execute()
                logger.info(f"Inserted {len(grades_payload)} grades.")

            # 4. Process and insert GPA
            gpa_payload = []
            for g in data.get("gpa", []):
                sgpa_val = g.get("sgpa")
                cgpa_val = g.get("cgpa")
                
                # Handle '-' or empty strings
                sgpa = float(sgpa_val) if sgpa_val and sgpa_val not in ["-", ""] else None
                cgpa = float(cgpa_val) if cgpa_val and cgpa_val not in ["-", ""] else None

                gpa_payload.append({
                    "user_id": user_id,
                    "semester": g.get("periodName"),
                    "sgpa": sgpa,
                    "cgpa": cgpa
                })

            if gpa_payload:
                self.supabase.table("student_gpa").insert(gpa_payload).execute()
                logger.info(f"Inserted {len(gpa_payload)} GPA records.")

            return True

        except Exception as e:
            logger.error(f"Failed to sync AIMS data: {type(e).__name__}: {e}", exc_info=True)
            raise e
