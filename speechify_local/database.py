import os
import sqlite3
import json
import time
import secrets
from typing import Optional, List, Dict, Any

# Locate database in persistent project data directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "speechify.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode and foreign keys for high performance
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    """Initializes tables for users, documents, and PDF binaries."""
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            picture TEXT,
            created_at INTEGER NOT NULL,
            last_login INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            is_pdf INTEGER NOT NULL DEFAULT 0,
            total_sentences INTEGER NOT NULL DEFAULT 0,
            total_words INTEGER NOT NULL DEFAULT 0,
            est_minutes REAL NOT NULL DEFAULT 0.0,
            current_sentence_index INTEGER NOT NULL DEFAULT 0,
            current_page INTEGER NOT NULL DEFAULT 0,
            speed REAL NOT NULL DEFAULT 1.0,
            voice TEXT NOT NULL DEFAULT 'af_heart',
            last_read_at INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            is_shared INTEGER NOT NULL DEFAULT 0,
            share_id TEXT UNIQUE,
            doc_data TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS pdf_blobs (
            doc_id TEXT PRIMARY KEY,
            user_id TEXT,
            pdf_bytes BLOB NOT NULL,
            FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_docs_user ON documents(user_id, last_read_at DESC);
        CREATE INDEX IF NOT EXISTS idx_docs_share ON documents(share_id);
        """)
        conn.commit()

# Initialize tables immediately on module import
init_db()

def upsert_user(sub: str, email: str, name: str, picture: str) -> Dict[str, Any]:
    """Inserts or updates a user from Google authentication."""
    now_ms = int(time.time() * 1000)
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO users (id, email, name, picture, created_at, last_login)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                email = excluded.email,
                name = excluded.name,
                picture = excluded.picture,
                last_login = excluded.last_login
        """, (sub, email, name, picture, now_ms, now_ms))
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (sub,)).fetchone()
        return dict(row) if row else {"id": sub, "email": email, "name": name, "picture": picture}

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

