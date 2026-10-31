import re
import io
import hashlib
import fitz  # PyMuPDF
from typing import List, Dict, Any, Tuple, Optional

# In-memory store for active PDF documents: doc_id -> bytes
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
    # Normalize em-dashes and en-dashes to hyphens or colons
    text = text.replace('—', ' - ').replace('–', ' - ')
    # Normalize quotation marks
    text = text.replace('“', '"').replace('”', '"').replace('’', "'").replace('‘', "'")
    # Replace non-breaking spaces
    text = text.replace('\xa0', ' ')
    # Normalize multiple whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def split_into_sentences(text: str) -> List[str]:
    """
    Splits a paragraph into distinct sentences, handling abbreviations and numbers.
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
    Parses plain text into paragraphs and sentences.
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

def find_sentence_rects(page: fitz.Page, sentence: str) -> List[fitz.Rect]:
    """
    Locates the visual bounding boxes for a sentence on a PDF page.
    Handles exact matches, hyphenated text, and multi-line wrapping.
    """
    # 1. Exact search
    clean_s = sentence.strip()
    rects = page.search_for(clean_s)
    if rects:
        return rects
        
    # 2. Search without punctuation
    no_punct = re.sub(r'[^\w\s]', '', clean_s)
    if len(no_punct) > 5:
        rects = page.search_for(no_punct)
        if rects:
            return rects

    # 3. Search by sub-chunks (prefix, middle, suffix)
    words = clean_s.split()
    collected_rects = []
    if len(words) >= 4:
        # Search first 4 words
        prefix = ' '.join(words[:4])
        r1 = page.search_for(prefix)
        if r1:
            collected_rects.extend(r1)
        # Search last 4 words
        suffix = ' '.join(words[-4:])
        r2 = page.search_for(suffix)
        if r2:
            collected_rects.extend(r2)

    return collected_rects

def parse_pdf(file_bytes: bytes, filename: str = "document.pdf") -> Dict[str, Any]:
    """
    Parses a PDF into structured pages, images, and coordinate-aligned sentences.
    Preserves exact visual geometry for Speechify-style overlay highlighting.
    """
    doc_id = "pdf_" + hashlib.md5(file_bytes).hexdigest()[:10]
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

        # Extract text blocks
        blocks = page.get_text("blocks")
        page_sentence_ids = []
        
        for b in blocks:
            b_text = b[4] # Block text
            if not b_text.strip():
                continue
            # Filter obvious single-number page footers
            if re.match(r'^\s*page\s*\d+\s*(of\s*\d+)?\s*$', b_text, re.IGNORECASE) or re.match(r'^\s*\d+\s*$', b_text):
                continue

            # Clean line-wraps inside block
            fixed_text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', b_text)
            fixed_text = re.sub(r'(?<!\n)\n(?!\n)', ' ', fixed_text)

            p_sentences = split_into_sentences(fixed_text)
            p_sentence_ids = []

            for s_text in p_sentences:
                w_count = len(s_text.split())
                total_words += w_count
                
                # Locate bounding rects on this page
                fitz_rects = find_sentence_rects(page, s_text)
                
                # Normalize rects into percentage coordinates (0% to 100%)
                norm_rects = []
                for fr in fitz_rects:
                    rx = round((fr.x0 / p_width) * 100, 2)
                    ry = round((fr.y0 / p_height) * 100, 2)
                    rw = round(((fr.x1 - fr.x0) / p_width) * 100, 2)
                    rh = round(((fr.y1 - fr.y0) / p_height) * 100, 2)
                    # Clamp values
                    rx = max(0.0, min(100.0, rx))
                    ry = max(0.0, min(100.0, ry))
                    rw = max(0.5, min(100.0 - rx, rw))
                    rh = max(0.5, min(100.0 - ry, rh))
                    norm_rects.append({"x": rx, "y": ry, "w": rw, "h": rh})

                s_obj = {
                    "id": sentence_counter,
                    "paragraph_idx": paragraph_counter,
                    "page_num": page_idx,
                    "text": s_text,
                    "word_count": w_count,
                    "rects": norm_rects
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

    est_minutes = round(total_words / 150.0, 1)

    return {
        "doc_id": doc_id,
        "is_pdf": True,
        "title": doc_title,
        "total_pages": len(doc),
        "total_sentences": len(all_sentences),
        "total_words": total_words,
        "est_minutes": est_minutes,
        "pages": pages_data,
        "sentences": all_sentences,
        "paragraphs": paragraphs_data
    }

def render_pdf_page_image(doc_id: str, page_num: int, dpi: int = 150) -> bytes:
    """
    Renders a specific page of a PDF document as high-resolution PNG bytes.
    """
    if doc_id not in PDF_STORE:
        raise ValueError(f"Document {doc_id} not found in memory store.")
        
    doc = fitz.open(stream=PDF_STORE[doc_id], filetype="pdf")
    if page_num < 0 or page_num >= len(doc):
        doc.close()
        raise IndexError(f"Page number {page_num} out of bounds (0..{len(doc)-1}).")
        
    page = doc[page_num]
    pix = page.get_pixmap(dpi=dpi)
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes
