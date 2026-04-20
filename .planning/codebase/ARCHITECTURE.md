# Architecture

**Analysis Date:** 2026-04-19

## Pattern Overview

**Overall:** Monolithic full-stack application — FastAPI backend serving a React SPA, with an integrated background scheduler and a multi-stage async pipeline.

**Key Characteristics:**
- Single Python process runs the API server, background task engine, and optional APScheduler
- FastAPI serves both the REST API (`/api/*`) and the compiled React build (SPA fallback route)
- All database I/O is fully async via SQLAlchemy async + asyncpg (PostgreSQL) or aiosqlite (SQLite)
- A `deque`-based in-memory ring buffer (200 entries) provides live log streaming to the frontend via polling — no WebSocket needed
- Automation safety: `AUTO_APPLY_ENABLED=False` and `DRY_RUN=True` by default; live submissions require both flags set

---

## Layers

**API Layer:**
- Purpose: HTTP request handling, request validation, response serialization
- Location: `backend/api/routes.py`
- Contains: FastAPI router, Pydantic request schemas, all route handlers, `_run_state` in-memory dict for live run status, background task launchers
- Depends on: Core layer, AI layer, DB layer
- Used by: Frontend via `axios` from `frontend/src/api/client.ts`

**Core Layer:**
- Purpose: Domain orchestration — job ingestion, scoring, application lifecycle, config
- Location: `backend/core/`
- Contains:
  - `application_engine.py` — `ApplicationEngine` class: ingest → score → submit pipeline
  - `config.py` — `Settings` via pydantic-settings; loads `.env`
  - `tier_config.py` — FAANG/tier-2 company detection; drives LaTeX resume tailoring
  - `resume_parser.py` — PDF/DOCX text extraction + AI-assisted parsing
  - `email_service.py` — async SMTP via `aiosmtplib`
- Depends on: AI layer, DB layer, Scrapers layer
- Used by: API layer, Scheduler

**AI Layer:**
- Purpose: All LLM interactions — scoring, generation, tailoring
- Location: `backend/ai/`
- Contains:
  - `client.py` — `get_ai_client()` factory; returns the right async client for the configured provider
  - `matcher.py` — `JobMatcher`: score_match, deep_score_match, cover letter, Q&A answering
  - `resume_tailor.py` — `ResumeTailor`: ATS keyword extraction, bullet rewriting
  - `latex_resume.py` — `LatexResumeGenerator`: AI-generated LaTeX → PDF compilation
  - `company_intel.py` — `CompanyIntel`: company research, salary estimates, interview prep
  - `followup.py` — `FollowUpGenerator`: follow-up email drafting and scheduling
- Depends on: `config.py` for provider/key resolution
- Used by: Core layer (engine, resume_parser), API layer (direct calls for premium endpoints)

**Scraper Layer:**
- Purpose: Job discovery from 6 external boards
- Location: `backend/scrapers/`
- Contains:
  - `base.py` — `BaseScraper` ABC + `ScrapedJob` dataclass + `RateLimiter` (adaptive exponential backoff)
  - `linkedin_scraper.py` — Playwright browser scraper; supports Easy Apply
  - `indeed_scraper.py` — Playwright browser scraper
  - `glassdoor_scraper.py` — Playwright browser scraper
  - `naukri_scraper.py` — Playwright browser scraper; India-specific
  - `wellfound_scraper.py` — Playwright browser scraper
  - `dice_scraper.py` — HTTP-only scraper (httpx, no browser)
  - `ats_applier.py` — `ATSApplier`: AI-driven form filler for Greenhouse, Lever, Workday, Ashby, BambooHR, Taleo, iCIMS, SmartRecruiters + generic fallback
  - `__init__.py` — exports `SCRAPERS` dict, `BROWSER_SCRAPERS` set, `HTTP_SCRAPERS` set
- Depends on: Playwright async API, httpx, `base.py`
- Used by: Core layer (ApplicationEngine), API layer (background task), Scheduler

