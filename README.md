# SIGNAL — AI-Based Security Chat Assistant

A defensive assistant that explains security alerts and logs using
Retrieval-Augmented Generation (RAG), grounded in a local knowledge base,
with input/output validation and full audit logging of every exchange.

## Architecture

```
Browser (frontend/)
      │  fetch()
      ▼
FastAPI backend (backend/app)
      │
      ├── validation.py     → input guardrails (prompt injection / offensive intent)
      ├── rag/vector_store   → ChromaDB similarity search over sample_data/
      ├── rag/embeddings     → sentence-transformers (local, free)
      ├── llm_client.py      → grounded prompt → Anthropic/OpenAI API
      ├── validation.py     → output guardrails + grounding check
      └── audit_logger.py    → writes every turn to SQLite (audit_logs table)
```

Every chat turn: **validate input → retrieve context → generate grounded
answer → validate output → log to audit trail → return with citations.**

## Stack & why

| Layer       | Choice                          | Why |
|-------------|----------------------------------|-----|
| Backend     | FastAPI                         | Async, auto-generated docs at `/docs`, minimal boilerplate |
| Embeddings  | sentence-transformers (local)   | Free, no API cost per chunk, no data leaves the machine to embed |
| Vector DB   | ChromaDB (persistent, embedded) | No server to host, persists to disk, trivial setup |
| Audit DB    | SQLite via SQLAlchemy           | Zero-config; swap to Postgres later by changing one connection string |
| LLM         | Anthropic Claude API (default)  | Strong instruction-following for "refuse/say-you-don't-know" grounding behavior |
| Frontend    | Plain HTML/CSS/JS               | No build step; keeps focus on the RAG pipeline |

## 1. Setup

### Prerequisites
- Python 3.11+
- An Anthropic API key (or OpenAI key, if you switch providers)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env and paste in your ANTHROPIC_API_KEY
```

Ingest the sample knowledge base into the vector DB (run this once, and
again any time you edit files in `sample_data/`):

```bash
python -m app.rag.ingest
```

Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

Visit **http://localhost:8000/docs** to see interactive API docs and try
the `/chat` endpoint directly.

### Frontend

No build step needed — just serve the static folder:

```bash
cd frontend
python -m http.server 5500
```

Open **http://localhost:5500** in your browser. If your backend runs on a
different host/port, update `API_BASE` at the top of `frontend/app.js`.

### Or: run everything with Docker

```bash
docker compose up --build
```

Backend → `http://localhost:8000`, frontend → `http://localhost:5500`.
(Set your API key in `backend/.env` before running this — compose reads it
via `env_file`.)

## 2. Using it

Ask things like:
- "What does Event ID 4625 mean?"
- "Explain this alert" + paste one of the entries from `sample_data/sample_alerts.json` into the "+ attach log/alert" field
- "What's the difference between severity and confidence?"

The assistant will only answer from what's in `sample_data/` (plus
whatever log/alert you paste in) and will say so explicitly if it doesn't
have enough context — it won't invent explanations for indicators it
hasn't seen.

Try also asking it to "write a script to exploit this vulnerability" —
you'll see the input-validation guardrail catch it and log the attempt
as flagged, rather than reaching the LLM.

## 3. Viewing the audit trail

Every chat turn is logged to `backend/audit.db` (SQLite) with the question,
retrieved sources, answer, latency, and any validation flags.

```bash
curl -H "X-Admin-Key: change-me-admin-key" http://localhost:8000/audit/logs
curl -H "X-Admin-Key: change-me-admin-key" http://localhost:8000/audit/logs/flagged
```

(Change `ADMIN_API_KEY` in `.env` before this ever leaves your laptop.)

## 4. Extending it

- **Add more knowledge**: drop `.md`/`.txt`/`.json` files into
  `backend/sample_data/` and re-run `python -m app.rag.ingest`.
- **Swap the LLM provider**: set `LLM_PROVIDER=openai` in `.env` and add
  `openai` to `requirements.txt` (already wired up in `llm_client.py`).
- **Swap SQLite for Postgres**: change the connection string in
  `app/database.py`; SQLAlchemy models don't need to change.
- **Real auth**: replace the `X-Admin-Key` header check in
  `app/routers/audit.py` with your actual auth (OAuth, session cookies,
  SSO) before this touches real data.

## 5. Project layout

```
security-chat-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, router registration
│   │   ├── config.py          # env-based settings
│   │   ├── database.py        # SQLAlchemy engine/session
│   │   ├── models.py          # AuditLog ORM model
│   │   ├── schemas.py         # Pydantic request/response models
│   │   ├── llm_client.py      # system prompt + grounded generation
│   │   ├── validation.py      # input/output guardrails, grounding check
│   │   ├── audit_logger.py    # writes audit_logs rows
│   │   ├── rag/
│   │   │   ├── embeddings.py  # sentence-transformers wrapper
│   │   │   ├── vector_store.py# ChromaDB wrapper
│   │   │   └── ingest.py      # chunk + embed sample_data/
│   │   └── routers/
│   │       ├── chat.py        # POST /chat
│   │       └── audit.py       # GET /audit/logs (protected)
│   ├── sample_data/            # knowledge base the RAG pipeline retrieves from
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── docker-compose.yml
└── README.md
```
