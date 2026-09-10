from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks, Request, UploadFile, File
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import os

# Fix: allow Google OAuth to return more scopes than requested (e.g., calendar + classroom combined)
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

from src.brain.agent import Agent
from src.services.class_ingestor import ClassroomIngestor
from supabase import create_client, Client
import os
import concurrent.futures
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Env
from dotenv import load_dotenv
load_dotenv()

# Get environment variables
FRONTEND_URLS = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Parse comma-separated URLs
allowed_origins = [url.strip() for url in FRONTEND_URLS.split(",") if url.strip()]
if not allowed_origins:
    allowed_origins = ["http://localhost:3000"]
    
DEFAULT_FRONTEND_URL = allowed_origins[0]
allowed_origins.append("*")
print(f"Allowed Origins: {allowed_origins}")
print(f"Default Frontend URL: {DEFAULT_FRONTEND_URL}")
print(f"Backend URL: {BACKEND_URL}")

app = FastAPI()

# Trust proxy headers from ngrok/dev tunnels
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Agent
try:
    agent = Agent()
    logger.info("Agent initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize agent: {e}")
    raise e

# Initialize Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
service_key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(url, key)
supabase_admin: Client = create_client(url, service_key) if service_key else None

if not supabase_admin:
    logger.warning("SUPABASE_SERVICE_ROLE_KEY not found. Admin operations may fail.")

# Dedicated thread pool for heavy background ingestion tasks.
# Runs completely off the asyncio event loop so API requests stay responsive.
_ingestor_pool = concurrent.futures.ThreadPoolExecutor(
    max_workers=max(1, (os.cpu_count() or 2) - 1),
    thread_name_prefix="ingestor",
)


class ChatRequest(BaseModel):
    message: str
    chat_id: str

class ChatResponse(BaseModel):
    response: str

class CreateChatRequest(BaseModel):
    title: str = "New Chat"

async def get_current_user(request: Request, authorization: Optional[str] = Header(None)):
    # Allow OPTIONS requests (CORS preflight) to pass through
    if request.method == "OPTIONS":
        return None
    
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authentication header")
    
    token = authorization.split(" ")[1]
    try:
        user = supabase.auth.get_user(token)
        return user
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/")
async def root():
    return {"status": "ok", "message": "Brain Server is running"}

# --- Chat Management Endpoints ---


@app.post("/chats")
async def create_chat(request: CreateChatRequest, user = Depends(get_current_user)):
    try:
        user_id = user.user.id
        # Use ADMIN client to bypass RLS, we trust user_id from token
        data = supabase_admin.table("chats").insert({
            "user_id": user_id,
            "title": request.title
        }).execute()
        return {"chat": data.data[0]}
    except Exception as e:
        logger.error(f"Error creating chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to create chat")

@app.get("/chats")
async def list_chats(user = Depends(get_current_user)):
    try:
        user_id = user.user.id
        data = supabase_admin.table("chats")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
        return {"chats": data.data}
    except Exception as e:
        logger.error(f"Error listing chats: {e}")
        raise HTTPException(status_code=500, detail="Failed to list chats")

@app.get("/chats/{chat_id}/messages")
async def get_chat_history(chat_id: str, user = Depends(get_current_user)):
    try:
        # Use ADMIN client
        data = supabase_admin.table("messages")\
            .select("*")\
            .eq("chat_id", chat_id)\
            .order("created_at", desc=False)\
            .execute()
        return {"messages": data.data}
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch history")

@app.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str, user = Depends(get_current_user)):
    try:
        user_id = user.user.id
        # Verify the chat belongs to the user
        chat = supabase_admin.table("chats")\
            .select("id")\
            .eq("id", chat_id)\
            .eq("user_id", user_id)\
            .execute()
        
        if not chat.data:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Delete chat (CASCADE will delete messages)
        supabase_admin.table("chats")\
            .delete()\
            .eq("id", chat_id)\
            .execute()
        
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete chat")

ALLOWED_UPLOAD_EXTENSIONS = {".txt", ".md", ".csv", ".py", ".js", ".ts", ".json", ".log", ".xml", ".html", ".css"}

