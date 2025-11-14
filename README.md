# Cerberus AI

Advanced PDF analysis, Chat, and Cybersecurity Intelligence in one full‑stack app. Cerberus AI combines a FastAPI backend with a React + Nginx frontend and offers background PDF processing (with OCR), a research pipeline for threat intelligence, an investigation tool, local file querying, a chatbot, and scheduled email reporting.

Screenshot: `frontend/src/assets/screenshot.png`

## Features

- PDF Professor: extract text or OCR scanned PDFs, process in background, track status, and view results.
- AI Servers: manage Ollama and Gemini servers and pick models dynamically from the UI.
- Research Pipeline: draft-first pipeline with scoring, AU bias, API-free discovery (RSS/Sitemaps/Crawling) or search API mode; finalize to a structured Markdown report.
- Investigations: quick AI-driven investigations for incidents or companies.
- Chatbot: simple conversation UI with selected model and server.
- Local Storage: upload PDFs to a local area, batch OCR + query with a prompt, and save job history.
- Email Scheduler: configure SMTP, recipient groups, and scheduled research jobs with delivery logs.
- Admin Cache Tools: list domains, inspect entries, refetch or clear discovery cache.
- Dockerized: one-command deployment with Nginx proxying `/api` to the backend.

## Architecture

- Frontend: React (Vite) built to static assets served by Nginx; Nginx proxies `/api/*` to the backend.
- Backend: FastAPI + Uvicorn; async IO via `httpx`; persistence via SQLite (async `aiosqlite`).
- OCR + PDF: PyMuPDF for text extraction; Tesseract OCR fallback for scanned PDFs.
- LLMs: Ollama (local) via REST; Gemini via Google Generative AI. Research pipeline uses LangChain wrappers.
- Discovery: API-free mode via RSS, sitemaps, and domain crawling (with politeness, caching, TTLs); or SERPAPI/Tavily when enabled.
- Scheduling: in-process scheduler loop executes configured research jobs and emails results.

Repository layout (high level):

```
backend/        FastAPI app, research pipeline, DB, scheduler
frontend/       React app and Nginx config (Dockerized)
docker-compose.yml   Orchestrates frontend + backend containers
```

## Quick Start (Docker Compose)

1) Create a `.env` in repo root for optional search/LLM keys (used by backend):

```
SERPAPI_API_KEY=your-serpapi-key
TAVILY_API_KEY=your-tavily-key
OPENROUTER_API_KEY=your-openrouter-key
```

2) (Recommended) Persist the DB by setting the database path in `backend/config.json`:

```
"database_file": "database/tasks.db"
```

3) Build and start:

```
docker-compose up -d --build
```

4) Open the app: http://localhost:3500

- Frontend: Nginx on port 3500
- Backend: FastAPI exposed on port 8001 (container port 8000)

To stop and remove containers (keep data): `docker-compose down`
To also remove volumes (delete data): `docker-compose down -v`

## Configuration

`backend/config.json` controls core behavior. Key fields:

- Paths and IO
  - `pdf_directory`: where uploads are stored for background PDF processing
  - `output_directory`: output artifacts (if used)
  - `log_directory`: backend logs directory
  - `database_file`: SQLite file path (set to `database/tasks.db` to use the compose volume)
- Processing
  - `chunk_size`: size of text chunks for LLM processing
  - `tesseract_path`: optional override path to Tesseract (Docker image installs it by default)
  - `llm.num_predict`: token/character budget for Ollama requests
  - `concurrency.llm_max_inflight`: semaphore for concurrent LLM calls
  - `extraction.timeout_s`: timeout when extracting fields during research
- CORS
  - `cors_origins`: list of allowed origins (useful for local dev without Nginx)
- Discovery and Search
  - `use_search_apis`: if true, allows SERPAPI/Tavily; otherwise API‑free mode
  - `discovery`: API‑free settings (recency, crawl depth, rate limits, cache TTL, keywords)
  - `sources`: curated RSS feeds, sitemap domains, and domain allowlist
- Research Pipeline
  - `research_pipeline.page_size`, `max_candidates`, `min_score`, `concurrency`
  - `filters`: e.g., `require_incident`, `require_au`, `aggregator_keywords`
  - `scheduler.jitter_seconds_max`: jitter before scheduled job runs

Environment variables (read by backend):

- `SERPAPI_API_KEY`: enables Google SERPAPI search
- `TAVILY_API_KEY`: enables Tavily search fallback
- `OPENROUTER_API_KEY`: optional for select LangChain backends

## Usage (UI Walkthrough)

First, configure at least one AI server:

1) Open “Manage AI Servers” in the UI.
2) Add an Ollama server: provide a name and the base URL (for example, `http://localhost:11434`). The backend appends `/api/generate` as needed.
3) Or add a Gemini server: provide a name and the Gemini API key.
4) You can add multiple servers and switch models per operation.

PDF Professor

- Upload one or multiple PDFs and provide a prompt.
- Choose server type (Ollama/Gemini), server name, and model.
- Background jobs appear in “Task Status”. Click a task to view the processed result.

Threats and Risks Research

- Enter a research query, optionally including a date range (e.g., “from 2025-01-01 to 2025-01-31”).
- Configure target count and advanced settings in Research Settings if needed.
- Start a job and monitor drafts and logs in real time; finalize to produce a single Markdown report.

Investigations

- Provide a short description of an incident or organization to investigate.
- Results return as an AI-curated summary with references where available.

Chatbot

- Open the Chat view, pick a server and model, and start chatting.

Local Storage

