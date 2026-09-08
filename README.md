# DocuMind AI — Multimodal Document Studio & RAG Assistant

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Abhishikth24i/documind-ai)

A multimodal RAG (Retrieval-Augmented Generation) document intelligence studio. Upload PDFs, documents, or images, extract diagrams, and ask natural-language questions grounded in your content.

- **Retrieval:** Sentence Transformers embeddings (`all-MiniLM-L6-v2`) + FAISS
  for semantic search over document chunks. Always free, always runs on the
  server itself.
- **Generation:** three interchangeable providers, set with one env var:
  - **Groq (recommended for a public deployment)** — free hosted API, works
    from any server, no GPU needed.
  - **Ollama (recommended for local development)** — runs entirely on your
    own machine, free, but only reachable by that one machine.
  - **Anthropic API** — optional, paid, if you'd rather use Claude.
- **Backend:** FastAPI. **Frontend:** one static HTML page, served by the
  same backend — the whole app is a single deployable service.
- **Multi-user:** each visitor gets a random session ID (stored in their
  browser), so uploaded documents are private to that visitor.

## Run it locally

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Defaults to Ollama. Install it from https://ollama.com, then:

```bash
ollama pull llama3.2
```

Start the server:

```bash
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** in your browser — the backend now serves the
frontend directly, so there's nothing else to run.

## Put it on GitHub

```bash
cd documind-ai
git init
git add .
git commit -m "Initial commit: DocuMind AI"
git branch -M main
git remote add origin https://github.com/<your-username>/documind-ai.git
git push -u origin main
```

(Create the empty repo on GitHub first, at github.com/new — don't initialize
it with a README there, since this project already has one.)

`.env` is gitignored on purpose — never commit real API keys.

## Deploy it as a live website (free)

This uses [Render](https://render.com)'s free web service tier and
[Groq](https://console.groq.com)'s free LLM API — no cost to you or to
anyone who visits the site.

1. **Get a free Groq API key** at https://console.groq.com/keys (sign up,
   click "Create API key").
2. **Push this repo to GitHub** (see above) — Render deploys from a GitHub
   repo.
3. **On Render:** New → Blueprint → connect your GitHub repo. Render reads
   `render.yaml` in this repo automatically and sets everything up.
4. When prompted, **paste your Groq key** into the `GROQ_API_KEY` field.
5. Click deploy. After the build finishes (a few minutes — it installs
   Sentence Transformers and downloads the embedding model on first boot),
   Render gives you a public URL like `https://documind-ai.onrender.com`.
   Anyone can open it and use it immediately, no setup on their end.

**Good to know about the free tier:**
- Render's free web services spin down after 15 minutes of no traffic, and
  take ~30–60 seconds to wake back up on the next visit. Fine for a portfolio
  project; upgrade to a paid instance if you need it always-on.
- Documents live in memory and reset whenever the service restarts or
  redeploys (e.g. on the free tier's idle spin-down). For a project meant to
  hold documents long-term, swap the in-memory store in `rag_engine.py` for a
  real database (e.g. Postgres + pgvector — Render, Supabase, and Neon all
  have free Postgres tiers).
- Groq's free tier has rate limits shared across everyone who uses your
  deployed site. Fine for demo/portfolio traffic; watch console.groq.com for
  usage if it gets popular.
- `MAX_DOCS_PER_SESSION` (default 10) caps how many documents one visitor can
  upload, to keep any single visitor from using up all the server's memory.

## How it works

```
Upload → extract text → chunk (800 chars, 100 overlap)
       → embed each chunk (Sentence Transformers)
       → store in a per-session, per-document FAISS index

Ask    → embed the question
       → retrieve top-k most similar chunks (cosine similarity via FAISS)
       → send question + chunks to the configured LLM (Groq / Ollama / Claude)
       → return grounded answer + source chunk scores
```

Every request carries an `X-Session-Id` header (a random ID the browser
generates once and stores in `localStorage`), which is how the backend keeps
different visitors' documents separate without needing a login system.

## Project structure

```
documind-ai/
├── backend/
│   ├── main.py          FastAPI app: routes, LLM providers, serves frontend
│   ├── rag_engine.py     chunking, embeddings, FAISS retrieval
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── index.html        upload + chat UI, no build step
├── render.yaml            one-click Render deployment config
└── LICENSE
```

## Next steps / ideas

- Swap in-memory storage for Postgres + pgvector so documents persist across
  restarts.
- Add authentication if you want documents tied to real user accounts instead
  of anonymous per-browser sessions.
- Support more file types (`.docx`, `.epub`) by extending `extract_text()` in
  `rag_engine.py`.
- Add a "delete all my documents" button and a session expiry/cleanup job so
  old sessions don't accumulate in memory forever.