@app.post("/chats/{chat_id}/upload")
async def upload_file_to_chat(chat_id: str, file: UploadFile = File(...), user = Depends(get_current_user)):
    """Upload a text file and save its content as a user message in the chat."""
    try:
        user_id = user.user.id
        
        # Verify chat ownership
        chat = supabase_admin.table("chats")\
            .select("id")\
            .eq("id", chat_id)\
            .eq("user_id", user_id)\
            .execute()
        
        if not chat.data:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Check file extension
        filename = file.filename or "upload.txt"
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_UPLOAD_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type '{ext}'. Supported: {', '.join(ALLOWED_UPLOAD_EXTENSIONS)}"
            )
        
        # Read file content
        content = await file.read()
        try:
            text_content = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File is not a valid text file")
        
        # Truncate very large files
        max_chars = 10000
        if len(text_content) > max_chars:
            text_content = text_content[:max_chars] + f"\n\n... [File truncated at {max_chars} characters]"
        
        # Save as a user message with file context
        file_message = f"📎 **Uploaded file: {filename}**\n\n```\n{text_content}\n```"
        
        supabase_admin.table("messages").insert({
            "chat_id": chat_id,
            "role": "user",
            "content": file_message
        }).execute()
        
        return {
            "status": "uploaded",
            "filename": filename,
            "message": file_message
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user = Depends(get_current_user)):
    try:
        logger.info(f"Received chat message from user {user.user.id} for chat {request.chat_id}")
        
        # Run Agent with Chat ID
        response = agent.run(request.message, user.user.id, request.chat_id)
        
        return ChatResponse(response=response)
    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/integrations")
async def get_user_integrations(user = Depends(get_current_user)):
    try:
        user_id = user.user.id
        # Query user_integrations table for this user
        # We only need provider and sync_status/last_synced_at
        data = supabase_admin.table("user_integrations")\
            .select("provider, sync_status, last_synced_at")\
            .eq("user_id", user_id)\
            .or_("access_token.not.is.null,provider.eq.aims")\
            .execute()
        
        # Filter out Gmail if it hasn't been explicitly synced
        # (Gmail tokens get auto-created during Classroom OAuth, but that doesn't mean Gmail is "connected")
        filtered = [
            i for i in data.data
            if i["provider"] != "gmail" or i.get("sync_status") == "active"
        ]
            
        return {"integrations": filtered}
    except Exception as e:
        logger.error(f"Error fetching integrations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch integrations")

# --- User Settings Endpoints ---

class UserSettingsRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    huggingface_token: Optional[str] = None
    planner_model: str = "gemini-2.5-flash"
    presenter_model: str = "gemini-2.5-flash"

VALID_MODELS = {
    "gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro",
    "gemini-2.5-flash-lite", "gemini-3-pro", "gemini-3-flash"
}

@app.get("/user/settings")
async def get_user_settings(user = Depends(get_current_user)):
    try:
        user_id = user.user.id
        data = supabase_admin.table("user_settings")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        if data.data:
            settings = data.data[0]
            # Mask API key for security — only show last 4 chars
            api_key = settings.get("gemini_api_key") or ""
            masked = f"...{api_key[-4:]}" if len(api_key) > 4 else ""
            # Mask HF token
            hf_token = settings.get("huggingface_token") or ""
            hf_masked = f"...{hf_token[-4:]}" if len(hf_token) > 4 else ""
            return {
                "settings": {
                    "gemini_api_key_masked": masked,
                    "has_api_key": bool(api_key),
                    "hf_token_masked": hf_masked,
                    "has_hf_token": bool(hf_token),
                    "planner_model": settings.get("planner_model", "gemini-2.5-flash"),
                    "presenter_model": settings.get("presenter_model", "gemini-2.5-flash"),
                }
            }
        else:
            return {
                "settings": {
                    "gemini_api_key_masked": "",
                    "has_api_key": False,
                    "hf_token_masked": "",
                    "has_hf_token": False,
                    "planner_model": "gemini-2.5-flash",
                    "presenter_model": "gemini-2.5-flash",
                }
            }
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch settings")