- Upload PDFs to local storage.
- Select files and submit a prompt; Cerberus OCRs each file, concatenates content, and processes with the chosen model.
- Review job results and history from the Local Storage pages.

Email Scheduler

- Add an Email Config (SMTP server, port, credentials, TLS/SSL options, sender info).
- Create Recipient Groups and add Recipients.
- Add a Scheduled Research job: choose frequency (daily/weekly/monthly), time, window (e.g., last 7 days), server/model, and recipient group.
- Monitor delivery status in Email Delivery Logs.

## API (Selected Endpoints)

Prefix: the frontend calls the backend under `/api/*` via Nginx. The backend defines these routes (subset):

- PDFs: `POST /process-pdfs/`, `POST /pdfprofessor`, `GET /status`, `GET /status/{task_id}`, `DELETE /task/{task_id}`
- Research jobs: `POST /research/jobs/start`, `GET /research/jobs/{job_id}`, `GET /research/jobs/{job_id}/drafts`, `GET /research/jobs/{job_id}/events`, `POST /research/jobs/{job_id}/finalize`, `POST /research`
- AI servers: `GET/POST/DELETE /ollama-servers`, `GET /ollama-models?url=…`, `GET/POST/DELETE /external-ai-servers`, `GET /external-ai/models?server_type=…`
- Research history: `GET /research`, `GET /research/{id}`, `DELETE /research/{id}`
- Investigate: `POST /investigate`
- Local storage: `GET /local-storage/files`, `POST /local-storage/upload`, `DELETE /local-storage/files/{filename}`, `GET /local-storage/files/{filename}`, `POST /local-storage/query`, `GET /local-storage/status/{job_id}`, `GET /local-storage/jobs`, `DELETE /local-storage/jobs/{job_id}`
- Chat: `POST /chat`
- Email scheduler: `POST /email-config`, `GET/PUT/DELETE /email-configs/{id}`, `GET /email-configs`
- Recipient groups: `POST/GET /email-recipient-groups`, `GET/PUT/DELETE /email-recipient-groups/{id}`
- Recipients: `POST /email-recipients`, `GET /email-recipients/{group_id}`, `GET/PUT/DELETE /email-recipients/{recipient_id}`
- Scheduled research: `POST/GET /scheduled-research`, `GET /scheduled-research/{id}`, `PUT/DELETE /scheduled-research/{id}`
- Email logs and tests: `GET /email-delivery-logs`, `POST /test-email`, `POST /test-scheduled-research`
- Cache admin: `GET /cache/domains`, `GET/DELETE /cache`, `POST /cache/refetch`, `POST /cache/refetch-domain`

OpenAPI docs are available at `/docs` on the backend (container port 8000; mapped to host 8001 when using compose).

## Development (without Docker)

Backend (Python 3.11)

```
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# optional: edit backend/config.json (set database_file, CORS origins for dev)
uvicorn main:app --reload --port 8000
```

Frontend (Node 20)

```
cd frontend
npm install
npm run dev
```

Note: The dev frontend uses `API_BASE_URL = "/api"`. In production Nginx proxies `/api` to the backend. For local dev without Docker, set up a Vite proxy to `http://localhost:8000` or run the frontend behind Nginx. Alternatively, adjust the base URL temporarily for local testing.

## Data & Persistence

- Uploaded PDFs: `uploaded_pdfs` (mounted as a volume in Docker)
- Logs: `logs` (volume)
- SQLite DB: set `database_file` to `database/tasks.db` so it resides in the `database` directory (volume). This preserves data across container restarts.

## Deployment Notes

- Reverse proxy: The provided Nginx config in the frontend image serves static assets and proxies `/api` to the `backend` service. It includes SSE‑friendly settings and raised timeouts for long jobs.
- OCR: The backend Docker image installs Tesseract. For bare‑metal runs, install Tesseract manually.
- CORS: When front and back are on different origins in dev, add your frontend origin to `config.json` under `cors_origins`.
- Resources: The research pipeline performs network fetches, OCR, and LLM calls. Consider memory/CPU limits on constrained hosts.

## Security

- SMTP credentials are stored in plaintext in SQLite for simplicity. For production, encrypt secrets at rest and restrict DB access.
- When exposing the backend publicly, put it behind a trusted reverse proxy, enable TLS, and restrict CORS.
- Gemini and search API keys should be treated as secrets and provided via environment variables.

## Troubleshooting

- No models listed / AI server errors
  1) Verify the Ollama URL or Gemini API key in the UI.
  2) Check connectivity from the backend container to the Ollama host.
  3) Confirm your models are pulled in Ollama (e.g., `ollama pull <model>`).

- OCR errors
  - Ensure Tesseract is installed (Docker image includes it). For local, install it and update `tesseract_path` in `config.json` if needed.

- Research yields few or no incidents
  - Increase `target_count`, relax filters, or enable `use_search_apis` with valid keys.
  - Provide `seed_urls` and set `focus_on_seed` as appropriate.

- Database not persisting in Docker
  - Set `database_file` in `backend/config.json` to `database/tasks.db` so it uses the volume.
  - Rebuild and restart with compose.

- Containers fail to start
  - Inspect logs: `docker-compose logs backend` and `docker-compose logs frontend`.

## Roadmap Ideas

- Add auth and role‑based access to admin endpoints.
- Export finalized research to branded PDFs.
- Add Kubernetes manifests and Helm chart.
- Add Vite dev proxy for seamless local development.

## Contributing

Issues and PRs are welcome. Please keep changes focused and include clear reproduction steps for bugs.

---

Cerberus AI is provided as‑is without warranty. Ensure your usage complies with data access policies of crawled sources and API providers.