**DB Layer:**
- Purpose: Persistence — schema definition, session management, DB init
- Location: `backend/db/database.py`, `backend/models/models.py`
- Contains: SQLAlchemy async engine, `AsyncSessionLocal`, `Base`, `get_db` dependency, `init_db()`
- Depends on: `config.py` for `DATABASE_URL`
- Used by: All layers that need DB access

**Scheduler:**
- Purpose: Autonomous periodic job search and follow-up email dispatch
- Location: `backend/scheduler.py`
- Contains: `run_scheduled_search()`, `run_followup_scheduler()`, `start_scheduler()` (APScheduler `AsyncIOScheduler`)
- Schedule:
  - Job search: every `SCHEDULER_INTERVAL_MINUTES` (default 60)
  - Follow-up emails: every 30 minutes
- Can run as standalone process (`python -m backend.scheduler`) or be launched separately from the main app

**Frontend Layer:**
- Purpose: Single-page React dashboard
- Location: `frontend/src/`
- Contains: React Router SPA, Zustand store, typed Axios API client, 11 page components
- Connects to backend: relative `/api` base URL — in dev via Vite proxy, in production served directly by FastAPI's static mount

---

## Data Flow

**Primary Automation Pipeline (Search → Score → Apply):**

1. Frontend calls `POST /api/run/search` with `profile_id`, `resume_id`, `sources`, `dry_run`, `days`
2. Route handler sets `_run_state["running"] = True` and spawns `_run_search_task` via FastAPI `BackgroundTasks`
3. `_run_search_task` in `routes.py`:
   - Loads `JobProfile` and `Resume` from DB
   - Initializes `JobMatcher` + `ApplicationEngine`
   - Fans out scrape tasks: `asyncio.gather(*[_scrape_one(source, role, location) ...])` — browser scrapers run under a `Semaphore(MAX_BROWSER_SCRAPERS=2)`
   - Each scraper returns `List[ScrapedJob]`
4. Collected `ScrapedJob` list → `engine.ingest_jobs(batch)`:
   - Deduplicates by `external_id` and by `MD5(company|title)` slug
   - Inserts new `Job` rows; skips already-applied companies
5. `engine.queue_applications(profile, resume)`:
   - Loads unscored jobs (up to 300)
   - Applies `_profile_filter()` (keyword inclusion/exclusion, remote-only flag)
   - For each job: `asyncio.gather` AI scoring under `Semaphore(MAX_AI_CONCURRENCY=8)` via `matcher.score_match()`
   - Score < `MIN_MATCH_SCORE` (0.70) → `SKIPPED`
   - Score >= `MIN_MATCH_SCORE` and `apply_recommendation=True` and score < `HITL_REVIEW_THRESHOLD` (0.85) → `PENDING`
   - Score >= `HITL_REVIEW_THRESHOLD` → triggers `deep_score_match()` (7-block analysis) → `REVIEW`
6. `engine.process_pending_applications(resume, dry_run)`:
   - Dry run: calls `_prepare_application()` concurrently for all pending, marks `APPLIED`
   - Live run: launches `N` Playwright browser workers (N = min(MAX_BROWSER_SCRAPERS, pending count))
   - Each worker: logs into LinkedIn/Naukri if credentials configured, pops from `asyncio.Queue`, calls `_submit_one()`
7. `_submit_one()`:
   - LinkedIn Easy Apply jobs → `LinkedInScraper.easy_apply()`
   - Naukri native → `_apply_naukri_native()` (button click)
   - All other ATS → `ATSApplier.apply()` (AI-driven form filling)
8. Stats written to `DailyStats` table; `_run_state` updated; frontend poll picks up logs via `GET /api/run/status`

**Application Preparation (`_prepare_application`):**

