import os
import hmac
import hashlib
import base64
import json
import time
import secrets
from typing import Optional, Dict, Any
from fastapi import Request, Response, HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from .database import upsert_user, get_user_by_id

# Environment Configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()

# Persistent Secret Key for Session Signing
SECRET_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", ".session_secret")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "")
if not SESSION_SECRET:
    if os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, "r", encoding="utf-8") as f:
            SESSION_SECRET = f.read().strip()
    if not SESSION_SECRET or len(SESSION_SECRET) < 16:
        SESSION_SECRET = secrets.token_hex(32)
        os.makedirs(os.path.dirname(SECRET_FILE), exist_ok=True)
        with open(SECRET_FILE, "w", encoding="utf-8") as f:
            f.write(SESSION_SECRET)

COOKIE_NAME = "speechify_session"
SESSION_DURATION_DAYS = 30

def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def b64url_decode(s: str) -> bytes:
    padding = '=' * (4 - (len(s) % 4)) if (len(s) % 4) != 0 else ''
    return base64.urlsafe_b64decode(s + padding)

def sign_session_payload(payload: Dict[str, Any]) -> str:
    body_json = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    body_b64 = b64url_encode(body_json)
    sig = hmac.new(SESSION_SECRET.encode('utf-8'), body_b64.encode('utf-8'), hashlib.sha256).digest()
    return f"{body_b64}.{b64url_encode(sig)}"

def verify_session_cookie(cookie_value: str) -> Optional[Dict[str, Any]]:
    if not cookie_value or "." not in cookie_value:
        return None
    try:
        body_b64, sig_b64 = cookie_value.split('.', 1)
        expected_sig = hmac.new(SESSION_SECRET.encode('utf-8'), body_b64.encode('utf-8'), hashlib.sha256).digest()
        actual_sig = b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        body_json = b64url_decode(body_b64).decode('utf-8')
        payload = json.loads(body_json)
        
        # Check expiration
        exp = payload.get("exp", 0)
        if exp < time.time():
            return None
        return payload
    except Exception:
        return None

def verify_google_credential(credential: str) -> Dict[str, Any]:
    """
    Verifies a Google OAuth ID Token using Google Auth Library.
    If GOOGLE_CLIENT_ID is not configured, verifies signature directly against Google's public certs.
    """
    if not credential:
        raise HTTPException(status_code=400, detail="Missing Google credential.")

    request_adapter = google_requests.Request()
    try:
        if GOOGLE_CLIENT_ID:
            id_info = id_token.verify_oauth2_token(credential, request_adapter, GOOGLE_CLIENT_ID)
        else:
            # Fallback verification: verifies signature and issuer without audience restriction
            id_info = id_token.verify_oauth2_token(credential, request_adapter)
            
        issuer = id_info.get("iss", "")
        if issuer not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError(f"Invalid token issuer: {issuer}")
            
        sub = id_info.get("sub")
        email = id_info.get("email")
        if not sub or not email:
            raise ValueError("Token missing sub or email.")

        name = id_info.get("name", email.split('@')[0])
        picture = id_info.get("picture", "")

        # Persist / update in database
        user = upsert_user(sub=sub, email=email, name=name, picture=picture)
        return user
    except Exception as e:
        print(f"[Auth Error] Google token verification failed: {e}")
        raise HTTPException(status_code=401, detail=f"Google verification failed: {str(e)}")

def set_auth_cookie(response: Response, user: Dict[str, Any]) -> str:
    """Creates a signed session cookie and sets it on the HTTP response."""
    now = time.time()
    exp = now + (SESSION_DURATION_DAYS * 86400)
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "name": user.get("name", ""),
        "picture": user.get("picture", ""),
        "exp": exp
    }
    token = sign_session_payload(payload)
    is_prod = bool(os.environ.get("RENDER"))
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_DURATION_DAYS * 86400,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        path="/"
    )
    return token

def clear_auth_cookie(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path="/")

def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Extracts current authenticated user from session cookie or Authorization header.
    Returns user dict or None if guest/unauthenticated.
    """
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            cookie = auth_header[7:].strip()

    if not cookie:
        return None

    session = verify_session_cookie(cookie)
    if not session:
        return None

    # Fetch latest user data from DB
    user = get_user_by_id(session["sub"])
    return user if user else session
