"""
main.py
DocuMind AI backend — upload a document, ask questions grounded in its content.

Serves both the API and the static frontend from one process, so the whole
app deploys as a single service.

Run locally with:
    uvicorn main:app --reload --port 8000
"""

import os

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import rag_engine

load_dotenv()

# LLM_PROVIDER chooses how answers get generated:
#   "groq"      -> FREE hosted LLM API, works from any server (recommended for
#                  a public deployment). Sign up at https://console.groq.com
#   "ollama"    -> free, but runs on ONE machine — fine for local use, not for
#                  a public website visitors reach over the internet.
#   "anthropic" -> paid Claude API, needs ANTHROPIC_API_KEY.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

_anthropic_client = None
if LLM_PROVIDER == "anthropic" and ANTHROPIC_API_KEY:
    import anthropic
    _anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

app = FastAPI(title="DocuMind AI", description="RAG-powered document Q&A assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    doc_id: str
    question: str
    history: list[ChatMessage] = []
    image_url: str | None = None



def _require_session(x_session_id: str | None) -> str:
    if not x_session_id:
        raise HTTPException(status_code=400, detail="Missing X-Session-Id header.")
    return x_session_id


def _llm_ready() -> bool:
    if LLM_PROVIDER == "anthropic":
        return _anthropic_client is not None
    if LLM_PROVIDER == "groq":
        return GROQ_API_KEY is not None
    return True


@app.get("/health")
def health():
    return {"status": "ok", "llm_provider": LLM_PROVIDER, "llm_configured": _llm_ready()}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...), x_session_id: str | None = Header(None)):
    session_id = _require_session(x_session_id)
    file_bytes = await file.read()
    try:
        result = rag_engine.ingest_document(session_id, file.filename, file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    return result


@app.get("/documents")
def get_documents(x_session_id: str | None = Header(None)):
    session_id = _require_session(x_session_id)
    return rag_engine.list_documents(session_id)


@app.delete("/documents/{doc_id}")
def remove_document(doc_id: str, x_session_id: str | None = Header(None)):
    session_id = _require_session(x_session_id)
    rag_engine.delete_document(session_id, doc_id)
    return {"deleted": doc_id}


@app.get("/documents/{doc_id}/images")
def get_document_images(doc_id: str, x_session_id: str | None = Header(None)):
    session_id = _require_session(x_session_id)
    return rag_engine.get_document_images(session_id, doc_id)



def _generate_with_ollama(messages: list[dict]) -> str:
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
            },
            timeout=120,
        )
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=500,
            detail=(
                "Couldn't reach Ollama at " + OLLAMA_BASE_URL + ". Install it from "
                "https://ollama.com, then run `ollama pull " + OLLAMA_MODEL + "` "
                "and make sure `ollama serve` is running."
            ),
        )
    if resp.status_code == 404:
        raise HTTPException(
            status_code=500,
            detail=f"Model '{OLLAMA_MODEL}' not found in Ollama. Run: ollama pull {OLLAMA_MODEL}",
        )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def _generate_with_groq(messages: list[dict], image_url: str | None = None) -> str:
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is not set. Add it to .env or environment variables.",
        )
    
    # If an image is attached, use the multimodal vision model
    model = "qwen/qwen3.8-27b" if image_url else GROQ_MODEL
    
    payload_messages = []
    for m in messages:
        if image_url and m == messages[-1] and m.get("role") == "user":
            payload_messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": m["content"]},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            })
        else:
            payload_messages.append(m)

    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={
            "model": model,
            "messages": payload_messages,
            "max_tokens": 2048,
            "temperature": 0.35,
        },
        timeout=60,
    )
    if resp.status_code == 401:
        raise HTTPException(status_code=500, detail="Groq rejected the API key — check GROQ_API_KEY.")
    if resp.status_code != 200:
        err_msg = resp.text
        try:
            err_msg = resp.json().get("error", {}).get("message", resp.text)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Groq API error ({resp.status_code}): {err_msg}")
    return resp.json()["choices"][0]["message"]["content"]