@app.put("/user/settings")
async def update_user_settings(request: UserSettingsRequest, user = Depends(get_current_user)):
    try:
        user_id = user.user.id
        
        # Validate models
        if request.planner_model not in VALID_MODELS:
            raise HTTPException(status_code=400, detail=f"Invalid planner model: {request.planner_model}")
        if request.presenter_model not in VALID_MODELS:
            raise HTTPException(status_code=400, detail=f"Invalid presenter model: {request.presenter_model}")
        
        payload = {
            "user_id": user_id,
            "planner_model": request.planner_model,
            "presenter_model": request.presenter_model,
        }
        
        # Only update API key if provided (non-empty)
        if request.gemini_api_key:
            payload["gemini_api_key"] = request.gemini_api_key
        
        # Only update HF token if provided (non-empty)
        if request.huggingface_token:
            payload["huggingface_token"] = request.huggingface_token
        
        supabase_admin.table("user_settings")\
            .upsert(payload, on_conflict="user_id")\
            .execute()
        
        return {"status": "saved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to save settings")

from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
import os

# Google OAuth Config
SCOPES = [
    'https://www.googleapis.com/auth/classroom.courses.readonly',
    'https://www.googleapis.com/auth/classroom.coursework.me.readonly',
    'https://www.googleapis.com/auth/classroom.announcements.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/gmail.readonly',
]
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.getenv("GOOGLE_CLIENT_SECRETS", os.path.join(PROJECT_ROOT, 'credentials', 'client_secrets.json'))  # Path to OAuth client secrets
    
import json
import base64

@app.get("/auth/google-classroom/authorize")
async def authorize_google_classroom(request: Request, user_id: str, callback_url: str = None):
    if not os.path.exists(CREDENTIALS_FILE):
        raise HTTPException(status_code=500, detail="Credentials file not found")
        
    # Ensure redirect_uri exactly matches Google Cloud Console by using BACKEND_URL env directly
    base_url = BACKEND_URL.rstrip("/")
    dynamic_redirect_uri = f"{base_url}/auth/google-classroom/callback"
    
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=dynamic_redirect_uri
    )
    
    # Fallback if no callback provided
    if not callback_url:
        callback_url = DEFAULT_FRONTEND_URL
        
    # JSON stringify the state
    state_payload = json.dumps({"user_id": user_id, "callback_url": callback_url})
    encoded_state = base64.urlsafe_b64encode(state_payload.encode()).decode()
    
    # Pass encoded state
    # prompt='consent' ensures Google always returns a refresh_token even on re-auth
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=encoded_state,
        prompt='consent'
    )
    
    return RedirectResponse(authorization_url)

@app.get("/auth/google-classroom/callback")
async def google_classroom_callback(request: Request, code: str, background_tasks: BackgroundTasks, state: str = None):
    try:
        # Decode state cautiously
        try:
            decoded_state_str = base64.urlsafe_b64decode(state.encode()).decode()
            state_data = json.loads(decoded_state_str)
            user_id = state_data.get("user_id")
            frontend_redirect = state_data.get("callback_url")
        except Exception:
            # Fallback for old states
            user_id = state
            frontend_redirect = None

        if not frontend_redirect:
            frontend_redirect = DEFAULT_FRONTEND_URL

        if not user_id:
             logger.error("No user_id in state")
             return RedirectResponse(f"{frontend_redirect}/dashboard/integrations?status=error_no_user")

        # The redirect_uri must exactly match what was used in authorize_google_classroom
        base_url = BACKEND_URL.rstrip("/")
        dynamic_redirect_uri = f"{base_url}/auth/google-classroom/callback"
        
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_FILE,
            scopes=SCOPES,
            redirect_uri=dynamic_redirect_uri
        )
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        logger.info(f"Successfully authenticated Google services for user {user_id}")
        
        # Store credentials for BOTH providers since we requested both scopes
        try:
             # Only store tokens if we actually received a valid access token
             if not credentials.token:
                 logger.warning(f"OAuth completed but no access token received for user {user_id}")
                 return RedirectResponse(f"{frontend_redirect}/dashboard/integrations?status=error")

             # Store for Google Classroom
             classroom_payload = {
                 "user_id": user_id,
                 "provider": "google_classroom",
                 "access_token": credentials.token,
                 "refresh_token": credentials.refresh_token,
                 "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
             }
             supabase_admin.table("user_integrations").upsert(classroom_payload).execute()
             logger.info(f"Stored Classroom tokens for user {user_id}")
             
             # Store for Gmail (same tokens, different provider entry)
             gmail_payload = {
                 "user_id": user_id,
                 "provider": "gmail",
                 "access_token": credentials.token,
                 "refresh_token": credentials.refresh_token,
                 "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
             }
             supabase_admin.table("user_integrations").upsert(gmail_payload).execute()
             logger.info(f"Stored Gmail tokens for user {user_id}")

        except Exception as db_e:
            logger.error(f"DB Error saving tokens: {db_e}")
            return RedirectResponse(f"{frontend_redirect}/dashboard/integrations?status=db_error")

        # Fetch user's HF token for embedding
        hf_token = None
        try:
            settings_data = supabase_admin.table("user_settings")\
                .select("huggingface_token")\
                .eq("user_id", user_id)\
                .execute()
            if settings_data.data:
                hf_token = settings_data.data[0].get("huggingface_token")
        except Exception:
            pass

        # Trigger Classroom Ingestion in Background
        ingestor = ClassroomIngestor(user_id, supabase_admin, hf_token=hf_token)
        _ingestor_pool.submit(ingestor.run)

        # Redirect back to frontend
        return RedirectResponse(f"{frontend_redirect}/dashboard/integrations?status=success")
        
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        try:
            decoded_state_str = base64.urlsafe_b64decode(state.encode()).decode()
            frontend_redirect = json.loads(decoded_state_str).get("callback_url", DEFAULT_FRONTEND_URL)
        except:
            frontend_redirect = DEFAULT_FRONTEND_URL
            
        return RedirectResponse(f"{frontend_redirect}/dashboard/integrations?status=error")

