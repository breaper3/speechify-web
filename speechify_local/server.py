import os
import io
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, FileResponse, JSONResponse
from pydantic import BaseModel

from .tts_engine import tts_engine
from .document_parser import parse_plain_text, parse_pdf, render_pdf_page_image, PDF_STORE
from .database import (
    save_document,
    get_document,
    list_user_documents,
    update_document_progress,
    delete_document,
    share_document,
    get_shared_document,
    get_pdf_bytes_from_db
)
from .auth import (
    GOOGLE_CLIENT_ID,
    verify_google_credential,
    set_auth_cookie,
    clear_auth_cookie,
    get_current_user
)

app = FastAPI(title="Speechify Cloud API", version="2.0.0")

# Hybrid cloud / local worker environment configuration
DEFAULT_TUNNEL_URL = "https://hist-recorder-rebecca-titten.trycloudflare.com"
LOCAL_WORKER_URL = os.environ.get("LOCAL_WORKER_URL", DEFAULT_TUNNEL_URL if os.environ.get("RENDER") else "").rstrip("/")
WORKER_SECRET_KEY = os.environ.get("WORKER_SECRET_KEY", "")

# Enable CORS for local network and mobile devices
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prevent stale caching of static assets on mobile browsers
@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

executor = ThreadPoolExecutor(max_workers=2)

class TextParseRequest(BaseModel):
    text: str
    title: Optional[str] = "Pasted Text"

class PrewarmRequest(BaseModel):
    sentences: List[str]
    voice: str = "af_heart"
    speed: float = 1.0

class GoogleAuthRequest(BaseModel):
    credential: str

class ProgressUpdateRequest(BaseModel):
    sentence_index: int
    page_num: int = 0
    speed: Optional[float] = None
    voice: Optional[str] = None

# ==================== SYSTEM & HEALTH ENDPOINTS ====================

@app.get("/api/health")
def health_endpoint():
    return {
        "status": "ok",
        "mode": "cloud" if LOCAL_WORKER_URL else "worker",
        "device": tts_engine.device,
        "voices_count": len(tts_engine.voices)
    }

@app.get("/api/node-status")
async def node_status():
    if not LOCAL_WORKER_URL:
        return {"configured": False, "online": True, "mode": "standalone_local", "device": tts_engine.device}
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.5) as client:
            headers = {"X-Worker-Token": WORKER_SECRET_KEY} if WORKER_SECRET_KEY else {}
            res = await client.get(f"{LOCAL_WORKER_URL}/api/health", headers=headers)
            if res.status_code == 200:
                data = res.json()
                return {"configured": True, "online": True, "worker_info": data}
    except Exception as ex:
        return {"configured": True, "online": False, "error": str(ex)}
    return {"configured": True, "online": False}

@app.get("/api/voices")
def get_voices():
    """Returns available local Kokoro and hybrid voices."""
    return {"voices": tts_engine.voices, "device": tts_engine.device}

# ==================== AUTHENTICATION & GOOGLE OAUTH ====================

@app.get("/api/auth/config")
def get_auth_config():
    """Returns Google Client ID and whether sign-in is configured."""
    return {
        "configured": bool(GOOGLE_CLIENT_ID),
        "client_id": GOOGLE_CLIENT_ID
    }

@app.post("/api/auth/google")
def google_auth_endpoint(body: GoogleAuthRequest, response: Response):
    """Verifies Google ID token, logs user in, and sets persistent session cookie."""
    user = verify_google_credential(body.credential)
    token = set_auth_cookie(response, user)
    return {
        "status": "ok",
        "authenticated": True,
        "user": user,
        "token": token
    }

@app.post("/api/auth/logout")
def logout_endpoint(response: Response):
    """Logs out and clears session cookie."""
    clear_auth_cookie(response)
    return {"status": "ok", "authenticated": False}

@app.get("/api/auth/me")
def get_me_endpoint(request: Request):
    """Returns current authenticated user session or guest status."""
    user = get_current_user(request)
    if user:
        return {"authenticated": True, "user": user}
    return {"authenticated": False, "user": None}

# ==================== DOCUMENT LIBRARY & PERSISTENCE ====================

@app.get("/api/documents")
def list_documents_endpoint(request: Request):
    """Lists saved documents for the current user (or guest library)."""
    current_user = get_current_user(request)
    user_id = current_user["id"] if current_user else None
    docs = list_user_documents(user_id=user_id)
    return {"documents": docs, "user_id": user_id}

