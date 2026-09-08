"""
rag_engine.py
Core Retrieval-Augmented Generation logic for DocuMind AI.

Responsibilities:
- Extract text from uploaded documents (PDF / TXT)
- Chunk text into overlapping windows
- Embed chunks with Sentence Transformers
- Store / search chunks per-document using FAISS (in-memory, per-process)
"""

import io
import os
import uuid
from dataclasses import dataclass, field

import faiss
import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 800))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 100))
TOP_K = int(os.getenv("TOP_K", 4))

# Loaded once at import time; reused for every request.
_embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)


import base64
import zipfile
import xml.etree.ElementTree as ET
import requests
from PIL import Image

@dataclass
class DocumentStore:
    """Holds the chunks + FAISS index + extracted images for a single uploaded document."""
    doc_id: str
    filename: str
    chunks: list[str] = field(default_factory=list)
    index: faiss.Index | None = None
    images: list[dict] = field(default_factory=list)


# In-memory registry of all uploaded documents, keyed by session_id -> doc_id.
# Each visitor to the site gets their own session_id (generated client-side),
# so one person's uploads are never visible to another person.
# NOTE: this resets whenever the server restarts. Swap for a real DB /
# persistent vector store (e.g. pgvector) if you need documents to survive
# restarts or deploys.
_SESSIONS: dict[str, dict[str, DocumentStore]] = {}

# Simple cap so one visitor can't exhaust server memory on a public deployment.
MAX_DOCS_PER_SESSION = int(os.getenv("MAX_DOCS_PER_SESSION", 10))


def _session_docs(session_id: str) -> dict[str, DocumentStore]:
    return _SESSIONS.setdefault(session_id, {})


def describe_image_with_vision(data_url: str, prompt: str = "Provide a thorough description and transcription of any diagrams, charts, numbers, formulas, or text shown in this image.") -> str:
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        return "Embedded visual diagram or image in document."
    try:
        payload = {
            "model": "qwen/qwen3.8-27b",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}}
                    ]
                }
            ],
            "max_tokens": 400,
            "temperature": 0.2
        }
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_api_key}"},
            json=payload,
            timeout=25
        )
        if res.status_code == 200:
            content = res.json()["choices"][0]["message"]["content"].strip()
            if content:
                return content
    except Exception as e:
        print(f"[Vision Error] {e}")
    return "Embedded visual diagram or image in document."


def extract_images_from_pdf(file_bytes: bytes, max_images: int = 6) -> list[dict]:
    """Extract embedded images from PDF pages and return standardized data URIs with vision descriptions."""
    images = []
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        for page_idx, page in enumerate(reader.pages):
            if len(images) >= max_images:
                break
            try:
                for img_idx, img_obj in enumerate(page.images):
                    if len(images) >= max_images:
                        break
                    raw_data = img_obj.data
                    try:
                        pil_img = Image.open(io.BytesIO(raw_data))
                        if pil_img.width < 50 or pil_img.height < 50:
                            continue
                        
                        max_dim = 1024
                        if pil_img.width > max_dim or pil_img.height > max_dim:
                            pil_img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                        
                        if pil_img.mode in ("RGBA", "P"):
                            pil_img = pil_img.convert("RGB")
                        
                        out_buf = io.BytesIO()
                        pil_img.save(out_buf, format="JPEG", quality=85)
                        out_buf.seek(0)
                        b64_str = base64.b64encode(out_buf.read()).decode("utf-8")
                        data_url = f"data:image/jpeg;base64,{b64_str}"
                        
                        img_id = f"img_p{page_idx+1}_{img_idx+1}"
                        img_name = img_obj.name or f"Figure {len(images)+1}"
                        
                        desc = describe_image_with_vision(
                            data_url,
                            f"Describe what is shown in this document diagram/image ({img_name} on Page {page_idx+1}). Include any key numbers, chart trends, labels, or text."
                        )
                        
                        images.append({
                            "id": img_id,
                            "name": img_name,
                            "page": page_idx + 1,
                            "width": pil_img.width,
                            "height": pil_img.height,
                            "data_url": data_url,
                            "description": desc
                        })
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception as e:
        print(f"[PDF Image Extraction Error] {e}")
    return images


