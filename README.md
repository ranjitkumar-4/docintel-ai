# DocIntel AI — Intelligent Document Investigator

DocIntel AI is a hackathon MVP for investigating uploaded organizational documents. It indexes excerpts, answers questions from retrieved evidence, exposes source references, flags selected cross-document contradictions, and abstains when relevant evidence is missing.

## Problem and solution

Policies and notices are spread across PDFs, Word files, text files, and scans. Manually locating an answer and checking whether another document disagrees is slow. DocIntel AI provides a single upload-and-question workflow with document/page/chunk provenance and a visible uncertainty path. It is a prototype, not a legal or compliance authority.

## Current capabilities

- Upload PDF, DOCX, TXT, JPG/JPEG, and PNG files. Files are validated per item; each outcome is `SUCCESS`, `FAILED`, or `PARTIAL`.
- Extract PDF text page-by-page, DOCX paragraphs/tables with approximate page grouping, TXT text, and image text through Tesseract OCR.
- Chunk extracted content with page and document metadata; embed and persist it in ChromaDB.
- Retrieve across all indexed documents or within selected documents using Chroma cosine distance plus keyword matching and a configured relevance threshold.
- Generate local extractive answers or use configured OpenAI/Gemini answer generation. The answer layer checks evidence coverage and handles detected conflicts before generation. A selected external provider that is missing credentials or unavailable returns an explicit API error; it does not claim a local fallback as an external-provider answer.
- Return supporting text, document name, page (approximate for DOCX), chunk ID, and relevance score. Conflicting answers include both statements and use `LOW` confidence.
- Store document metadata and investigation history as JSON; restore document chunks from ChromaDB after process restart.
- Expose backend, vector-index, and OCR readiness to the frontend.

The local embedding option is a deterministic 384-dimensional hash vectorizer, not a pretrained language model. Its similarity is combined with lexical overlap; evaluate it on your corpus before relying on it. External embedding providers are supported only for the model profiles documented below, and switching profiles requires a deliberate reindex.

## Architecture

```text
React + TypeScript (Vite)
        │ HTTP /api (CORS allowlist)
        ▼
FastAPI
  ├─ upload validation and PDF/DOCX/TXT/OCR extractors
  ├─ page-aware chunker
  ├─ embedding profile validation
  ├─ persistent ChromaDB cosine index
  ├─ thresholded hybrid retrieval
  ├─ evidence-grounded answer generation
  ├─ topic/context-aware conflict checks
  └─ JSON document, conflict, and investigation registries
```

## Project structure

```text
backend/          FastAPI API, document processing, retrieval, and tests
frontend/         React + TypeScript + Vite application
documents/        Local upload/demo-data directory (contents are gitignored)
data/             Local JSON state (gitignored)
chroma_db/        Local ChromaDB index (gitignored)
seed_demo.py      Idempotent demo corpus loader
reindex_embeddings.py
                  Safe staged embedding/index migration utility
start.sh          Starts the local backend and frontend
render.yaml       Render backend service and persistent-disk blueprint
```

### Storage

- `CHROMA_PERSIST_DIR`: Chroma vector index.
- `UPLOAD_DIR`: uploaded and generated demo documents.
- `DATA_DIR`: JSON registry/history/conflict state and the active-index pointer.

Keep all three on persistent storage. The API and metadata are designed for one backend process; this MVP does not provide distributed locking or multi-replica coordination.

## Requirements and local setup

Prerequisites: Python 3.11+, Node.js 18+, npm, and (for OCR) the Tesseract executable.

```bash
# From the project root
cp .env.example .env  # if .env does not already exist; do not overwrite your secrets
python3.11 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cd frontend
npm install
cd ..
```

Start the backend and frontend in separate terminals:

```bash
./run_backend.sh
```

```bash
./run_frontend.sh
```

The frontend is at `http://localhost:5173`; the API and interactive API docs are at `http://127.0.0.1:8000` and `http://127.0.0.1:8000/docs`. `./start.sh` starts both services together.

To use a different backend URL for the frontend, set `VITE_API_BASE_URL` at frontend build time, for example:

```bash
cd frontend
VITE_API_BASE_URL=https://your-api.example.com npm run build
```

## OCR setup

`pytesseract` is only a Python wrapper; it does not install Tesseract.

- macOS with Homebrew: `brew install tesseract`
- Debian/Ubuntu: `sudo apt-get update && sudo apt-get install -y tesseract-ocr`
- Windows: install a Tesseract OCR engine and add its executable directory to `PATH`.

Verify on the **backend host** with `tesseract --version`. `/api/health` reports `ocr_available`. If Tesseract is unavailable or returns no readable text, image extraction fails explicitly and error/placeholder text is not indexed as successful content. Scanned PDF pages are marked with extraction warnings; selectable PDF text remains usable without OCR. OCR success on a specific document still depends on scan quality and language data.