@app.post("/classroom/resync")
async def resync_classroom(background_tasks: BackgroundTasks, user = Depends(get_current_user)):
    """Re-sync Google Classroom data. Only fetches items updated since last sync."""
    try:
        user_id = user.user.id
        
        # Get the last synced timestamp
        integration = supabase_admin.table("user_integrations")\
            .select("last_synced_at")\
            .eq("user_id", user_id)\
            .eq("provider", "google_classroom")\
            .single().execute()
        
        if not integration.data:
            raise HTTPException(status_code=400, detail="Google Classroom not connected. Please connect first.")
        
        last_synced_at = integration.data.get("last_synced_at")
        logger.info(f"Starting classroom resync for user {user_id}, last synced: {last_synced_at}")
        
        # Fetch user's HF token for embedding
        hf_token = None
        try:
            settings_data = supabase_admin.table("user_settings")\
                .select("huggingface_token")\
                .eq("user_id", user_id)\
                .execute()
            if settings_data.data:
                hf_token = settings_data.data[0].get("huggingface_token")
        except Exception:
            pass

        # Create ingestor with last_synced_at for incremental sync
        ingestor = ClassroomIngestor(user_id, supabase_admin, last_synced_at=last_synced_at, hf_token=hf_token)
        _ingestor_pool.submit(ingestor.run)
        
        return {"status": "resync_started", "last_synced_at": last_synced_at}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/classroom/cancel-sync")
