import os
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

import io
import json
from pathlib import Path
from datetime import datetime

import pdfplumber
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()   

# ---------------- CONFIG ----------------
SCOPES= [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
    "https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly",
    "https://www.googleapis.com/auth/classroom.announcements.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/calendar"
]

BASE_DIR = Path(__file__).resolve().parents[2]
CREDENTIALS_FILE = Path(os.getenv("GOOGLE_CLIENT_SECRETS", str(BASE_DIR / "credentials" / "client_secrets.json")))
TOKEN_FILE = BASE_DIR / "token.json"
OUTPUT_FILE = BASE_DIR / "homework.json"

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
# ---------------------------------------


def authenticate():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    return creds

def upsert_course(course_id, name, owner_id="YOUR_USER_ID_HERE"): 
    data = {
        "classroom_id": course_id,
        "name": name,
        # "user_id": owner_id # Uncomment if you have user linking working
    }
    try:
        # We match on classroom_id to update if it exists
        # Returns the list of inserted/updated rows
        response = supabase.table("courses").upsert(data, on_conflict="classroom_id").execute()
        if response.data and len(response.data) > 0:
            return response.data[0]['id']
        return None
    except Exception as e:
        print(f"Error saving course {name}: {e}")
        return None

def upsert_inbox_item(item, internal_course_id):
    due = item.get("due_date")
    data = {
        "source": "CLASSROOM",
        "external_id": item["id"],
        "title": item["type"] + ": " + item["title"], # e.g. "ASSIGNMENT: Lab 1"
        "description_summary": (item["description"] or "")[:500], 
        "type": item["type"],
        "course_id": internal_course_id,
        "due_date": f"{due}T23:59:59Z" if due else None
    }
    try:
        supabase.table("inbox_items").upsert(data, on_conflict="external_id").execute()
        print(f"Saved: {item['title']}")
    except Exception as e:
        print(f"Error saving item {item['title']}: {e}")


# ---------- DRIVE PARSING ----------

def download_file(drive, request):
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    return fh

def get_drive_mime_type(drive, file_id):
    meta = drive.files().get(
        fileId=file_id,
        fields="mimeType"
    ).execute()
    return meta["mimeType"]


def parse_drive_file(drive, file_id, mime_type):
    """
    Convert Drive file into plain text
    """
    # Google Docs
    if mime_type == "application/vnd.google-apps.document":
        request = drive.files().export_media(
            fileId=file_id,
            mimeType="text/plain"
        )
        fh = download_file(drive, request)
        return fh.read().decode("utf-8", errors="ignore")

    # Google Slides
    if mime_type == "application/vnd.google-apps.presentation":
        request = drive.files().export_media(
            fileId=file_id,
            mimeType="text/plain"
        )
        fh = download_file(drive, request)
        return fh.read().decode("utf-8", errors="ignore")

    # Google Sheets
    if mime_type == "application/vnd.google-apps.spreadsheet":
        request = drive.files().export_media(
            fileId=file_id,
            mimeType="text/csv"
        )
        fh = download_file(drive, request)
        return fh.read().decode("utf-8", errors="ignore")

    # PDFs
    if mime_type == "application/pdf":
        request = drive.files().get_media(fileId=file_id)
        fh = download_file(drive, request)
        text = []
        with pdfplumber.open(fh) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
        return "\n".join(text)

    return f"[UNSUPPORTED FILE TYPE: {mime_type}]"


# ---------- CLASSROOM FETCH ----------

def fetch_all_pages(method, key):
    items = []
    page_token = None

    while True:
        resp = method(pageToken=page_token).execute()
        items.extend(resp.get(key, []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return items


def parse_due_date(due):
    if not due:
        return None
    return f"{due.get('year')}-{due.get('month'):02d}-{due.get('day'):02d}"


def fetch_homework():
    creds = authenticate()
    classroom = build("classroom", "v1", credentials=creds)
    drive = build("drive", "v3", credentials=creds)

    results = []

    courses = fetch_all_pages(
        lambda **kw: classroom.courses().list(
            studentId="me",
            courseStates=["ACTIVE"],
            **kw
        ),
        "courses"
    )

    for course in courses:
        course_id = course["id"]
        course_name = course["name"]
        
        # [NEW] Save Course and get UUID
        internal_id = upsert_course(course_id, course_name)

        materials = fetch_all_pages(
            lambda **kw: classroom.courses()
            .courseWorkMaterials()
            .list(courseId=course_id, **kw),
            "courseWorkMaterial"
        )

        assignments = fetch_all_pages(
            lambda **kw: classroom.courses()
            .courseWork()
            .list(courseId=course_id, **kw),
            "courseWork"
        )

        announcements = fetch_all_pages(
            lambda **kw: classroom.courses()
            .announcements()
            .list(courseId=course_id, **kw),
            "announcements"
        )

        all_items = materials + assignments + announcements

        for work in all_items:
            # Determine type
            w_type = work.get("workType")
            if not w_type:
                if "text" in work:
                    w_type = "ANNOUNCEMENT"
                else:
                    w_type = "MATERIAL"

            item = {
                "course": course_name,
                "id": work.get("id"),
                "type": w_type,
                "title": work.get("title", "Announcement"),
                "description": work.get("description") or work.get("text", ""),
                "due_date": parse_due_date(work.get("dueDate")),
                "max_points": work.get("maxPoints"),
                "materials_text": [],
            }

            for mat in work.get("materials", []):
                if "driveFile" in mat:
                    drive_file = mat["driveFile"]["driveFile"]
                    try:
                        file_id = drive_file.get("id")
                        mime_type = drive_file.get("mimeType")

                        if not mime_type and file_id:
                            mime_type = get_drive_mime_type(drive, file_id)

                        text = parse_drive_file(
                            drive,
                            file_id,
                            mime_type,
                        )
                        item["materials_text"].append(text)
                    except Exception as e:
                        item["materials_text"].append(
                            f"[ERROR PARSING FILE: {e}]"
                        )

            results.append(item)
            # [NEW] Save Item if we have a valid course link
            if internal_id:
                upsert_inbox_item(item, internal_id)
            

    return results


if __name__ == "__main__":
    homework = fetch_homework()
    OUTPUT_FILE.write_text(
        json.dumps(homework, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"Saved {len(homework)} items to {OUTPUT_FILE}")