## Environment configuration

Copy `.env.example` to `.env` and configure the backend:

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | Answer synthesis: `local`, `openai`, or `gemini`. |
| `OPENAI_API_KEY`, `GEMINI_API_KEY` | Optional backend-only credentials. Never use a `VITE_` prefix. The UI does not accept, store, or return secret values. |
| `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL` | One of `local/local-hash-v1` (384), `openai/text-embedding-3-small` (1536), or `gemini/text-embedding-004` (768). |
| `CHROMA_PERSIST_DIR`, `UPLOAD_DIR`, `DATA_DIR` | Persistent vector, file, and JSON storage paths. |
| `CHUNK_SIZE`, `CHUNK_OVERLAP` | Chunking configuration. |
| `SIMILARITY_THRESHOLD`, `TOP_K_RESULTS` | Retrieval relevance threshold and result count. |
| `CORS_ORIGINS` | Comma-separated exact frontend origins allowed to call the backend. |
| `APP_ENV` | Set to `production` when deployed. |
| `ALLOW_DESTRUCTIVE_RESET` | Keep `false`; reset remains disabled in production even if accidentally enabled. |

AI services are optional. The default `LLM_PROVIDER=local` uses the deterministic local grounded extractor and makes no external LLM calls. If configured, `LLM_PROVIDER=openai` calls the OpenAI Chat Completions API using `gpt-4o-mini`; `LLM_PROVIDER=gemini` calls the Google Generative Language `gemini-1.5-flash` API. External embeddings use OpenAI `text-embedding-3-small` or Gemini `text-embedding-004` independently of the answer provider. All API keys stay in backend environment variables and are sent in authorization headers where the provider supports them. External network/provider calls were not part of the local validation.

Changing provider, model, or vector dimension does not delete the existing index. A mismatch disables vector queries/indexing and is reported by `/api/health`; do not point a different embedding profile at an existing collection.

### Safe reindex

To build a separate Chroma collection using the currently configured embedding profile and switch to it only after it validates:

```bash
PYTHONPATH=backend .venv/bin/python reindex_embeddings.py
```

The existing collection is preserved. Back up `CHROMA_PERSIST_DIR`, `DATA_DIR`, and `UPLOAD_DIR` before reindexing or changing storage configuration.

## Demo workflow

1. Start the backend and frontend. The backend does not seed documents automatically; check that the dashboard reports backend, vector store, and OCR status.
2. For a preloaded conflict demo, click **Load Sample Documents**, or run `PYTHONPATH=backend .venv/bin/python seed_demo.py`. The seed script is idempotent. `--reset` replaces known demo records only and preserves non-demo registry entries.
3. The canonical corpus includes normal factual content, intentionally conflicting 20-day/18-day leave statements, an unanswered pet-insurance topic, and an OCR image notice. OCR text is only available if Tesseract is installed; otherwise that demo image shows its actual failed status.
4. Ask **“How many paid leaves are available?”**. For indexed policy and handbook documents, expect an explicit conflict alert, both source statements, and `LOW` confidence.
5. Ask **“What is the company's pet insurance policy?”**. If no uploaded document answers it, expect **“Information not found.”**, no supporting source, and `NOT FOUND` confidence.
6. Ask a factual question present in the demo corpus (for example, **“What is the home office setup stipend for remote work?”**). Open a source to inspect its extracted text, page, chunk ID, and relevance score.
7. Open an old investigation from History or its generated `/#investigation-{id}` link. The corresponding record and source excerpt are persisted with the JSON history and vector index.

Answers and conflict detection are heuristic and corpus-dependent. A demo prompt is not hardcoded to return its expected answer.

For a staged judge workflow, upload `Employee_Handbook.pdf` (18 days) and `HR_Rules.pdf`/`.txt` first and ask the annual paid-leave question. Then upload `Leave_Policy.pdf` (20 days) and ask again to demonstrate conflict reporting. The built-in seeded corpus already includes its explicit 20-day/18-day conflict, so do not seed that corpus before demonstrating the “before conflict / after conflict” sequence.

## Tests and checks

Backend regression suite (Python `unittest`):

```bash
cd backend
../.venv/bin/python -m unittest discover -s tests -v
```

The suite covers PDF/DOCX/TXT extraction, chunking, OCR error handling and a real-image Tesseract OCR upload/index/retrieval test when Tesseract is installed, embeddings and Chroma metadata, retrieval threshold/filter behavior, grounded answers and sources, no-answer handling, external provider failures without fallback, leave/numeric/polarity conflicts and unrelated-number false positives, upload statuses, restart persistence of document details/retrieval/history/share links, and repeated demo seeding/reset behavior.

Frontend TypeScript check and production build:

```bash
cd frontend
npm run build
```

## API overview