async def cancel_classroom_sync(user = Depends(get_current_user)):
    """Cancel an in-progress Google Classroom sync."""
    try:
        user_id = user.user.id
        supabase_admin.table("user_integrations").update({
            "sync_status": "cancelled"
        }).eq("user_id", user_id).eq("provider", "google_classroom").execute()
        
        return {"status": "cancelled"}
    except Exception as e:
        logger.error(f"Cancel sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ... existing code ...

# Create AimsManager Instance
from src.brain.services.aims_manager import AimsManager
aims_manager = AimsManager(supabase_admin) # Use Admin client to write

class AimsSyncRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None

@app.options("/aims/sync")
async def aims_sync_options():
    """Handle CORS preflight for aims sync"""
    return {"status": "ok"}

@app.post("/aims/sync")
async def sync_aims(request: AimsSyncRequest, user = Depends(get_current_user)):
    try:
        user_id = user.user.id
        
        # Validate credentials are provided
        if not request.username or not request.password:
            raise HTTPException(status_code=400, detail="Username and password are required")
        
        # Run sync synchronously for now as user waits, but could be background task
        # User requested waiting for loading, so we await it.
        await aims_manager.sync_user_grades(user_id, request.username, request.password)
        
        # Also update user_integrations to show as connected
        supabase_admin.table("user_integrations").upsert({
            "user_id": user_id,
            "provider": "aims",
            "sync_status": "active",
            "last_synced_at": "now()"
        }, on_conflict="user_id, provider").execute()
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        # Return 500 but with detail so frontend can show "Invalid credentials" if we parsed it
        # ideally we catch specific errors like AuthFailure
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/aims/data")
async def get_aims_data(user = Depends(get_current_user)):
    try:
        user_id = user.user.id
        
        # Fetch Grades
        grades = supabase_admin.table("student_grades")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("semester", desc=True)\
            .execute()
            
        # Fetch GPA
        gpa = supabase_admin.table("student_gpa")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("semester", desc=True)\
            .execute()
            
        return {
            "grades": grades.data,
            "gpa": gpa.data
        }
    except Exception as e:
         logger.error(f"Failed to fetch aims data: {e}")
         raise HTTPException(status_code=500, detail="Failed to fetch data")

# Gmail Service Endpoints
from src.brain.services.gmail_service import GmailService

@app.post("/gmail/sync")
async def sync_gmail(background_tasks: BackgroundTasks, days_back: int = 4, user = Depends(get_current_user)):
    """Sync Gmail and fetch important emails."""
    try:
        user_id = user.user.id
        gmail_service = GmailService(supabase_admin)
        
        # Verify the user has valid Gmail tokens before starting sync
        # Use plain list query — .maybe_single() returns 406 when 0 rows exist, crashing on .data
        existing_rows = supabase_admin.table("user_integrations")\
            .select("access_token, refresh_token")\
            .eq("user_id", user_id)\
            .eq("provider", "gmail")\
            .execute()

        if not existing_rows.data:
            raise HTTPException(status_code=400, detail="Gmail not connected. Please connect Google Classroom first to grant Gmail access.")
        
        row = existing_rows.data[0]
        # Allow sync if either token exists — gmail_service will auto-refresh via refresh_token
        if not row.get("access_token") and not row.get("refresh_token"):
            raise HTTPException(status_code=400, detail="No Gmail tokens found. Please reconnect Google Classroom.")
        
        # Update existing row's sync status (only updates, doesn't create new rows)
        supabase_admin.table("user_integrations")\
            .update({"sync_status": "active"})\
            .eq("user_id", user_id)\
            .eq("provider", "gmail")\
            .execute()
        
        # Run sync in background for better UX
        def sync_task():
            try:
                result = gmail_service.fetch_and_store_important_emails(user_id, days_back=days_back)
                logger.info(f"Gmail sync complete for user {user_id}: {result}")
            except Exception as e:
                logger.error(f"Gmail sync failed for user {user_id}: {e}")
        
        background_tasks.add_task(sync_task)
        
        return {"status": "sync_started", "message": f"Gmail sync started for last {days_back} days"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Gmail sync endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gmail/reconnect")
async def reconnect_gmail(user = Depends(get_current_user)):
    """
    Refresh Gmail access token using stored refresh_token.
    Returns needs_oauth=True if there's no refresh_token (user must re-authorize via OAuth).
    """
    try:
        user_id = user.user.id

        # Fetch stored tokens
        rows = supabase_admin.table("user_integrations")\
            .select("refresh_token, expires_at")\
            .eq("user_id", user_id)\
            .eq("provider", "gmail")\
            .execute()

        if not rows.data or not rows.data[0].get("refresh_token"):
            return {"status": "needs_oauth", "message": "No refresh token found. Please reconnect via Google Classroom OAuth."}

        refresh_token = rows.data[0]["refresh_token"]

        # Load client credentials
        with open(CREDENTIALS_FILE, "r") as f:
            cred_data = json.load(f)
        client_config = cred_data.get("web", cred_data.get("installed", {}))
        client_id = client_config["client_id"]
        client_secret = client_config["client_secret"]

        # Exchange refresh_token for a new access_token directly via Google token endpoint
        import httpx as _httpx
        token_response = _httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            }
        )

        if token_response.status_code != 200:
            err = token_response.json()
            logger.error(f"Token refresh failed for user {user_id}: {err}")
            if err.get("error") == "invalid_grant":
                return {"status": "needs_oauth", "message": "Refresh token revoked. Please reconnect via Google Classroom OAuth."}
            raise HTTPException(status_code=502, detail=f"Google token refresh failed: {err.get('error_description', err)}")

        token_data = token_response.json()
        new_access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600)
        new_expiry = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()

        # Persist new access token
        supabase_admin.table("user_integrations").update({
            "access_token": new_access_token,
            "expires_at": new_expiry,
            "sync_status": "active",
        }).eq("user_id", user_id).eq("provider", "gmail").execute()

        logger.info(f"Gmail token refreshed for user {user_id}")
        return {"status": "reconnected", "message": "Gmail access token refreshed successfully."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Gmail reconnect error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/gmail/important")
async def get_important_emails(user = Depends(get_current_user)):
    """Get important emails for the current user."""
    try:
        user_id = user.user.id
        gmail_service = GmailService(supabase_admin)
        emails = gmail_service.get_important_emails(user_id, limit=50)
        
        return {"emails": emails}
    except Exception as e:
        logger.error(f"Failed to fetch important emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("src.server:app", host="0.0.0.0", port=8000, reload=True)

# --- Google Calendar Helper ---
from google.oauth2.credentials import Credentials as GoogleCredentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build as google_build
# Removed conflicting 'import datetime'

def get_gcal_credentials_for_user(user_id: str):
    """Build Google OAuth Credentials from per-user tokens stored in user_integrations."""
    integration = supabase_admin.table("user_integrations")\
        .select("access_token, refresh_token, expires_at, scholr_calendar_id")\
        .eq("user_id", user_id)\
        .eq("provider", "google_calendar")\
        .maybe_single()\
        .execute()
    
    if not integration.data or not integration.data.get("access_token"):
        return None, None
    
    # Load the client_id and client_secret from credentials.json
    with open(CREDENTIALS_FILE, "r") as f:
        cred_data = json.load(f)
    client_config = cred_data.get("web", cred_data.get("installed", {}))
    
    creds = GoogleCredentials(
        token=integration.data["access_token"],
        refresh_token=integration.data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_config["client_id"],
        client_secret=client_config["client_secret"],
    )
    
    # Refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleAuthRequest())
        # Update stored tokens
        supabase_admin.table("user_integrations").update({
            "access_token": creds.token,
            "expires_at": creds.expiry.isoformat() if creds.expiry else None,
        }).eq("user_id", user_id).eq("provider", "google_calendar").execute()
    
    scholr_calendar_id = integration.data.get("scholr_calendar_id")
    return creds, scholr_calendar_id

def get_gcal_service_for_user(user_id: str):
    """Returns (calendar_service, scholr_calendar_id) or (None, None)."""
    creds, scholr_cal_id = get_gcal_credentials_for_user(user_id)
    if not creds:
        return None, None
    service = google_build('calendar', 'v3', credentials=creds)
    return service, scholr_cal_id

# --- Google Calendar OAuth (Separate from Classroom) ---

CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']

@app.get("/auth/google-calendar/authorize")
async def authorize_google_calendar_oauth(request: Request, user_id: str, callback_url: str = None):
    """Initiate OAuth flow for Google Calendar access only."""
    if not os.path.exists(CREDENTIALS_FILE):
        raise HTTPException(status_code=500, detail="Credentials file not found")
    
    base_url = BACKEND_URL.rstrip("/")
    dynamic_redirect_uri = f"{base_url}/auth/google-calendar/callback"
    
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=CALENDAR_SCOPES,
        redirect_uri=dynamic_redirect_uri
    )
    
    if not callback_url:
        callback_url = DEFAULT_FRONTEND_URL
    
    state_payload = json.dumps({"user_id": user_id, "callback_url": callback_url})
    encoded_state = base64.urlsafe_b64encode(state_payload.encode()).decode()
    
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=encoded_state,
        prompt='consent'
    )
    
    return RedirectResponse(authorization_url)