def _generate_with_anthropic(system_prompt: str, messages: list[dict]) -> str:
    if _anthropic_client is None:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY is not set. Add it to .env and restart the server.",
        )
    # Anthropic expects user/assistant messages list and system prompt separately
    user_msgs = [m for m in messages if m["role"] in ("user", "assistant")]
    response = _anthropic_client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1200,
        system=system_prompt,
        messages=user_msgs,
    )
    return "".join(block.text for block in response.content if block.type == "text")


@app.post("/ask")
def ask_question(req: AskRequest, x_session_id: str | None = Header(None)):
    session_id = _require_session(x_session_id)
    matches = []
    if req.doc_id and req.doc_id != "new":
        try:
            matches = rag_engine.retrieve(session_id, req.doc_id, req.question)
        except KeyError:
            raise HTTPException(status_code=404, detail="Document not found in this session. Please re-upload it.")

    if matches:
        context = "\n\n---\n\n".join(m["text"] for m in matches)
        system_content = (
            "You are DocuMind AI, an exceptionally perceptive, articulate, and thoughtful research assistant, document architect, and writing partner.\n\n"
            "Persona & Communication Style:\n"
            "1. Human-Like Intellectual Warmth: Speak naturally, engagingly, and directly — like Claude 3.5 Sonnet or an insightful senior colleague. Avoid robotic boilerplate, repetitive disclaimers, or stiff robotic phrases.\n"
            "2. Multimodal & Visual Fluency: Understand and discuss diagrams, charts, schemas, figures, and images thoroughly. When analyzing visual figures or uploaded images, identify key metrics, axes, trends, and takeaways accurately.\n"
            "3. Document Q&A: Ground answers in the document context while offering thoughtful synthesis, comparative analysis, and practical implications.\n"
            "4. Document Editing & PDF Formatting: If the user asks to edit, polish, write, rewrite, or format a document, provide complete, beautifully formatted Markdown under a clear section (e.g., '### ✍️ Document'). Include well-structured headings, bullet lists, or tables so it is ready for instant PDF export.\n"
            "5. Proactive Guidance: When appropriate, offer natural follow-up angles, creative suggestions, or helpful next steps to assist the user."
            f"\n\n=== RELEVANT DOCUMENT EXCERPTS & VISUAL CONTEXT ===\n{context}\n================================="
        )
    else:
        system_content = (
            "You are DocuMind AI, an expert document creator, professional writer, and document architect.\n\n"
            "Persona & Communication Style:\n"
            "1. Human-Grade Eloquence: Speak with conversational warmth, clarity, and precision. You are collaborating closely with the user to build publication-grade materials.\n"
            "2. Multimodal Mastery: If the user provides or describes an image, diagram, or chart, incorporate those visual details directly into the document structure.\n"
            "3. Comprehensive & Complete: Create publication-ready documents with elegant Markdown headings, organized sub-sections, executive summaries, bullet points, or tables.\n"
            "4. PDF-Ready: Ensure the generated text is thorough, formatted cleanly, and ready to be downloaded as a PDF."
        )

    # Build multi-turn chat message payload
    system_message = {
        "role": "system",
        "content": system_content
    }
    
    chat_payload = [system_message]
    # Add recent chat history for conversational memory
    for prev in req.history[-8:]:
        if prev.role in ("user", "assistant") and prev.content:
            chat_payload.append({"role": prev.role, "content": prev.content})

    # Add current question
    chat_payload.append({"role": "user", "content": req.question})

    if LLM_PROVIDER == "anthropic":
        answer_text = _generate_with_anthropic(system_message["content"], chat_payload)
    elif LLM_PROVIDER == "groq":
        answer_text = _generate_with_groq(chat_payload, image_url=req.image_url)
    else:
        answer_text = _generate_with_ollama(chat_payload)

    return {
        "answer": answer_text,
        "sources": matches,
    }



# --- Serve the frontend from the same service (so one deploy = whole app) ---
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/google-signin")
    def serve_google_signin():
        return FileResponse(os.path.join(FRONTEND_DIR, "google-signin.html"))

