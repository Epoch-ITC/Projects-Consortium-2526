import logging
import os
import datetime
from typing import Dict, Any
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from supabase import create_client
import json

from src.brain.core.mcp_tool import MCPTool

logger = logging.getLogger(__name__)

# Path to OAuth client secrets (project root: src/brain/tools -> src/brain -> src -> root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CREDENTIALS_FILE = os.getenv("GOOGLE_CLIENT_SECRETS", os.path.join(BASE_DIR, 'credentials', 'client_secrets.json'))


class SchedulerTool(MCPTool):
    def __init__(self):
        self._supabase = None

    @property
    def name(self) -> str:
        return "scheduler"

    @property
    def description(self) -> str:
        return (
            "The Master Schedule & Todo Manager. "
            "Actions: "
            "'get_schedule' — view calendar events + deadlines in a time range (checks BOTH primary & scholr calendars). "
            "'schedule_event' — create a calendar event on the 'scholr' calendar. "
            "'create_todo' — add a task to the user's todo list (also syncs to scholr calendar). "
            "'list_todos' — list the user's pending (incomplete) todos. "
            "'complete_todo' — mark a todo as complete. "
            "IMPORTANT: ALWAYS call 'get_schedule' FIRST before suggesting new events/todos, to check for time conflicts."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_schedule", "schedule_event", "create_todo", "list_todos", "complete_todo"],
                    "description": "Action to perform."
                },
                "start_time": {
                    "type": "string",
                    "description": "ISO 8601 (e.g. 2025-01-20T00:00:00+05:30). Required for get_schedule, schedule_event."
                },
                "end_time": {
                    "type": "string",
                    "description": "ISO 8601. Required for get_schedule and schedule_event."
                },
                "title": {
                    "type": "string",
                    "description": "Title for new event or todo."
                },
                "description": {
                    "type": "string",
                    "description": "Optional description for todo."
                },
                "due_at": {
                    "type": "string",
                    "description": "ISO 8601 datetime for when the todo is due. Used with create_todo."
                },
                "todo_id": {
                    "type": "string",
                    "description": "UUID of the todo to complete. Used with complete_todo."
                }
            },
            "required": ["action"]
        }

    def _get_supabase(self):
        if not self._supabase:
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", os.environ.get("SUPABASE_KEY"))
            self._supabase = create_client(url, key)
        return self._supabase

    def _get_gcal_service(self, user_id: str):
        """Build GCal service from per-user tokens stored in user_integrations."""
        sb = self._get_supabase()
        integration = sb.table("user_integrations")\
            .select("access_token, refresh_token, expires_at, scholr_calendar_id")\
            .eq("user_id", user_id)\
            .eq("provider", "google_calendar")\
            .maybe_single()\
            .execute()
        
        if not integration.data or not integration.data.get("access_token"):
            return None, None
        
        # Load client config
        with open(CREDENTIALS_FILE, "r") as f:
            cred_data = json.load(f)
        client_config = cred_data.get("web", cred_data.get("installed", {}))
        
        creds = Credentials(
            token=integration.data["access_token"],
            refresh_token=integration.data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_config["client_id"],
            client_secret=client_config["client_secret"],
        )
        
        # Refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            sb.table("user_integrations").update({
                "access_token": creds.token,
                "expires_at": creds.expiry.isoformat() if creds.expiry else None,
            }).eq("user_id", user_id).eq("provider", "google_calendar").execute()
        
        service = build('calendar', 'v3', credentials=creds)
        scholr_calendar_id = integration.data.get("scholr_calendar_id")
        return service, scholr_calendar_id

    def execute(self, action: str, user_id: str = None, **kwargs) -> str:
        try:
            if action == "get_schedule":
                start_time = kwargs.get("start_time")
                end_time = kwargs.get("end_time")
                if not start_time or not end_time:
                    return "Error: start_time and end_time are required for get_schedule."
                return self._get_unified_schedule(user_id, start_time, end_time)
            
            elif action == "schedule_event":
                title = kwargs.get("title")
                start_time = kwargs.get("start_time")
                end_time = kwargs.get("end_time")
                if not title or not start_time or not end_time:
                    return "Error: title, start_time, and end_time required for schedule_event."
                return self._create_gcal_event(user_id, title, start_time, end_time)
            
            elif action == "create_todo":
                title = kwargs.get("title")
                if not title:
                    return "Error: title is required for create_todo."
                return self._create_todo(user_id, title, kwargs.get("due_at"), kwargs.get("description"))
            
            elif action == "list_todos":
                return self._list_todos(user_id)
            
            elif action == "complete_todo":
                todo_id = kwargs.get("todo_id")
                if not todo_id:
                    return "Error: todo_id is required for complete_todo."
                return self._complete_todo(user_id, todo_id)
            
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            logger.error(f"Scheduler Error: {e}")
            return f"Error: {e}"

    def _get_unified_schedule(self, user_id: str, start: str, end: str) -> str:
        timeline = []

        # Ensure timezone suffix
        start_tz = start if ('+' in start or start.endswith('Z')) else start + '+05:30'
        end_tz = end if ('+' in end or end.endswith('Z')) else end + '+05:30'

        # 1. Fetch Google Calendar (primary + scholr)
        service, scholr_cal_id = self._get_gcal_service(user_id) if user_id else (None, None)
        if service:
            for cal_id, cal_label in [('primary', 'GCAL'), (scholr_cal_id, 'SCHOLR')]:
                if not cal_id:
                    continue
                try:
                    events_result = service.events().list(
                        calendarId=cal_id, timeMin=start_tz, timeMax=end_tz,
                        singleEvents=True, orderBy='startTime'
                    ).execute()
                    for e in events_result.get('items', []):
                        s = e['start'].get('dateTime', e['start'].get('date'))
                        timeline.append({
                            "time": s,
                            "source": cal_label,
                            "title": e.get('summary', 'Busy'),
                            "link": e.get('htmlLink')
                        })
                except Exception as e:
                    logger.error(f"{cal_label} fetch failed: {e}")
        else:
            timeline.append({"time": start, "source": "INFO", "title": "Google Calendar not connected. Connect it from Integrations page."})

        # 2. Fetch Supabase Deadlines
        try:
            sb = self._get_supabase()
            resp = sb.table("inbox_items").select("due_date, title, type, course_id")\
                .gte("due_date", start).lte("due_date", end)
            if user_id:
                resp = resp.eq("user_id", user_id)
            resp = resp.execute()
            
            for item in resp.data:
                timeline.append({
                    "time": item['due_date'],
                    "source": "DEADLINE",
                    "title": f"[{item['type']}] {item['title']}",
                })
        except Exception as e:
            logger.error(f"Supabase deadline fetch failed: {e}")

        # 3. Fetch pending todos
        try:
            sb = self._get_supabase()
            resp = sb.table("todos").select("title, due_at, priority")\
                .eq("is_completed", False)
            if user_id:
                resp = resp.eq("user_id", user_id)
            resp = resp.gte("due_at", start).lte("due_at", end).execute()
            
            for item in resp.data:
                timeline.append({
                    "time": item.get('due_at', ''),
                    "source": "TODO",
                    "title": f"[{item['priority'].upper()}] {item['title']}",
                })
        except Exception as e:
            logger.error(f"Todos fetch failed: {e}")

        # 4. Sort and format
        timeline.sort(key=lambda x: x.get('time', ''))

        if not timeline:
            return "No events, deadlines, or todos found in this period. Schedule is free!"

        output = [f"=== Schedule ({start} to {end}) ==="]
        for t in timeline:
            icons = {"GCAL": "📅", "SCHOLR": "📋", "DEADLINE": "⏰", "TODO": "✅", "INFO": "ℹ️"}
            icon = icons.get(t['source'], "•")
            output.append(f"{icon} {t['time']} | {t['source']} | {t['title']}")
        
        return "\n".join(output)

    def _create_gcal_event(self, user_id: str, summary: str, start: str, end: str) -> str:
        service, scholr_cal_id = self._get_gcal_service(user_id) if user_id else (None, None)
        if not service or not scholr_cal_id:
            return "Error: Google Calendar not connected. Please connect from Integrations page."
        
        event = {
            'summary': summary,
            'start': {'dateTime': start, 'timeZone': 'Asia/Kolkata'},
            'end': {'dateTime': end, 'timeZone': 'Asia/Kolkata'},
        }
        event = service.events().insert(calendarId=scholr_cal_id, body=event).execute()
        return f"Event created on scholr calendar: {event.get('htmlLink')}"

    def _create_todo(self, user_id: str, title: str, due_at: str = None, description: str = None) -> str:
        sb = self._get_supabase()
        
        todo_data = {
            "user_id": user_id,
            "title": title,
            "description": description,
            "due_at": due_at,
            "source": "chat",
        }
        
        # Try to create GCal event
        gcal_event_id = None
        if due_at:
            service, scholr_cal_id = self._get_gcal_service(user_id) if user_id else (None, None)
            if service and scholr_cal_id:
                try:
                    due_dt = datetime.datetime.fromisoformat(due_at)
                    end_dt = due_dt + datetime.timedelta(minutes=15)  # Deadline marker
                    event = {
                        'summary': title,
                        'description': description or '',
                        'start': {'dateTime': due_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
                        'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
                    }
                    created = service.events().insert(calendarId=scholr_cal_id, body=event).execute()
                    gcal_event_id = created.get('id')
                except Exception as e:
                    logger.error(f"GCal event creation failed: {e}")
        
        todo_data["gcal_event_id"] = gcal_event_id
        result = sb.table("todos").insert(todo_data).execute()
        
        cal_note = " (also added to scholr calendar)" if gcal_event_id else ""
        due_note = f" due at {due_at}" if due_at else ""
        return f"Todo created: '{title}'{due_note}{cal_note}"

    def _list_todos(self, user_id: str) -> str:
        sb = self._get_supabase()
        query = sb.table("todos").select("id, title, due_at, priority, is_completed, source")\
            .eq("is_completed", False)\
            .order("due_at", desc=False)
        if user_id:
            query = query.eq("user_id", user_id)
        
        result = query.execute()
        
        if not result.data:
            return "No pending todos. Your task list is clear! 🎉"
        
        output = [f"=== Pending Todos ({len(result.data)}) ==="]
        for t in result.data:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t['priority'], "⚪")
            due = f" (due: {t['due_at']})" if t.get('due_at') else ""
            output.append(f"{priority_icon} {t['title']}{due} [id: {t['id'][:8]}...]")
        
        return "\n".join(output)

    def _complete_todo(self, user_id: str, todo_id: str) -> str:
        sb = self._get_supabase()
        
        # Verify ownership
        existing = sb.table("todos").select("title, gcal_event_id")\
            .eq("id", todo_id).eq("user_id", user_id).maybe_single().execute()
        
        if not existing.data:
            return f"Error: Todo not found (id: {todo_id})"
        
        sb.table("todos").update({
            "is_completed": True,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }).eq("id", todo_id).execute()
        
        return f"Todo '{existing.data['title']}' marked as complete ✅"