FastAPI’s interactive schema is available at `/docs`. Core endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Backend, vector-index, embedding-profile, persistence, and OCR readiness |
| `POST` | `/api/documents/upload` | Validate/process one or more documents and return per-file status |
| `GET` | `/api/documents` and `/api/documents/{id}` | List documents and inspect persisted document chunks |
| `POST` | `/api/documents/seed-demo` | Index the canonical demo corpus |
| `POST` | `/api/investigation/ask` | Retrieve evidence, answer/abstain, cite sources, and detect conflict |
| `GET` | `/api/investigation/history` and `/api/investigation/{id}` | Retrieve saved investigations |
| `GET` | `/api/conflicts` | List recorded conflicts |
| `GET`, `POST` | `/api/settings` | Read safe settings or update local non-secret runtime settings; updates are disabled in production |
| `POST` | `/api/system/reset` | Destructive reset, disabled in production and opt-in locally |

## Deployment

Deploy the frontend to Vercel and the FastAPI backend to a persistent Python host. Vercel hosts this React/Vite frontend; it does not host this project's persistent FastAPI + ChromaDB service. A Render Blueprint is provided in `render.yaml` and provisions one Python service with a persistent disk.

### Render backend

1. Push this repository to GitHub and create a Render Blueprint from it. Render reads `render.yaml`; the service root is `backend`, and the persistent disk is mounted at `/var/data`.
2. The Blueprint uses the paid `starter` service plan because Render's free web services do not provide a persistent disk. Keep one backend instance: the local Chroma and JSON storage do not support concurrent replicas.
3. After deployment, confirm `https://<render-service>.onrender.com/health` responds successfully. The service uses the local answer and embedding providers by default; optional external API keys are not required.
4. `backend/apt.txt` requests the Tesseract system package for the Render Python build. Confirm `/api/health` reports OCR available after deployment; if the host build does not install the package, image uploads must report OCR unavailable rather than claim OCR success.

### Vercel frontend

1. Import the same GitHub repository as a Vercel project and set **Root Directory** to `frontend`.
2. Use the Vite defaults: install `npm install`, build `npm run build`, and output directory `dist`. `frontend/vercel.json` configures the SPA fallback.
3. Add the Vercel project environment variable `VITE_API_BASE_URL` with the backend origin only, e.g. `https://<render-service>.onrender.com` (no trailing slash and no `/api`). This is a public URL, not a secret. Redeploy after setting or changing it.
4. Copy the exact production Vercel origin, e.g. `https://<your-project>.vercel.app`, into the Render service's `CORS_ORIGINS` environment variable. Add a comma-separated list only if multiple explicit browser origins are needed. Redeploy/restart the backend after changing it.
5. Verify the Vercel site can call the backend, upload a non-sensitive test document, ask a question, and open its sources.

### Storage, secrets, and exposure

- Render's `/var/data` disk stores `CHROMA_PERSIST_DIR`, `UPLOAD_DIR`, and `DATA_DIR` across service restarts. Back up this disk before reindexing or changing embedding profiles.
- Install Tesseract and required language data on the backend host if image/scanned-PDF OCR is required; `/api/health` reports OCR readiness.
- Keep LLM/embedding API credentials only in backend environment secrets. Never set secrets as `VITE_*` variables or commit `.env`.
- This MVP has no authentication, authorization, per-user separation, rate limiting, or encrypted-at-rest storage. A public deployment is suitable only for a controlled demo with non-sensitive documents; do not upload confidential company or personal files.
- Hosted deployment has not been performed or verified by this repository configuration alone. Provider account setup, repository connection, environment variables, health checks, and a real hosted upload/question flow still need to be completed.

## Security and limitations

- `.env`, `.env.*` (except `.env.example`), local document uploads, Chroma data, and JSON state are ignored by Git.
- `/api/settings` exposes whether backend keys are configured, not the keys themselves. Secret values are configured on the backend, not sent from the browser.
- Destructive reset requires `ALLOW_DESTRUCTIVE_RESET=true` in a trusted non-production environment. The production environment check always disables it.
- There is no user authentication, per-user document isolation, rate limiting, encrypted-at-rest storage, or multi-process write coordination. This is a local/demo MVP, not a hardened multi-tenant service.
- DOCX page numbers are approximate. OCR quality and conflict heuristics are not guaranteed. The local embedding model is a lightweight hash vectorizer. External LLM output is constrained by prompts and evidence checks, not formally verified.
- External OpenAI/Gemini integrations require valid backend credentials, connectivity, and provider availability; they are not required for the default local demo.
- External API calls, successful real-image Tesseract OCR, and hosted deployment are not verified in the current local environment.
- Use a clean persistent data directory when changing embedding dimensions/providers; only the explicit reindex workflow should activate a new vector collection.

## Future improvements

Authentication and authorization, shared transactional metadata storage, evaluation datasets for retrieval/conflict precision, richer table/OCR handling, and observability are appropriate next steps before production use.