@app.get("/auth/google-calendar/callback")
async def google_calendar_callback(request: Request, code: str, state: str = None):
    """Handle Google Calendar OAuth callback, store tokens, create 'scholr' calendar."""
    try:
        try:
            decoded_state_str = base64.urlsafe_b64decode(state.encode()).decode()
            state_data = json.loads(decoded_state_str)
            user_id = state_data.get("user_id")
            frontend_redirect = state_data.get("callback_url")
        except Exception:
            user_id = state
            frontend_redirect = None

        if not frontend_redirect:
            frontend_redirect = DEFAULT_FRONTEND_URL

        if not user_id:
            logger.error("No user_id in calendar OAuth state")
            return RedirectResponse(f"{frontend_redirect}/dashboard/integrations?status=error_no_user")

        base_url = BACKEND_URL.rstrip("/")
        dynamic_redirect_uri = f"{base_url}/auth/google-calendar/callback"

        flow = Flow.from_client_secrets_file(
            CREDENTIALS_FILE,
            scopes=CALENDAR_SCOPES,
            redirect_uri=dynamic_redirect_uri
        )
        flow.fetch_token(code=code)
        credentials = flow.credentials

        if not credentials.token:
            return RedirectResponse(f"{frontend_redirect}/dashboard/integrations?status=error")

        # Store tokens for Google Calendar
        calendar_payload = {
            "user_id": user_id,
            "provider": "google_calendar",
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
            "sync_status": "active",
        }
        
        # Check if "scholr" calendar already exists for this user
        existing_cal_id = None
        try:
            existing = supabase_admin.table("user_integrations")\
                .select("scholr_calendar_id")\
                .eq("user_id", user_id)\
                .eq("provider", "google_calendar")\
                .maybe_single()\
                .execute()
            if existing and existing.data:
                existing_cal_id = existing.data.get("scholr_calendar_id")
        except Exception:
            pass  # Row doesn't exist yet, that's fine
        
        if not existing_cal_id:
            # Create the "scholr" calendar
            try:
                cal_service = google_build('calendar', 'v3', credentials=credentials)
                new_calendar = cal_service.calendars().insert(body={
                    'summary': 'scholr',
                    'description': 'Tasks and events managed by Student Helper',
                    'timeZone': 'Asia/Kolkata',
                }).execute()
                calendar_payload["scholr_calendar_id"] = new_calendar['id']
                logger.info(f"Created 'scholr' calendar for user {user_id}: {new_calendar['id']}")
            except Exception as cal_e:
                logger.error(f"Failed to create scholr calendar: {cal_e}")
                # Continue without calendar — tokens are still saved
        else:
            calendar_payload["scholr_calendar_id"] = existing_cal_id
        
        supabase_admin.table("user_integrations").upsert(
            calendar_payload, on_conflict="user_id, provider"
        ).execute()
        logger.info(f"Stored Google Calendar tokens for user {user_id}")

        return RedirectResponse(f"{frontend_redirect}/dashboard/integrations?status=success")

    except Exception as e:
        import traceback
        logger.error(f"Google Calendar OAuth callback failed: {e}")
        traceback.print_exc()
        try:
            decoded_state_str = base64.urlsafe_b64decode(state.encode()).decode()
            frontend_redirect = json.loads(decoded_state_str).get(
                "callback_url", DEFAULT_FRONTEND_URL
            )
        except Exception:
            frontend_redirect = DEFAULT_FRONTEND_URL
        from urllib.parse import quote
        error_msg = quote(str(e)[:200])
        return RedirectResponse(f"{frontend_redirect}/dashboard/integrations?status=error&error_detail={error_msg}")