Runs concurrently for each application before submission:
- `matcher.generate_cover_letter()` — routed to cheap client (Groq/Flash)
- `matcher.answer_question()` × N standard questions (years experience, work authorization)
- `LatexResumeGenerator.generate_tailored_pdf()` — only if `tier_config.should_tailor()` returns True
  - Tier 1 (FAANG+): always tailor if score >= 0.70
  - Tier 2 (Shopify, Atlassian, etc.): tailor if score >= 0.80
  - Non-tier: skip LaTeX generation
- Tailored PDF saved to `data/tailored_resumes/<app_id>_<slug>.pdf`; path stored in `Application.tailored_resume_path`

**AI Scoring Pipeline (matcher.py):**

- `score_match()` → always uses `complex_client` (primary AI provider, Gemini-1.5-Pro or Claude)
- `generate_cover_letter()` / `answer_question()` → uses `simple_client` (Groq/Gemini-Flash) if available, falls back to complex client
- All AI responses: JSON strip → `json.loads` → regex fallback extraction on parse error
- Provider dispatch: `_call_ai(client, provider, prompt, model, max_tokens)` — handles Anthropic, OpenAI, Gemini, Groq, xAI

**Follow-Up Pipeline (Scheduler-driven):**

1. Every 30 minutes, `run_followup_scheduler()` fires
2. For each `APPLIED` application without `FollowUp` rows: seeds 3 scheduled records (thank_you, gentle_check, final_followup)
3. For all `FollowUp` records where `scheduled_for <= now` and `status = pending`:
   - Generates email via `FollowUpGenerator.generate_followup()`
   - Sends via SMTP if configured (`email_service.send_email`)
   - Updates `status` to `sent` or `failed`

**HITL Review Flow:**

1. High-scoring jobs (>= 0.85) land in `status = REVIEW` with `deep_analysis` JSON attached
2. Frontend `ReviewQueue` page polls `GET /api/applications/review-queue`
3. Human clicks Approve → `POST /api/applications/{id}/approve` → status moves to `PENDING`
4. On next apply run, engine picks up `PENDING` applications and submits them

**Frontend State Flow:**

- Zustand store (`frontend/src/store/useStore.ts`) holds: `activeResume`, `activeProfile`, `isRunning`, `logs`, `runStats`
- `App.tsx` runs a global polling effect: every 1s when `isRunning`, every 3s otherwise — calls `GET /api/run/status`
- Individual pages call typed API methods from `frontend/src/api/client.ts` via `axios`

---

## Key Abstractions

**`ScrapedJob` (dataclass):**
- Purpose: Normalized job record crossing scraper → engine boundary
- Definition: `backend/scrapers/base.py`
- Fields: `external_id`, `title`, `company`, `location`, `description`, `url`, `apply_url`, `source`, `easy_apply`, `remote`, salary range, `extra_data`

**`ApplicationStatus` (enum):**
- Purpose: Drives the entire application lifecycle state machine
- Definition: `backend/models/models.py`
- Values: `PENDING → REVIEW → APPLYING → APPLIED → INTERVIEW → OFFER | FAILED | SKIPPED | REJECTED`

**`BaseScraper` (ABC):**
- Purpose: Shared contract for all 6 scrapers + adaptive rate limiting
- Definition: `backend/scrapers/base.py`
- Required methods: `search_jobs()`, `get_job_details()`
- Context manager protocol for browser scrapers (`__aenter__` / `__aexit__`)

**`ApplicationEngine`:**
- Purpose: Central orchestrator for the ingest-score-apply pipeline
- Definition: `backend/core/application_engine.py`
- Key methods: `ingest_jobs()`, `queue_applications()`, `process_pending_applications()`, `_prepare_application()`, `_submit_one()`
- Accepts a `log_fn` callback so the API layer can inject live logging into `_run_state`