def extract_text(filename: str, file_bytes: bytes) -> str:
    """Extract raw text from uploaded PDF, DOCX, or plain text files."""
    lower = filename.lower()
    
    # PDF files
    if lower.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            pages_text = []
            for i, page in enumerate(reader.pages):
                try:
                    txt = page.extract_text()
                    if txt:
                        pages_text.append(txt.strip())
                except Exception:
                    continue
            full_text = "\n\n".join(pages_text).strip()
            return full_text
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Could not read PDF '{filename}': {str(e)}")

    # Image files (PNG, JPG, JPEG, WEBP, BMP)
    image_extensions = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
    if lower.endswith(image_extensions):
        try:
            pil_img = Image.open(io.BytesIO(file_bytes))
            if pil_img.mode in ("RGBA", "P"):
                pil_img = pil_img.convert("RGB")
            max_dim = 1024
            if pil_img.width > max_dim or pil_img.height > max_dim:
                pil_img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            out_buf = io.BytesIO()
            pil_img.save(out_buf, format="JPEG", quality=85)
            b64_str = base64.b64encode(out_buf.getvalue()).decode("utf-8")
            data_url = f"data:image/jpeg;base64,{b64_str}"
            desc = describe_image_with_vision(
                data_url,
                "Transcribe all visible text, numbers, formulas, and describe all charts, diagrams, tables, and visual components in this image comprehensively."
            )
            return f"### Visual Document: {filename}\n\n{desc}"
        except Exception as e:
            raise ValueError(f"Could not process image '{filename}': {str(e)}")

    # DOCX files (Word documents)
    if lower.endswith(".docx"):
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx_zip:
                xml_content = docx_zip.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                paragraphs = []
                for p in tree.iterfind(".//w:p", namespaces):
                    texts = [node.text for node in p.iterfind(".//w:t", namespaces) if node.text]
                    if texts:
                        paragraphs.append("".join(texts))
                full_text = "\n\n".join(paragraphs).strip()
                if not full_text:
                    raise ValueError(f"Document '{filename}' appears to be empty.")
                return full_text
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Could not read Word document '{filename}': {str(e)}")

    # Plain text and code formats
    text_extensions = (
        ".txt", ".md", ".csv", ".json", ".tsv", ".log",
        ".xml", ".html", ".htm", ".py", ".js", ".css", ".sql", ".yaml", ".yml"
    )
    if lower.endswith(text_extensions) or "." not in filename:
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return file_bytes.decode("latin-1")
            except Exception as e:
                raise ValueError(f"Unable to decode text file '{filename}': {str(e)}")

    raise ValueError(
        f"Unsupported file type for '{filename}'. Supported: PDF, DOCX, Images (PNG, JPG, WEBP), TXT, MD, CSV, JSON."
    )


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping character-based chunks while preserving readability."""
    text = " ".join(text.split())  # normalize whitespace
    if not text:
        return []

    chunks = []
    start = 0
    total_len = len(text)
    while start < total_len:
        end = min(start + chunk_size, total_len)
        chunk = text[start:end]
        chunks.append(chunk)
        if end >= total_len:
            break
        start += max(1, chunk_size - overlap)
    return chunks


def _embed(texts: list[str]) -> np.ndarray:
    vectors = _embedder.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return vectors.astype("float32")


def ingest_document(session_id: str, filename: str, file_bytes: bytes) -> dict:
    """Extract, chunk, embed, and index a new document for one visitor's session."""
    docs = _session_docs(session_id)
    if len(docs) >= MAX_DOCS_PER_SESSION:
        raise ValueError(
            f"Limit of {MAX_DOCS_PER_SESSION} documents per session reached. "
            "Remove one before uploading another."
        )

    lower = filename.lower()
    images = []
    if lower.endswith(".pdf"):
        images = extract_images_from_pdf(file_bytes)
    elif lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
        try:
            pil_img = Image.open(io.BytesIO(file_bytes))
            if pil_img.mode in ("RGBA", "P"):
                pil_img = pil_img.convert("RGB")
            out_buf = io.BytesIO()
            pil_img.save(out_buf, format="JPEG", quality=85)
            b64_str = base64.b64encode(out_buf.getvalue()).decode("utf-8")
            data_url = f"data:image/jpeg;base64,{b64_str}"
            desc = describe_image_with_vision(data_url, "Transcribe all visible text, numbers, formulas, and describe all charts, diagrams, tables, and visual components in this image comprehensively.")
            images.append({
                "id": "img_upload_1",
                "name": filename,
                "page": 1,
                "width": pil_img.width,
                "height": pil_img.height,
                "data_url": data_url,
                "description": desc
            })
        except Exception:
            pass

    text = extract_text(filename, file_bytes)

    # If text is empty but we have extracted images (e.g. scanned PDF)
    if not text and images:
        text_parts = []
        for img in images:
            if img.get("description"):
                text_parts.append(f"### [Visual Diagram / Image on Page {img['page']}]:\n{img['description']}")
        text = "\n\n".join(text_parts)

    if not text and not images:
        raise ValueError(f"No extractable text or visual elements found in '{filename}'.")

    chunks = chunk_text(text) if text else []

    # Also add image descriptions to chunks so FAISS matches visual questions
    for img in images:
        desc = img.get("description")
        if desc and len(desc) > 20:
            chunks.append(f"[Visual Figure on Page {img['page']} ({img['name']})]: {desc}")

    if not chunks:
        chunks = [text or "Visual document uploaded without plain text."]

    vectors = _embed(chunks)
    dimension = vectors.shape[1]

    # Inner product on normalized vectors == cosine similarity.
    index = faiss.IndexFlatIP(dimension)
    index.add(vectors)

    doc_id = str(uuid.uuid4())
    docs[doc_id] = DocumentStore(doc_id=doc_id, filename=filename, chunks=chunks, index=index, images=images)

    return {
        "doc_id": doc_id,
        "filename": filename,
        "chunk_count": len(chunks),
        "total_chars": len(text),
        "images": images
    }


