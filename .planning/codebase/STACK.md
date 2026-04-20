# Technology Stack

**Analysis Date:** 2026-04-19

## Languages

**Primary (Backend):**
- Python 3.12 — all backend logic, AI calls, scraping, API

**Primary (Frontend):**
- TypeScript 5.7 — all frontend UI code
- TSConfig target: ES2020, strict mode enabled

## Runtime

**Environment:**
- Python 3.12.3 (system)
- Node 20 (Docker build stage — `FROM node:20-slim AS frontend-builder`)

**Package Manager:**
- pip (backend) — lockfile: `backend/requirements.txt`
- npm (frontend) — lockfile: `frontend/package-lock.json` (present via `package*.json` copy in Dockerfile)

## Frameworks

**Backend Core:**
- FastAPI 0.115.0 — async web framework; entry point `backend/main.py`
- Uvicorn 0.32.0 (standard extras) — ASGI server; started via `uvicorn backend.main:app`
- Pydantic 2.10.0 — data validation and settings
- pydantic-settings 2.6.1 — `Settings` class in `backend/core/config.py`

**Frontend Core:**
- React 18.3.1 — UI framework
- React Router DOM 6.28.0 — client-side routing
- Vite 6.0.5 — dev server and build tool; config at `frontend/vite.config.ts`

**Database ORM:**
- SQLAlchemy 2.0.36 (async) — ORM; models in `backend/models/models.py`
- Alembic 1.14.0 — migrations (present in requirements, migration files not yet detected)

**Task Scheduling:**
- APScheduler 3.10.4 — periodic job search runs; interval configured via `SCHEDULER_INTERVAL_MINUTES`
- Celery 5.4.0 — async task queue (installed; `docker-compose.yml` runs a `scheduler` service)

**Testing:**
- No test framework detected in requirements or package.json (scripts in `scripts/` are manual smoke tests)

**Build/Dev:**
- `@vitejs/plugin-react` 4.3.4 — Vite React plugin
- TypeScript compiler (`tsc`) — used in `npm run build` (`tsc && vite build`)
- autoprefixer 10.4.20 + PostCSS 8.4.49 — CSS processing
- TailwindCSS 3.4.16 — utility CSS framework

## Key Dependencies

**AI/LLM:**
- `anthropic` 0.40.0 — Claude API client (`backend/ai/client.py`)
- `openai` 1.57.0 — OpenAI and xAI (Grok) client (xAI uses OpenAI client with custom base URL)
- `google-generativeai` 0.8.3 — Gemini API client
- groq (not pinned in requirements — installed optionally: `pip install groq`) — Groq/Llama client

**Browser Automation:**
- `playwright` 1.49.0 — headless Chromium for scraping and ATS form filling (`backend/scrapers/`, `backend/scrapers/ats_applier.py`)
- `httpx` 0.28.0 — async HTTP client for API-based scrapers (e.g., Dice)

**Resume Parsing:**
- `pdfplumber` 0.11.4 — PDF text extraction
- `python-docx` 1.1.2 — DOCX parsing
- `pymupdf` 1.25.0 — additional PDF extraction (MuPDF)

**HTML Parsing:**
- `beautifulsoup4` 4.12.3 — HTML parsing
- `lxml` 5.3.0 — XML/HTML backend for BeautifulSoup

**Auth & Security:**
- `python-jose[cryptography]` 3.3.0 — JWT handling
- `passlib[bcrypt]` 1.7.4 — password hashing

**Infrastructure:**
- `redis` 5.2.0 — Redis client (for Celery broker)
- `aiosqlite` 0.20.0 — async SQLite driver (default local dev database)
- `asyncpg` 0.30.0 — async PostgreSQL driver (used when `DATABASE_URL` is PostgreSQL, e.g., on Render)

**Resilience:**
- `tenacity` 9.0.0 — retry logic with exponential backoff in scrapers

**Logging:**
- `loguru` 0.7.2 — structured logging across all backend modules
- `rich` 13.9.4 — terminal formatting

**Email:**
- `aiosmtplib` 3.0.2 — async SMTP (`backend/core/email_service.py`)

**Utilities:**
- `python-dotenv` 1.0.1 — `.env` file loading
- `pandas` 2.2.3 — data processing

**Frontend UI:**
- Zustand 5.0.2 — global state management (`frontend/src/store/`)
- Radix UI (`@radix-ui/react-*`) — accessible headless UI primitives (dialog, select, tabs, switch, progress, tooltip)
- Framer Motion 11.18.2 — animations
- Recharts 2.13.3 — charts/dashboards
- Axios 1.7.9 — HTTP client (`frontend/src/api/client.ts`)
- react-hot-toast 2.4.1 — toast notifications
- react-dropzone 14.3.5 — file upload (resume drag-and-drop)
- lucide-react 0.468.0 — icon library
- date-fns 4.1.0 — date formatting
- clsx + tailwind-merge — conditional className utilities

## Configuration

**Environment:**
- All config via `backend/core/config.py` using pydantic-settings
- Loaded from `.env` file (root-level); `.env.example` committed (`.env` itself not committed)
- `class Config: env_file = ".env"; case_sensitive = True`

**Key env vars required for operation:**
```
# AI (at least one required)
ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, XAI_API_KEY
AI_PROVIDER=gemini        # which provider to use
AI_MODEL=gemini-1.5-flash

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/applyra.db   # default (local)
# or: postgresql+asyncpg://user:pass@host/db         # production

# Job board credentials (optional — enables scraping with login)
LINKEDIN_EMAIL, LINKEDIN_PASSWORD
NAUKRI_EMAIL, NAUKRI_PASSWORD

# Safety switches
AUTO_APPLY_ENABLED=false   # must be true to actually submit applications
DRY_RUN=true               # simulate without submitting

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0

# Email (optional)
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, NOTIFY_EMAIL

# Rate limiting / concurrency
SCRAPER_DELAY_SECONDS=1.0
MAX_APPLICATIONS_PER_DAY=25
MAX_AI_CONCURRENCY=8
MAX_BROWSER_SCRAPERS=2
```

**Build:**
- `frontend/vite.config.ts` — Vite config; dev proxy `/api` → `http://localhost:8000`
- `frontend/tsconfig.json` — TypeScript compiler options (strict mode, ESNext modules, no-emit)
- Multi-stage `Dockerfile` — node:20 frontend build + python:3.12-slim runtime
- `Dockerfile.full` — extended image (used by `docker-compose.yml`, includes scheduler)
- `docker-compose.yml` — three services: `applyra` (web), `scheduler`, `redis`

## Platform Requirements

**Development:**
- Python 3.12+
- Node 20+ (for frontend build)
- Redis (for Celery; optional if scheduler not running)
- Playwright browsers: `playwright install chromium` required
- LaTeX (`pdflatex`) — optional; falls back to reportlab if absent (for LaTeX resume generation)

**Production:**
- Deployed on Render (free tier) — `render.yaml` configures web service + managed PostgreSQL
- Database: SQLite (local/Docker) or PostgreSQL via `asyncpg` (Render/production)
- Docker image exposed on port 8000
- Frontend served as static files from `frontend/dist/` by the FastAPI app itself

---

*Stack analysis: 2026-04-19*