@app.get("/api/documents/{doc_id}")
def get_document_endpoint(doc_id: str, request: Request):
    """Loads complete parsed document and restores reading progress."""
    current_user = get_current_user(request)
    user_id = current_user["id"] if current_user else None
    doc_record = get_document(doc_id, user_id=user_id)
    if not doc_record:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Warm PDF cache in memory if needed
    if doc_record.get("is_pdf") and doc_id not in PDF_STORE:
        pdf_bytes = get_pdf_bytes_from_db(doc_id)
        if pdf_bytes:
            PDF_STORE[doc_id] = pdf_bytes

    doc_data = doc_record["doc_data"]
    doc_data["current_sentence_index"] = doc_record.get("current_sentence_index", 0)
    doc_data["current_page"] = doc_record.get("current_page", 0)
    doc_data["speed"] = doc_record.get("speed", 1.0)
    doc_data["voice"] = doc_record.get("voice", "af_heart")
    doc_data["is_shared"] = bool(doc_record.get("is_shared", 0))
    doc_data["share_id"] = doc_record.get("share_id")
    return doc_data

@app.post("/api/documents/{doc_id}/progress")
def update_progress_endpoint(doc_id: str, req: ProgressUpdateRequest, request: Request):
    """Updates active reading position (sentence index and page)."""
    current_user = get_current_user(request)
    user_id = current_user["id"] if current_user else None
    ok = update_document_progress(
        doc_id=doc_id,
        sentence_index=req.sentence_index,
        page_num=req.page_num,
        speed=req.speed,
        voice=req.voice,
        user_id=user_id
    )
    return {"status": "ok", "updated": ok}

@app.delete("/api/documents/{doc_id}")
def delete_document_endpoint(doc_id: str, request: Request):
    """Deletes a document from the user's library."""
    current_user = get_current_user(request)
    user_id = current_user["id"] if current_user else None
    ok = delete_document(doc_id, user_id=user_id)
    return {"status": "ok", "deleted": ok}

@app.post("/api/documents/{doc_id}/share")
def share_document_endpoint(doc_id: str, request: Request):
    """Generates a shareable token and URL for a document."""
    current_user = get_current_user(request)
    user_id = current_user["id"] if current_user else None
    share_id = share_document(doc_id, user_id=user_id)
    if not share_id:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    base_url = str(request.base_url).rstrip("/")
    return {
        "status": "ok",
        "share_id": share_id,
        "share_url": f"{base_url}/?share={share_id}"
    }

@app.get("/api/shared/{share_id}")
def get_shared_doc_endpoint(share_id: str):
    """Retrieves document data for anyone opening a share link."""
    doc_record = get_shared_document(share_id)
    if not doc_record:
        raise HTTPException(status_code=404, detail="Shared document not found or expired.")
        
    doc_id = doc_record["doc_id"]
    if doc_record.get("is_pdf") and doc_id not in PDF_STORE:
        pdf_bytes = get_pdf_bytes_from_db(doc_id)
        if pdf_bytes:
            PDF_STORE[doc_id] = pdf_bytes

    doc_data = doc_record["doc_data"]
    doc_data["is_shared_view"] = True
    doc_data["share_id"] = share_id
    return doc_data

# ==================== PARSING & INGESTION ====================

@app.post("/api/parse-text")
def parse_text_endpoint(req: TextParseRequest, request: Request):
    """Parses raw text into paragraphs and sentences, and auto-saves to library."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    
    current_user = get_current_user(request)
    user_id = current_user["id"] if current_user else None

    parsed = parse_plain_text(req.text, title=req.title or "Pasted Document")
    save_document(
        doc_id=parsed["doc_id"],
        title=parsed["title"],
        filename="pasted_text.txt",
        is_pdf=False,
        total_sentences=parsed["total_sentences"],
        total_words=parsed["total_words"],
        est_minutes=parsed["est_minutes"],
        doc_data=parsed,
        user_id=user_id
    )
    return parsed

@app.post("/api/parse-file")
async def parse_file_endpoint(file: UploadFile = File(...), request: Request = None):
    """Upload, parse PDF or TXT, and automatically save to user's library."""
    filename = file.filename or "uploaded_file"
    contents = await file.read()
    
    current_user = get_current_user(request) if request else None
    user_id = current_user["id"] if current_user else None
    
    if filename.lower().endswith(".pdf"):
        try:
            parsed = parse_pdf(contents, filename=filename)
            save_document(
                doc_id=parsed["doc_id"],
                title=parsed["title"],
                filename=filename,
                is_pdf=True,
                total_sentences=parsed["total_sentences"],
                total_words=parsed["total_words"],
                est_minutes=parsed["est_minutes"],
                doc_data=parsed,
                user_id=user_id,
                pdf_bytes=contents
            )
            return parsed
        except Exception as e:
            print(f"[PDF Parse Error] {e}")
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")
    else:
        try:
            text = contents.decode("utf-8")
        except UnicodeDecodeError:
            text = contents.decode("latin-1", errors="ignore")
        parsed = parse_plain_text(text, title=filename.rsplit('.', 1)[0].replace('_', ' ').title())
        save_document(
            doc_id=parsed["doc_id"],
            title=parsed["title"],
            filename=filename,
            is_pdf=False,
            total_sentences=parsed["total_sentences"],
            total_words=parsed["total_words"],
            est_minutes=parsed["est_minutes"],
            doc_data=parsed,
            user_id=user_id
        )
        return parsed

