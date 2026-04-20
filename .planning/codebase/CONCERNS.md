# Technical Concerns

**Analysis Date:** 2026-04-20

## Critical

### 1. In-Memory Run State — Single-User, Single-Process Only
**File:** `backend/api/routes.py:17–20`
```python
_run_state: dict = {
    "running": False,
    "logs": deque(maxlen=200),
    "stats": {},
}
```
- State is a module-level dict — lost on restart, invisible across processes
- Docker Compose runs scheduler as a separate container: its logs never appear in the UI
- Multiple concurrent users would share and corrupt the same state
- No persistence: a crash mid-run loses all progress
- **Fix:** Move to Redis pub/sub or SSE with DB-backed run records

### 2. No Authentication / Authorization
**File:** `backend/main.py`, `backend/api/routes.py`
- All API endpoints are completely open — no auth middleware
- Anyone with network access can trigger job applications, read resumes, delete data
- Credentials (LinkedIn/Naukri passwords) flow through unprotected endpoints
- CORS only allows localhost origins — adequate for local, not for deployed instances
- **Fix:** Add JWT or session-based auth before any deployment on a shared host

### 3. Celery/Redis Installed But Not Used
**Files:** `requirements.txt`, `docker-compose.yml`
- `celery==5.4.0` and `redis==5.2.0` are installed and Redis is in docker-compose
- Actual background tasks use FastAPI `BackgroundTasks` (in-process, blocking event loop)
- Long-running scrape+apply tasks (can take 30+ min) block the FastAPI worker
- **Fix:** Wire Celery tasks for `_run_search_task` to unblock the event loop properly

---

## High

### 4. Scraper CSS Selector Fragility
**Files:** `backend/scrapers/*.py`
- All browser scrapers use hardcoded CSS selectors and JS `querySelectorAll` patterns
- LinkedIn, Indeed, Glassdoor, Wellfound change their HTML frequently (A/B tests, redesigns)
- No fallback selector chains for most scrapers — one change = 0 results silently
- Dice scraper uses HTTP with no bot detection mitigation (single IP, no rotation)
- `BROWSER_SCRAPERS` set in `__init__.py` incorrectly lists Glassdoor as browser; Dice as HTTP — but Glassdoor uses Playwright context

### 5. AI Scoring Quality Not Validated
**File:** `backend/ai/matcher.py`
- `MIN_MATCH_SCORE = 0.70` and `HITL_REVIEW_THRESHOLD = 0.85` are arbitrary defaults
- No baseline dataset to measure false positives/negatives
- Different AI providers return differently calibrated scores — Gemini vs Claude vs GPT will produce different distributions for the same job/resume pair
- Score is parsed from JSON in AI response: if model returns non-JSON, score defaults to 0.0 silently

### 6. `queue_applications` Queries All Unscored Jobs (No Batch Awareness)
**File:** `backend/core/application_engine.py:85`
```python
stmt = select(Job).where(...).order_by(Job.discovered_at.desc()).limit(300)
```
- Hard limit of 300 jobs per scoring call — jobs beyond 300 are never scored in one run
- In batch mode (new), `queue_applications` is called once per batch but still queries all unscored jobs, not just the current batch's newly ingested ones
- Cross-batch scoring overlap means batch N may score jobs from batch N-1 that weren't yet scored

### 7. Daily Application Limit Race Condition
**File:** `backend/core/application_engine.py:195–197`
```python
if (stats.applications_sent or 0) >= settings.MAX_APPLICATIONS_PER_DAY:
    queue.task_done(); continue
```
- Limit is checked under `asyncio.Lock` — correct for single-process
- But across Docker restarts or if `_get_daily_stats` reads stale DB cache, limit could be bypassed
- No atomic increment — read-then-write with async lock is not truly atomic at DB level

---

## Medium

### 8. Resume File Storage — No Cleanup
**File:** `backend/api/routes.py` (resume delete endpoint)
- Uploaded resumes saved to `data/resumes/` — disk fills up over time
- Deleting a resume record does not necessarily delete the file on disk
- Tailored resumes (`tailored_resume_path`) stored in `data/` with no expiry or cleanup

### 9. SQLite in Production (Render Deploy)
**File:** `render.yaml`
- Render deployment uses PostgreSQL (via `DATABASE_URL`), which is correct
- But local default is SQLite, and `asyncpg` (Postgres async driver) is installed alongside `aiosqlite`
- Schema differences between SQLite and PostgreSQL (JSON handling, concurrency) can cause silent bugs when testing locally and deploying to Postgres

### 10. Browser Session Persistence Fragility
**Files:** `backend/core/application_engine.py:188–191`
```python
li_ok = await self._linkedin_login(page, context, ..., "data/session")
naukri_ok = await self._naukri_login(page, context, ..., "data/session_naukri")
```
- Session cookies stored in `data/session/` — not committed to Docker volumes by default
- LinkedIn sessions expire or get invalidated (bot detection) — no automatic re-auth
- Failed login doesn't abort the run, just sets `li_ok = False` and continues silently

### 11. ATS Generic Form Fill — AI Hallucination Risk
**File:** `backend/scrapers/ats_applier.py`
- `_apply_generic()` sends all visible form fields to AI and asks it to fill them
- AI may confidently fill fields with plausible-but-wrong answers (salary, start date, references)
- No field-level validation after AI fills — wrong values submitted silently
- Screenshot on failure helps debugging but doesn't prevent incorrect submissions

### 12. No Request Timeout on `/run/status` Historical Logs
**File:** `frontend/src/App.tsx`
- Poll timeout recently fixed to 5s, but `_run_state["logs"]` deque maxlen=200 means logs overflow during long runs — early batch logs lost
- Frontend `setLogs` replaces the entire array each poll; no append-only accumulation

---

## Low

### 13. Hardcoded CORS Origins
**File:** `backend/main.py:32–37`
```python
allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"]
```
- Production deployment doesn't add the actual domain dynamically
- Should read from `ALLOWED_ORIGINS` env var

### 14. `python-jose` + `passlib` Installed — Auth Not Wired
**File:** `requirements.txt`
- JWT and password hashing libraries installed but no auth routes exist
- Dead dependency weight; creates a false impression that auth is implemented

### 15. Scheduler Not Integrated With Main App
**File:** `backend/scheduler.py`
- Runs as a completely separate process — its activity appears nowhere in the UI
- Uses its own DB session independent of the API process
- Scheduled runs can overlap if previous run takes longer than `SCHEDULER_INTERVAL_MINUTES`

### 16. `scripts/` Not Gitignored and Contain Hardcoded Test Data
**Files:** `scripts/test_apply.py`, `scripts/test_scrapers.py`
- Scripts may contain hardcoded job URLs, email addresses, or test credentials
- No `.gitignore` entry for scripts with local credentials

### 17. No Structured Logging / Correlation IDs
**File:** `backend/api/routes.py:471–475`
- `_log()` emits to both loguru and in-memory deque — no request/run correlation ID
- Multiple overlapping runs (if triggered) would produce interleaved logs with no way to separate them