def list_documents(session_id: str) -> list[dict]:
    return [
        {
            "doc_id": d.doc_id,
            "filename": d.filename,
            "chunk_count": len(d.chunks),
            "image_count": len(d.images),
        }
        for d in _session_docs(session_id).values()
    ]


def get_document_images(session_id: str, doc_id: str) -> list[dict]:
    store = _session_docs(session_id).get(doc_id)
    if not store:
        return []
    return store.images


def delete_document(session_id: str, doc_id: str) -> None:
    _session_docs(session_id).pop(doc_id, None)


def retrieve(session_id: str, doc_id: str, query: str, k: int = TOP_K) -> list[dict]:
    """Return the most relevant chunks for a query, with similarity scores."""
    store = _session_docs(session_id).get(doc_id)
    if store is None:
        raise KeyError(f"Unknown doc_id: {doc_id}")

    total_chunks = len(store.chunks)
    if total_chunks == 0:
        return []

    # If document is small (<= 6 chunks), return all chunks so context is complete
    if total_chunks <= 6:
        return [{"text": chunk, "score": 1.0} for chunk in store.chunks]

    query_vector = _embed([query])
    k = min(k, total_chunks)
    scores, indices = store.index.search(query_vector, k)

    results = []
    seen_indices = set()
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1 or idx in seen_indices:
            continue
        seen_indices.add(idx)
        results.append({"text": store.chunks[idx], "score": float(score)})

    # If query is asking for summary or overview, make sure beginning of document is included
    query_lower = query.lower()
    summary_keywords = ("summar", "overview", "what is this", "about", "outline", "key point", "tldr")
    if any(kw in query_lower for kw in summary_keywords):
        for idx in range(min(2, total_chunks)):
            if idx not in seen_indices:
                seen_indices.add(idx)
                results.insert(0, {"text": store.chunks[idx], "score": 0.85})

    return results