**`JobMatcher`:**
- Purpose: All AI-powered assessment — scoring, cover letters, Q&A
- Definition: `backend/ai/matcher.py`
- Dual-client pattern: `complex_client` for scoring (expensive), `simple_client` for generation (cheap)
- Smart routing: scoring always goes to Gemini-1.5-Pro/Claude; cover letters and Q&A go to Groq/Flash

**`ATSApplier`:**
- Purpose: Universal ATS form filler using AI to interpret form fields
- Definition: `backend/scrapers/ats_applier.py`
- Supports: Greenhouse, Lever, Workday, Ashby, BambooHR, Taleo, iCIMS, SmartRecruiters + generic HTML fallback
- Humanizes input: random keystroke delays, mouse movement, scroll before click

---

## Entry Points

**Production API Server:**
- Location: `backend/main.py`
- Triggers: `uvicorn backend.main:app`
- Responsibilities: CORS setup, route mounting at `/api`, DB init via lifespan, frontend SPA serving from `frontend/dist/`

**Background Scheduler (standalone):**
- Location: `backend/scheduler.py`
- Triggers: `python -m backend.scheduler`
- Responsibilities: Periodic job search + apply cycle, follow-up email dispatch

**Development Frontend:**
- Location: `frontend/src/main.tsx`
- Triggers: `npm run dev` (Vite dev server, proxies `/api` to backend)

**Docker Entry:**
- Location: `Dockerfile`, `Dockerfile.full`, `docker-compose.yml`

---

## Error Handling

**Strategy:** Catch-and-continue at the pipeline boundary; individual scraper/apply failures do not abort the batch.

**Patterns:**
- Scrapers: exceptions caught in `_scrape_one()` → logged as error, returns `[]` — run continues
- AI calls: exceptions caught in `matcher.py` methods → return default `{"score": 0.0, "apply_recommendation": False}`
- Application submission: `_submit_one()` wrapped in try/except → returns `(False, error_str)` → status set to `FAILED`
- `asyncio.gather(*coros, return_exceptions=True)` in `_prepare_application()` — exceptions stored as values, not raised
- DB: SQLAlchemy session has rollback in `get_db()` on exception; engine-level commits are explicit
- Frontend: Axios response interceptor extracts `error.response.data.detail` and rejects with a normalized `Error`

---

## Background Task System

**Mechanism:** FastAPI `BackgroundTasks` for user-triggered runs; APScheduler `AsyncIOScheduler` for timer-driven runs.

**In-Memory Run State:**
```python
_run_state = {
    "running": bool,
    "logs": deque(maxlen=200),  # ring buffer of {ts, level, msg}
    "stats": dict,              # scraped/new/queued/applied/failed counts
}
```
- Prevents concurrent runs: `if _run_state["running"]: return`
- Frontend polls `GET /api/run/status` to stream live progress

**Concurrency Controls:**
- `asyncio.Semaphore(MAX_BROWSER_SCRAPERS=2)` — caps simultaneous Playwright browser instances
- `asyncio.Semaphore(MAX_AI_CONCURRENCY=8)` — caps concurrent AI API calls during scoring
- `asyncio.Queue` + `asyncio.Lock` for multi-worker application submission

---

## Cross-Cutting Concerns

**Logging:** `loguru` throughout backend; structured JSON-like log lines; `_log()` helper in `routes.py` dual-writes to loguru and `_run_state["logs"]`

**Validation:** Pydantic schemas at API boundary; SQLAlchemy model constraints at DB boundary; no shared validation layer between them

**Authentication:** No user authentication system. Single-user application. Credentials (LinkedIn, Naukri) stored as env vars, used by the engine at runtime.

**Configuration:** All settings via `backend/core/config.py` `Settings` class (pydantic-settings, reads `.env`). Single global `settings` instance imported wherever needed.

**AI Provider Abstraction:** `get_ai_client()` in `backend/ai/client.py` returns provider-specific async clients; callers receive an opaque client object and pass `provider` string alongside it for dispatch in `_call_ai()`.

---

*Architecture analysis: 2026-04-19*
