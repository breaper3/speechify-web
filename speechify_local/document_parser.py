import os
import re
import io
import hashlib
import tempfile
import fitz  # PyMuPDF
from typing import List, Dict, Any, Tuple, Optional

# Persistent on-disk cache directory for PDF files and rendered pages
CACHE_DIR = os.path.join(tempfile.gettempdir(), "speechify_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# In-memory store fallback: doc_id -> bytes
PDF_STORE: Dict[str, bytes] = {}

COMMON_ABBREVIATIONS = {
    'mr.', 'mrs.', 'ms.', 'dr.', 'prof.', 'sr.', 'jr.', 'vs.', 'etc.', 
    'e.g.', 'i.e.', 'inc.', 'ltd.', 'corp.', 'u.s.', 'u.k.', 'jan.', 
    'feb.', 'mar.', 'apr.', 'aug.', 'sept.', 'oct.', 'nov.', 'dec.',
    'no.', 'vol.', 'dept.', 'est.', 'approx.', 'al.'
}

def clean_text(text: str) -> str:
    """Normalize text and strip stray control characters."""
    if not text:
        return ""
    text = text.replace('—', ' - ').replace('–', ' - ')
    text = text.replace('“', '"').replace('”', '"').replace('’', "'").replace('‘', "'")
    text = text.replace('\xa0', ' ')
    return re.sub(r'[ \t]+', ' ', text).strip()

def split_into_sentences(text: str) -> List[str]:
    """
    Splits text into clean sentences, handling abbreviations and numerical figures.
    """
    text = clean_text(text)
    if not text:
        return []
        
    words = text.split()
    processed_words = []
    
    for word in words:
        lower_word = word.lower().rstrip(',:;"\'')
        if lower_word in COMMON_ABBREVIATIONS:
            processed_words.append(word.replace('.', '___DOT___'))
        else:
            if re.match(r'^\$?\d+\.\d+%?$', word):
                processed_words.append(word.replace('.', '___DOT___'))
            else:
                processed_words.append(word)
                
    joined = ' '.join(processed_words)
    raw_sentences = re.split(r'(?<=[.!?؟۔])\s+(?=[A-Z0-9"\'\(\[\u0600-\u06FF])', joined)
    
    final_sentences = []
    for s in raw_sentences:
        restored = s.replace('___DOT___', '.').strip()
        if restored:
            final_sentences.append(restored)
            
    return final_sentences if final_sentences else [text]

def parse_plain_text(raw_text: str, title: str = "Document") -> Dict[str, Any]:
    """
    Parses plain text into structured paragraphs and sentences.
    """
    paragraphs_raw = [p.strip() for p in re.split(r'\n\s*\n', raw_text) if p.strip()]
    if not paragraphs_raw:
        paragraphs_raw = [raw_text.strip()]
        
    sentences_list: List[Dict[str, Any]] = []
    paragraphs_data: List[Dict[str, Any]] = []
    sentence_counter = 0
    total_words = 0
    
    for p_idx, p_text in enumerate(paragraphs_raw):
        p_sentences = split_into_sentences(p_text)
        p_sentence_ids = []
        
        for s_text in p_sentences:
            words_in_s = len(s_text.split())
            total_words += words_in_s
            s_obj = {
                "id": sentence_counter,
                "paragraph_idx": p_idx,
                "page_num": 0,
                "text": s_text,
                "word_count": words_in_s,
                "rects": []
            }
            sentences_list.append(s_obj)
            p_sentence_ids.append(sentence_counter)
            sentence_counter += 1
            
        paragraphs_data.append({
            "idx": p_idx,
            "sentence_ids": p_sentence_ids
        })
        
    est_minutes = round(total_words / 150.0, 1)
    
    return {
        "doc_id": "txt_" + hashlib.md5(raw_text.encode('utf-8')).hexdigest()[:8],
        "is_pdf": False,
        "title": title,
        "total_sentences": len(sentences_list),
        "total_words": total_words,
        "est_minutes": est_minutes,
        "sentences": sentences_list,
        "paragraphs": paragraphs_data,
        "pages": []
    }

def get_pdf_bytes(doc_id: str) -> bytes:
    """Retrieve PDF bytes from memory or disk cache."""
    if doc_id in PDF_STORE:
        return PDF_STORE[doc_id]
        
    disk_path = os.path.join(CACHE_DIR, f"{doc_id}.pdf")
    if os.path.exists(disk_path):
        with open(disk_path, "rb") as f:
            data = f.read()
            PDF_STORE[doc_id] = data
            return data
            
    raise ValueError(f"Document {doc_id} not found in memory or disk cache.")

def parse_pdf(file_bytes: bytes, filename: str = "document.pdf") -> Dict[str, Any]:
    """
    High-speed, single-pass PDF parser with exact visual bounding box alignment.
    Saves document persistently to disk cache to prevent loss during server lifecycle.
    """
    doc_id = "pdf_" + hashlib.md5(file_bytes).hexdigest()[:12]
    
    # Persist raw PDF to disk cache
    disk_path = os.path.join(CACHE_DIR, f"{doc_id}.pdf")
    if not os.path.exists(disk_path):
        with open(disk_path, "wb") as f:
            f.write(file_bytes)
    PDF_STORE[doc_id] = file_bytes
    
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    doc_title = filename.rsplit('.', 1)[0].replace('_', ' ').title()
    meta_title = doc.metadata.get("title") if doc.metadata else None
    if meta_title and len(meta_title.strip()) > 2:
        doc_title = meta_title.strip()
        
    pages_data = []
    all_sentences: List[Dict[str, Any]] = []
    paragraphs_data: List[Dict[str, Any]] = []
    sentence_counter = 0
    paragraph_counter = 0
    total_words = 0

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        p_width = page.rect.width
        p_height = page.rect.height
        aspect_ratio = round(p_height / p_width, 4) if p_width > 0 else 1.414

        # Fast single-pass word and block extraction
        blocks = page.get_text("blocks")
        page_words = page.get_text("words")  # (x0, y0, x1, y1, word, block_no, line_no, word_no)
        
        # Index words by block_no
        block_words_map: Dict[int, list] = {}
        for w in page_words:
            b_idx = w[5]
            if b_idx not in block_words_map:
                block_words_map[b_idx] = []
            block_words_map[b_idx].append(w)

        page_sentence_ids = []

        for b in blocks:
            b_text = b[4]
            b_idx = b[5]
            if not b_text.strip():
                continue
                
            # Filter standard numeric page footers
            if re.match(r'^\s*page\s*\d+\s*(of\s*\d+)?\s*$', b_text, re.IGNORECASE) or re.match(r'^\s*\d+\s*$', b_text):
                continue

            # Clean line-wraps inside block
            fixed_text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', b_text)
            fixed_text = re.sub(r'(?<!\n)\n(?!\n)', ' ', fixed_text)

            p_sentences = split_into_sentences(fixed_text)
            p_sentence_ids = []
            
            b_words = block_words_map.get(b_idx, [])
            w_pointer = 0

            for s_text in p_sentences:
                w_count = len(s_text.split())
                total_words += w_count
                
                # Fast single-pass line bounding calculation
                rects = []
                if b_words and w_pointer < len(b_words):
                    matched_words = b_words[w_pointer : w_pointer + w_count]
                    w_pointer += w_count
                    
                    if matched_words:
                        line_rects: Dict[int, list] = {}
                        for mw in matched_words:
                            line_no = mw[6]
                            if line_no not in line_rects:
                                line_rects[line_no] = [mw[0], mw[1], mw[2], mw[3]]
                            else:
                                line_rects[line_no][0] = min(line_rects[line_no][0], mw[0])
                                line_rects[line_no][1] = min(line_rects[line_no][1], mw[1])
                                line_rects[line_no][2] = max(line_rects[line_no][2], mw[2])
                                line_rects[line_no][3] = max(line_rects[line_no][3], mw[3])
                                
                        for lr in line_rects.values():
                            rx = round((lr[0] / p_width) * 100, 2)
                            ry = round((lr[1] / p_height) * 100, 2)
                            rw = round(((lr[2] - lr[0]) / p_width) * 100, 2)
                            rh = round(((lr[3] - lr[1]) / p_height) * 100, 2)
                            rects.append({
                                "x": max(0.0, min(100.0, rx)),
                                "y": max(0.0, min(100.0, ry)),
                                "w": max(0.5, min(100.0 - rx, rw)),
                                "h": max(0.5, min(100.0 - ry, rh))
                            })

                s_obj = {
                    "id": sentence_counter,
                    "paragraph_idx": paragraph_counter,
                    "page_num": page_idx,
                    "text": s_text,
                    "word_count": w_count,
                    "rects": rects
                }
                all_sentences.append(s_obj)
                p_sentence_ids.append(sentence_counter)
                page_sentence_ids.append(sentence_counter)
                sentence_counter += 1

            if p_sentence_ids:
                paragraphs_data.append({
                    "idx": paragraph_counter,
                    "page_num": page_idx,
                    "sentence_ids": p_sentence_ids
                })
                paragraph_counter += 1

        pages_data.append({
            "page_num": page_idx,
            "width": round(p_width, 1),
            "height": round(p_height, 1),
            "aspect_ratio": aspect_ratio,
            "sentence_ids": page_sentence_ids
        })

    doc.close()
    est_minutes = round(total_words / 150.0, 1)

    return {
        "doc_id": doc_id,
        "is_pdf": True,
        "title": doc_title,
        "total_pages": len(pages_data),
        "total_sentences": len(all_sentences),
        "total_words": total_words,
        "est_minutes": est_minutes,
        "pages": pages_data,
        "sentences": all_sentences,
        "paragraphs": paragraphs_data
    }

def render_pdf_page_image(doc_id: str, page_num: int, dpi: int = 130) -> bytes:
    """
    Renders a specific page of a PDF as high-performance JPEG bytes.
    Caches rendered pages directly on disk for instant sub-millisecond retrieval.
    """
    cached_img_path = os.path.join(CACHE_DIR, f"{doc_id}_p{page_num}_{dpi}.jpg")
    if os.path.exists(cached_img_path):
        with open(cached_img_path, "rb") as f:
            return f.read()

    # Load PDF from memory or disk cache
    pdf_bytes = get_pdf_bytes(doc_id)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    if page_num < 0 or page_num >= len(doc):
        doc.close()
        raise IndexError(f"Page number {page_num} out of bounds (0..{len(doc)-1}).")
        
    page = doc[page_num]
    pix = page.get_pixmap(dpi=dpi)
    # JPEG quality 85 produces sharp text while reducing RAM and file size by 80%
    jpg_bytes = pix.tobytes("jpeg", jpg_quality=85)
    doc.close()

    # Save to disk cache for subsequent requests
    try:
        with open(cached_img_path, "wb") as f:
            f.write(jpg_bytes)
    except Exception:
        pass

    return jpg_bytes