# --- Todo CRUD Endpoints ---

class TodoCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    due_at: Optional[str] = None  # ISO 8601
    priority: str = "medium"
    source: str = "manual"

class TodoUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_at: Optional[str] = None
    is_completed: Optional[bool] = None
    priority: Optional[str] = None

@app.get("/todos")
async def list_todos(
    completed: Optional[bool] = None,
    user = Depends(get_current_user)
):
    """List user's todos, optionally filtered by completion status."""
    try:
        user_id = user.user.id
        query = supabase_admin.table("todos")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)
        
        if completed is not None:
            query = query.eq("is_completed", completed)
        
        data = query.execute()
        return {"todos": data.data}
    except Exception as e:
        logger.error(f"Error listing todos: {e}")
        raise HTTPException(status_code=500, detail="Failed to list todos")

@app.post("/todos")
async def create_todo(request: TodoCreateRequest, user = Depends(get_current_user)):
    """Create a todo and sync to Google Calendar 'scholr' calendar."""
    try:
        user_id = user.user.id
        
        todo_data = {
            "user_id": user_id,
            "title": request.title,
            "description": request.description,
            "due_at": request.due_at,
            "priority": request.priority,
            "source": request.source,
        }
        
        # Try to create GCal event on "scholr" calendar
        gcal_event_id = None
        service, scholr_cal_id = get_gcal_service_for_user(user_id)
        if service and scholr_cal_id and request.due_at:
            try:
                due_dt = datetime.fromisoformat(request.due_at)
                end_dt = due_dt + timedelta(minutes=15)  # Short deadline marker, not a time block
                
                event = {
                    'summary': request.title,
                    'description': request.description or '',
                    'start': {'dateTime': due_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
                    'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
                }
                created_event = service.events().insert(
                    calendarId=scholr_cal_id, body=event
                ).execute()
                gcal_event_id = created_event.get('id')
                logger.info(f"Created GCal event {gcal_event_id} for todo '{request.title}'")
            except Exception as gcal_e:
                logger.error(f"Failed to create GCal event: {gcal_e}")
        
        todo_data["gcal_event_id"] = gcal_event_id
        
        data = supabase_admin.table("todos").insert(todo_data).execute()
        return {"todo": data.data[0]}
    except Exception as e:
        logger.error(f"Error creating todo: {e}")
        raise HTTPException(status_code=500, detail="Failed to create todo")

@app.put("/todos/{todo_id}")
async def update_todo(todo_id: str, request: TodoUpdateRequest, user = Depends(get_current_user)):
    """Update a todo and sync changes to Google Calendar."""
    try:
        user_id = user.user.id
        
        # Verify ownership
        existing = supabase_admin.table("todos")\
            .select("*")\
            .eq("id", todo_id)\
            .eq("user_id", user_id)\
            .maybe_single()\
            .execute()
        
        if not existing.data:
            raise HTTPException(status_code=404, detail="Todo not found")
        
        update_data = {}
        if request.title is not None:
            update_data["title"] = request.title
        if request.description is not None:
            update_data["description"] = request.description
        if request.due_at is not None:
            update_data["due_at"] = request.due_at
        if request.is_completed is not None:
            update_data["is_completed"] = request.is_completed
        if request.priority is not None:
            update_data["priority"] = request.priority
        
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Handle GCal event if it exists
        gcal_event_id = existing.data.get("gcal_event_id")
        if gcal_event_id:
            service, scholr_cal_id = get_gcal_service_for_user(user_id)
            if service and scholr_cal_id:
                try:
                    if request.is_completed:
                        # Delete GCal event when todo is completed
                        service.events().delete(
                            calendarId=scholr_cal_id, eventId=gcal_event_id
                        ).execute()
                        update_data["gcal_event_id"] = None  # Clear the reference
                        logger.info(f"Deleted GCal event {gcal_event_id} (todo completed)")
                    else:
                        # Otherwise update the event details
                        gcal_update = {}
                        if request.title is not None:
                            gcal_update['summary'] = request.title
                        if request.description is not None:
                            gcal_update['description'] = request.description
                        if request.due_at is not None:
                            due_dt = datetime.fromisoformat(request.due_at)
                            end_dt = due_dt + timedelta(minutes=15)
                            gcal_update['start'] = {'dateTime': due_dt.isoformat(), 'timeZone': 'Asia/Kolkata'}
                            gcal_update['end'] = {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Kolkata'}
                        
                        if gcal_update:
                            service.events().patch(
                                calendarId=scholr_cal_id,
                                eventId=gcal_event_id,
                                body=gcal_update
                            ).execute()
                except Exception as gcal_e:
                    logger.error(f"Failed to update/delete GCal event: {gcal_e}")
        
        data = supabase_admin.table("todos")\
            .update(update_data)\
            .eq("id", todo_id)\
            .execute()
        
        return {"todo": data.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating todo: {e}")
        raise HTTPException(status_code=500, detail="Failed to update todo")

@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: str, user = Depends(get_current_user)):
    """Delete a todo and remove its Google Calendar event."""
    try:
        user_id = user.user.id
        
        # Verify ownership and get gcal_event_id
        existing = supabase_admin.table("todos")\
            .select("gcal_event_id")\
            .eq("id", todo_id)\
            .eq("user_id", user_id)\
            .maybe_single()\
            .execute()
        
        if not existing.data:
            raise HTTPException(status_code=404, detail="Todo not found")
        
        # Delete GCal event if it exists
        gcal_event_id = existing.data.get("gcal_event_id")
        if gcal_event_id:
            service, scholr_cal_id = get_gcal_service_for_user(user_id)
            if service and scholr_cal_id:
                try:
                    service.events().delete(
                        calendarId=scholr_cal_id, eventId=gcal_event_id
                    ).execute()
                except Exception as gcal_e:
                    logger.error(f"Failed to delete GCal event: {gcal_e}")
        
        supabase_admin.table("todos")\
            .delete()\
            .eq("id", todo_id)\
            .execute()
        
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting todo: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete todo")