@app.get("/api/pdf-page/{doc_id}/{page_num}")
def get_pdf_page(doc_id: str, page_num: int, dpi: int = 130):
    """
    Renders a specific page of an uploaded PDF as a high-performance JPEG image.
    Cached on disk, database, and browser for instant sub-millisecond retrieval.
    """
    try:
        jpg_bytes = render_pdf_page_image(doc_id, page_num, dpi=dpi)
        return Response(
            content=jpg_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=604800, immutable"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except IndexError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sample-pdf")
def get_sample_pdf(request: Request):
    """Loads, saves, and parses the sample PDF."""
    sample_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_speechify.pdf")
    if not os.path.exists(sample_path):
        from .create_sample_pdf import create_sample_pdf
        create_sample_pdf(sample_path)
        
    with open(sample_path, "rb") as f:
        pdf_bytes = f.read()
        
    current_user = get_current_user(request)
    user_id = current_user["id"] if current_user else None

    parsed = parse_pdf(pdf_bytes, filename="Speechify_Local_Research_Paper.pdf")
    save_document(
        doc_id=parsed["doc_id"],
        title=parsed["title"],
        filename="Speechify_Local_Research_Paper.pdf",
        is_pdf=True,
        total_sentences=parsed["total_sentences"],
        total_words=parsed["total_words"],
        est_minutes=parsed["est_minutes"],
        doc_data=parsed,
        user_id=user_id,
        pdf_bytes=pdf_bytes
    )
    return parsed

# ==================== TEXT TO SPEECH ====================

@app.get("/api/tts")
async def tts_stream(
    request: Request,
    text: str = Query(..., description="Sentence or phrase to synthesize"),
    voice: str = Query("af_heart", description="Voice ID"),
    speed: float = Query(1.0, ge=0.5, le=2.0, description="Synthesis base speed")
):
    """
    Synthesize text into WAV audio stream with memory caching,
    secure worker authentication, and transparent cloud-to-worker proxying.
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text parameter cannot be empty.")
    
    # 1. Security token check when this instance runs as a worker node
    if WORKER_SECRET_KEY and not LOCAL_WORKER_URL:
        req_token = request.headers.get("X-Worker-Token") or request.query_params.get("token")
        if req_token != WORKER_SECRET_KEY:
            raise HTTPException(status_code=403, detail="Unauthorized worker access.")

    # 2. Proxy to local GPU worker if running in cloud mode and requesting non-cloud voice
    is_cloud_native = voice.startswith("edge:")
    if LOCAL_WORKER_URL and not is_cloud_native:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"X-Worker-Token": WORKER_SECRET_KEY} if WORKER_SECRET_KEY else {}
                url = f"{LOCAL_WORKER_URL}/api/tts"
                params = {"text": text, "voice": voice, "speed": speed}
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code == 200:
                    return Response(content=resp.content, media_type="audio/wav")
        except Exception as proxy_err:
            print(f"[Proxy Warning] GPU worker unreachable ({proxy_err}), using cloud fallback voice")
            fallback_voice = "edge:en-US-GuyNeural" if any(k in voice for k in ["adam", "michael", "george", "jordan", "beast"]) else "edge:en-US-JennyNeural"
            wav_bytes = tts_engine.synthesize(text, voice_id=fallback_voice, speed=speed)
            return Response(content=wav_bytes, media_type="audio/wav")

    # 3. Direct synthesis
    try:
        wav_bytes = tts_engine.synthesize(text, voice_id=voice, speed=speed)
        return Response(content=wav_bytes, media_type="audio/wav")
    except Exception as e:
        print(f"[TTS Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/prewarm")
def prewarm_sentences(req: PrewarmRequest, background_tasks: BackgroundTasks):
    """
    Background pre-synthesis of upcoming sentences to ensure 0ms gap during playback.
    """
    def _run_prewarm():
        for s in req.sentences[:3]:
            if s and s.strip():
                try:
                    tts_engine.synthesize(s, voice_id=req.voice, speed=req.speed)
                except Exception as e:
                    print(f"[Prewarm Error] {e}")

    background_tasks.add_task(_run_prewarm)
    return {"status": "prewarming", "count": min(len(req.sentences), 3)}

# Serve static frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"status": "Server running", "message": "static/index.html not found yet."})