def save_document(
    doc_id: str,
    title: str,
    filename: str,
    is_pdf: bool,
    total_sentences: int,
    total_words: int,
    est_minutes: float,
    doc_data: Dict[str, Any],
    user_id: Optional[str] = None,
    pdf_bytes: Optional[bytes] = None,
    current_sentence_index: int = 0,
    current_page: int = 0,
    speed: float = 1.0,
    voice: str = "af_heart"
) -> Dict[str, Any]:
    """Persists a parsed document, its metadata, and raw PDF bytes."""
    now_ms = int(time.time() * 1000)
    doc_json = json.dumps(doc_data)

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO documents (
                doc_id, user_id, title, filename, is_pdf, total_sentences,
                total_words, est_minutes, current_sentence_index, current_page,
                speed, voice, last_read_at, created_at, is_shared, share_id, doc_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?)
            ON CONFLICT(doc_id) DO UPDATE SET
                title = excluded.title,
                user_id = COALESCE(excluded.user_id, documents.user_id),
                total_sentences = excluded.total_sentences,
                total_words = excluded.total_words,
                est_minutes = excluded.est_minutes,
                doc_data = excluded.doc_data,
                last_read_at = excluded.last_read_at
        """, (
            doc_id, user_id, title, filename, 1 if is_pdf else 0,
            total_sentences, total_words, est_minutes,
            current_sentence_index, current_page, speed, voice,
            now_ms, now_ms, doc_json
        ))

        if is_pdf and pdf_bytes:
            conn.execute("""
                INSERT INTO pdf_blobs (doc_id, user_id, pdf_bytes)
                VALUES (?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    pdf_bytes = excluded.pdf_bytes,
                    user_id = COALESCE(excluded.user_id, pdf_blobs.user_id)
            """, (doc_id, user_id, pdf_bytes))

        conn.commit()

    return {
        "doc_id": doc_id,
        "title": title,
        "filename": filename,
        "is_pdf": is_pdf,
        "total_sentences": total_sentences,
        "total_words": total_words,
        "est_minutes": est_minutes,
        "current_sentence_index": current_sentence_index,
        "current_page": current_page,
        "speed": speed,
        "voice": voice,
        "last_read_at": now_ms
    }

def get_document(doc_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves full document record including parsed data."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["doc_data"] = json.loads(d["doc_data"])
        return d

def get_pdf_bytes_from_db(doc_id: str) -> Optional[bytes]:
    """Retrieves original PDF file bytes from the database."""
    with get_connection() as conn:
        row = conn.execute("SELECT pdf_bytes FROM pdf_blobs WHERE doc_id = ?", (doc_id,)).fetchone()
        return bytes(row["pdf_bytes"]) if row else None

def list_user_documents(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns library listing with reading progress and stats without heavy body text."""
    with get_connection() as conn:
        if user_id:
            rows = conn.execute("""
                SELECT doc_id, user_id, title, filename, is_pdf, total_sentences,
                       total_words, est_minutes, current_sentence_index, current_page,
                       speed, voice, last_read_at, created_at, is_shared, share_id
                FROM documents
                WHERE user_id = ?
                ORDER BY last_read_at DESC
            """, (user_id,)).fetchall()
        else:
            # Anonymous / guest listing (documents without user assignment)
            rows = conn.execute("""
                SELECT doc_id, user_id, title, filename, is_pdf, total_sentences,
                       total_words, est_minutes, current_sentence_index, current_page,
                       speed, voice, last_read_at, created_at, is_shared, share_id
                FROM documents
                ORDER BY last_read_at DESC
                LIMIT 50
            """).fetchall()

        return [dict(r) for r in rows]

def update_document_progress(
    doc_id: str,
    sentence_index: int,
    page_num: int = 0,
    speed: Optional[float] = None,
    voice: Optional[str] = None,
    user_id: Optional[str] = None
) -> bool:
    """Updates reading position and timestamp."""
    now_ms = int(time.time() * 1000)
    with get_connection() as conn:
        params: List[Any] = [sentence_index, page_num, now_ms]
        sets = ["current_sentence_index = ?", "current_page = ?", "last_read_at = ?"]

        if speed is not None:
            sets.append("speed = ?")
            params.append(speed)
        if voice is not None:
            sets.append("voice = ?")
            params.append(voice)

        params.append(doc_id)
        where_clause = "WHERE doc_id = ?"
        if user_id:
            where_clause += " AND (user_id = ? OR user_id IS NULL)"
            params.append(user_id)

        sql = f"UPDATE documents SET {', '.join(sets)} {where_clause}"
        cur = conn.execute(sql, tuple(params))
        conn.commit()
        return cur.rowcount > 0

def delete_document(doc_id: str, user_id: Optional[str] = None) -> bool:
    """Deletes document and associated PDF blob."""
    with get_connection() as conn:
        if user_id:
            cur = conn.execute("DELETE FROM documents WHERE doc_id = ? AND (user_id = ? OR user_id IS NULL)", (doc_id, user_id))
        else:
            cur = conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        conn.commit()
        return cur.rowcount > 0

def share_document(doc_id: str, user_id: Optional[str] = None) -> Optional[str]:
    """Generates a unique share_id for public / shared access."""
    with get_connection() as conn:
        row = conn.execute("SELECT share_id FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
        if not row:
            return None
        if row["share_id"]:
            return row["share_id"]

        new_share_id = secrets.token_urlsafe(12)
        conn.execute("UPDATE documents SET is_shared = 1, share_id = ? WHERE doc_id = ?", (new_share_id, doc_id))
        conn.commit()
        return new_share_id

def get_shared_document(share_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves document data for a valid share_id."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM documents WHERE share_id = ?", (share_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["doc_data"] = json.loads(d["doc_data"])
        return d
