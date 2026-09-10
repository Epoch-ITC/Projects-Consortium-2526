import os
import uuid
import logging
import json
import io
import threading
import concurrent.futures
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from supabase import Client
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from huggingface_hub import InferenceClient

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Hugging Face model (same model, 768-dim vectors)
HF_EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

class ClassroomIngestor:
    def __init__(self, user_id: str, supabase_client: Client, last_synced_at: Optional[Any] = None, hf_token: Optional[str] = None):
        self.user_id = user_id
        self.supabase = supabase_client
        self.hf_token = hf_token
        self._hf_client = None
        self._hf_client_lock = threading.Lock()  # Guard lazy HF client init across threads
        
        # Normalize last_synced_at (can be string from JSON or datetime from Supabase client)
        self.last_synced_at = None
        if last_synced_at:
            try:
                if isinstance(last_synced_at, str):
                    val = last_synced_at.replace(' ', 'T')
                    self.last_synced_at = datetime.fromisoformat(val.replace('Z', '+00:00'))
                elif isinstance(last_synced_at, datetime):
                    self.last_synced_at = last_synced_at
            except Exception as e:
                logger.warning(f"Failed to parse last_synced_at '{last_synced_at}': {e}")
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )

    def _check_cancelled(self) -> bool:
        """Check if the user has requested cancellation."""
        try:
            data = self.supabase.table("user_integrations")\
                .select("sync_status")\
                .eq("user_id", self.user_id)\
                .eq("provider", "google_classroom")\
                .single().execute()
            return data.data and data.data.get("sync_status") == "cancelled"
        except Exception:
            return False

    def _get_hf_client(self) -> InferenceClient:
        # Thread-safe lazy init
        if self._hf_client is None:
            with self._hf_client_lock:
                if self._hf_client is None:  # double-checked locking
                    if not self.hf_token:
                        raise ValueError("Hugging Face token not configured. Please add it in Settings.")
                    self._hf_client = InferenceClient(provider="hf-inference", api_key=self.hf_token)
        return self._hf_client

    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings via Hugging Face Inference API."""
        client = self._get_hf_client()
        result = client.feature_extraction(texts, model=HF_EMBEDDING_MODEL)
        # Result is a numpy array or nested list — convert to list of lists
        if hasattr(result, 'tolist'):
            return result.tolist()
        return result

    def run(self):
        """Main execution flow — processes courses in parallel using n-1 CPU cores."""
        try:
            logger.info(f"Starting ingestion for user {self.user_id}")
            self._update_status("in_progress", 0)

            # 1. Get Token
            creds = self._get_google_creds()

            # 2. Fetch Courses (single-threaded; cheap API call)
            service = build('classroom', 'v1', credentials=creds)
            courses = self._fetch_courses(service)
            self._update_status("in_progress", 10)

            if not courses:
                self._update_status("success", 100)
                logger.info("No courses found.")
                return

            # 3. Process courses in parallel — use n-1 cores, min 1
            n_workers = max(1, (os.cpu_count() or 2) - 1)
            logger.info(f"Processing {len(courses)} courses with {n_workers} worker(s) (cpu_count={os.cpu_count()})")

            total_items = 0
            processed_courses = 0
            progress_lock = threading.Lock()
            cancelled_event = threading.Event()

            def process_course(course):
                """Process a single course in a worker thread."""
                if cancelled_event.is_set():
                    return 0

                # Google API clients are NOT thread-safe — each thread needs its own instances
                thread_service = build('classroom', 'v1', credentials=creds)
                thread_drive = build('drive', 'v3', credentials=creds)

                count = 0
                try:
                    course_uuid = self._upsert_course(course)
                    logger.info(f"Fetching work for course: {course['name']}")

                    # Assignments
                    results_cw = thread_service.courses().courseWork().list(
                        courseId=course['id'], pageSize=100
                    ).execute()
                    for item in results_cw.get('courseWork', []):
                        if cancelled_event.is_set():
                            break
                        if self._is_after_last_sync(item):
                            self._process_item(course_uuid, item, 'ASSIGNMENT', thread_drive)
                            count += 1

                    # Announcements
                    results_ann = thread_service.courses().announcements().list(
                        courseId=course['id'], pageSize=100
                    ).execute()
                    for item in results_ann.get('announcements', []):
                        if cancelled_event.is_set():
                            break
                        if self._is_after_last_sync(item):
                            self._process_item(course_uuid, item, 'ANNOUNCEMENT', thread_drive)
                            count += 1

                except Exception as exc:
                    logger.error(f"Failed to process course '{course.get('name')}': {exc}")

                # Update shared progress (thread-safe)
                nonlocal total_items, processed_courses
                with progress_lock:
                    total_items += count
                    processed_courses += 1
                    progress = 10 + int(processed_courses / len(courses) * 80)
                    self._update_status("in_progress", progress)
                    # Propagate cancellation signal to other threads
                    if self._check_cancelled():
                        cancelled_event.set()

                return count

            with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as executor:
                futures = {executor.submit(process_course, course): course for course in courses}
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        course = futures[future]
                        logger.error(f"Unhandled error in course '{course.get('name')}': {e}")

                    if cancelled_event.is_set():
                        # Signal remaining queued futures to exit early
                        for f in futures:
                            f.cancel()
                        break

            if cancelled_event.is_set():
                logger.info(f"Sync cancelled after processing {total_items} items.")
                self._update_status("idle", 0)
            else:
                self._update_status("success", 100)
                logger.info(f"Ingestion complete! Processed {total_items} items across {len(courses)} courses.")

        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            self._update_status("error", 0)
            # Don't re-raise — server must keep running
            
    def _get_google_creds(self):
        data = self.supabase.table("user_integrations")\
            .select("*").eq("user_id", self.user_id).eq("provider", "google_classroom")\
            .single().execute()
        
        record = data.data
        if not record:
            raise ValueError("No integration found")

        # Read client_id and client_secret from the OAuth secrets file
        secrets_path = os.getenv("GOOGLE_CLIENT_SECRETS", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'credentials', 'client_secrets.json'))
        with open(secrets_path, 'r') as f:
            secrets = json.load(f)
        
        # Handle both 'web' and 'installed' client types
        client_config = secrets.get('web') or secrets.get('installed', {})
        client_id = client_config.get('client_id')
        client_secret = client_config.get('client_secret')

        creds = Credentials(
            token=record['access_token'],
            refresh_token=record['refresh_token'],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret
        )
        
        # Refresh if expired
        if creds.expired or not creds.valid:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            # Update stored tokens
            self.supabase.table("user_integrations").update({
                "access_token": creds.token,
                "expires_at": creds.expiry.isoformat() if creds.expiry else None
            }).eq("user_id", self.user_id).eq("provider", "google_classroom").execute()
            logger.info("Refreshed expired Google credentials")
        
        return creds

    def _update_status(self, status: str, progress: int):
        payload = {
            "sync_status": status,
            "sync_progress": progress
        }
        # Only update the timestamp on successful completion
        if status == "success":
            payload["last_synced_at"] = datetime.now(timezone.utc).isoformat()
            
        self.supabase.table("user_integrations").update(payload)\
            .eq("user_id", self.user_id).eq("provider", "google_classroom").execute()

    def _fetch_courses(self, service):
        results = service.courses().list(pageSize=10).execute()
        return results.get('courses', [])

    def _is_after_last_sync(self, item) -> bool:
        """Check if an item was updated after the last sync time.
        If no last_synced_at is set (first sync), always returns True."""
        if not self.last_synced_at:
            return True  # Full sync — process everything
        
        # Google Classroom items have 'updateTime' in ISO format
        update_time_str = item.get('updateTime')
        if not update_time_str:
            return True  # No updateTime — process to be safe
        
        try:
            # item_update is always a string from API
            item_update = datetime.fromisoformat(update_time_str.replace('Z', '+00:00'))
            
            # self.last_synced_at is already normalized to datetime in __init__
            is_new = item_update > self.last_synced_at
            
            if not is_new:
                logger.debug(f"Skipping old item {item.get('id')} (updated {item_update}, last sync {self.last_synced_at})")
            return is_new
        except (ValueError, TypeError) as e:
            logger.warning(f"Timestamp comparison failed for {item.get('id')}: {e}")
            return True  # Parse error — process to be safe

    def _upsert_course(self, course_data) -> str:
        """Upserts course and returns internal UUID"""
        # Create deterministic UUID based on User + ClassroomID
        # This ensures if multiple users access same course, they get different DB entries (correct for RLS)
        c_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{self.user_id}_{course_data['id']}"))
        
        payload = {
            "id": c_uuid,
            "user_id": self.user_id,
            "classroom_id": course_data['id'],
            "name": course_data['name']
        }
        self.supabase.table("courses").upsert(payload).execute()
        return c_uuid

    def _extract_drive_content(self, drive_service, file_id, title) -> str:
        """Downloads and extracts text from a PDF file in Google Drive"""
        try:
            if not title.lower().endswith(".pdf"):
                return "" # Skip non-PDFs for now (or implement logic for Docs/Slides)

            logger.info(f"📥 Downloading & Parsing PDF: {title}")
            
            # 1. Download File
            request = drive_service.files().get_media(fileId=file_id)
            file_stream = io.BytesIO()
            downloader = MediaIoBaseDownload(file_stream, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()

            # 2. Extract Text
            file_stream.seek(0)
            reader = PdfReader(file_stream)
            text = []
            for page in reader.pages:
                text.append(page.extract_text())
            
            full_text = "\n".join(text)
            return f"\n\n[FILE CONTENT: {title}]\n{full_text}\n"

        except Exception as e:
            logger.warning(f"Failed to extract content from {title}: {e}")
            return f"\n[FILE ERROR: Could not read {title}]"

    def _process_item(self, course_uuid, item, item_type, drive_service):
        try:
            # 1. Extract Details
            item_id = item['id']
            # Announcements might have 'text' instead of 'description', and no title
            title = item.get('title', 'Announcement')
            
            if item_type == 'ANNOUNCEMENT':
                 desc = item.get('text', '')
            else:
                 desc = item.get('description', '')
                 
            # 2. Extract Materials & Content
            files_data = []
            materials = item.get('materials', [])
            
            # DEEP INGESTION: Append file content to description for indexing
            deep_content = ""
            
            for mat in materials:
                if 'driveFile' in mat:
                    df = mat['driveFile']['driveFile']
                    file_id = df.get('id')
                    file_title = df.get('title')
                    
                    files_data.append({
                        "type": "drive_file",
                        "title": file_title,
                        "url": df.get('alternateLink'),
                        "id": file_id
                    })
                    
                    # Extract Data
                    if file_id and file_title:
                        deep_content += self._extract_drive_content(drive_service, file_id, file_title)
                        
                elif 'youtubeVideo' in mat:
                    yt = mat['youtubeVideo']
                    files_data.append({
                        "type": "youtube",
                        "title": yt.get('title'),
                        "url": yt.get('alternateLink'),
                        "id": yt.get('id')
                    })
                elif 'link' in mat:
                    lnk = mat['link']
                    files_data.append({
                        "type": "link",
                        "title": lnk.get('title'),
                        "url": lnk.get('url')
                    })
            
            # Combine original desc + file content
            full_indexable_text = f"Title: {title}\nDescription: {desc}\n{deep_content}"
            
            # 3. Create Deterministic ID
            item_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{self.user_id}_{item_id}"))
            
            # 4. Upsert Item
            sb_payload = {
                "id": item_uuid,
                "user_id": self.user_id,
                "course_id": course_uuid,
                "external_id": item_id,
                "type": item_type,
                "title": title,
                "description": desc, # Store original description for display
                "files_data": files_data
            }
            if 'dueDate' in item:
                # Naive date handling, assume DueTime usually sets timezone
                # item['dueDate'] = {'year': 2023, 'month': 5, 'day': 12}
                d = item['dueDate']
                t = item.get('dueTime', {'hours': 23, 'minutes': 59})
                dt = datetime(d['year'], d['month'], d['day'], t.get('hours',0), t.get('minutes',0))
                sb_payload['due_date'] = dt.isoformat()
                
            self.supabase.table("inbox_items").upsert(sb_payload).execute()
            
            # 5. Handle Embeddings (PGVector)
            # Remove old embeddings for this item first (to avoid duplicates on re-sync)
            self.supabase.table("embeddings").delete().eq("item_id", item_uuid).execute()
            
            # Chunk the DEEP CONTENT
            chunks = self.text_splitter.split_text(full_indexable_text)
            
            if chunks:
                embeddings = self._get_embeddings(chunks)
                rows = []
                for i, chunk in enumerate(chunks):
                    rows.append({
                        "user_id": self.user_id,
                        "item_id": item_uuid,
                        "content": chunk, # This now contains PDF text
                        "embedding": embeddings[i]
                    })
                
                if rows:
                    self.supabase.table("embeddings").insert(rows).execute()
                    
        except Exception as e:
            logger.error(f"Failed to process assignment {item.get('id')}: {e}")


