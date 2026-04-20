# External Integrations

**Analysis Date:** 2026-04-20

## AI / LLM Providers

All wired through `backend/ai/client.py` — returns a provider-specific async client based on `AI_PROVIDER` env var.

| Provider | Env Var | Client | Default Model | Use |
|----------|---------|--------|--------------|-----|
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | `anthropic.AsyncAnthropic` | configurable | Scoring, cover letters |
| OpenAI (GPT) | `OPENAI_API_KEY` | `openai.AsyncOpenAI` | configurable | Scoring, cover letters |
| Google Gemini | `GEMINI_API_KEY` | `google.generativeai` | `gemini-1.5-flash` | **Default provider** |
| Groq | `GROQ_API_KEY` | `groq.AsyncGroq` | configurable | Simpler tasks (fast/cheap) |
| xAI (Grok) | `XAI_API_KEY` | `openai.AsyncOpenAI` (xAI base URL) | configurable | Alternative |

**Two-tier AI routing** (`backend/ai/matcher.py`):
- **Complex tasks** (job scoring, deep analysis): primary `AI_PROVIDER`
- **Simple tasks** (cover letter, Q&A answers): `SIMPLER_AI_PROVIDER` (default: `groq`) if key available, else fallback to primary

**AI operations:**
- `score_match(resume, job)` → `(float 0–1, dict analysis)` — quick filter pass
- `deep_score_match(resume, job)` → `(float, 7-block analysis dict)` — HITL queue
- `generate_cover_letter(resume, job, highlights)` → `str` — 250-word, 3-paragraph
- `answer_question(resume, question, field_type)` → `str|bool|int` — form Q&A
- `ai_fill_form_fields(candidate, job, fields)` → `dict` — ATS generic form fill

---

## Job Board Scrapers

Defined in `backend/scrapers/`. All implement `BaseScraper.search_jobs(query, location, max_results, days)`.

| Board | Class | Method | Auth Required | Notes |
|-------|-------|--------|--------------|-------|
| LinkedIn | `LinkedInScraper` | Playwright | Optional (for Easy Apply) | `LINKEDIN_EMAIL` / `LINKEDIN_PASSWORD` |
| Indeed | `IndeedScraper` | Playwright + stealth | No | `playwright-stealth` for bot detection |
| Glassdoor | `GlassdoorScraper` | Playwright | No | Login modal dismissal built in |
| Naukri | `NaukriScraper` | Playwright | Optional | `NAUKRI_EMAIL` / `NAUKRI_PASSWORD` for applying |
| Dice | `DiceScraper` | HTTP (httpx) | No | Only pure HTTP scraper |
| Wellfound | `WellfoundScraper` | Playwright | No | Startup/angel jobs |

**Concurrency control** (`backend/api/routes.py`):
- Browser scrapers: `asyncio.Semaphore(MAX_BROWSER_SCRAPERS)` — default 2 concurrent browsers
- HTTP scrapers: no semaphore (rate-limited internally)

**Rate limiting** (`backend/scrapers/base.py` → `RateLimiter`):
- Base delay: `SCRAPER_DELAY_SECONDS` (default 1.0s)
- Adaptive: exponential backoff on HTTP 429/403/503
- Jitter: ±20% to desynchronize parallel requests
- Max delay: 60s

---

## ATS Platforms (Application Submission)

`backend/scrapers/ats_applier.py` — `ATSApplier` class.

Detected from apply URL domain:

| ATS | Domain Signal | Handler |
|-----|-------------|---------|
| Greenhouse | `greenhouse.io`, `boards.greenhouse` | `_apply_greenhouse()` |
| Lever | `jobs.lever.co` | `_apply_lever()` |
| Workday | `myworkdayjobs.com`, `wd3.myworkday` | `_apply_workday()` |
| Ashby | `jobs.ashbyhq.com` | `_apply_ashby()` |
| BambooHR | `bamboohr.com` | `_apply_bamboo()` |
| Taleo | `taleo.net` | `_apply_taleo()` |
| Generic | (fallback) | `_apply_generic()` |

All handlers:
1. Navigate to apply URL
2. Upload resume file
3. Fill standard fields (name, email, phone, LinkedIn, GitHub)
4. AI-scan remaining visible form fields → fill with `human_type()` / `human_click()`
5. Submit → verify success signals ("thank you", "application received")
6. Retry up to `MAX_RETRIES` (default 3) with exponential backoff

---

## Database

| Setting | Default | Notes |
|---------|---------|-------|
| Driver | `sqlite+aiosqlite` | Async SQLite for local/dev |
| Production | `asyncpg` (PostgreSQL) | Via `DATABASE_URL` env var on Render |
| ORM | SQLAlchemy 2.0 async | `backend/db/database.py` |
| Migrations | Alembic | `alembic/` directory |
| Connection | `AsyncSessionLocal` session factory | Per-request via FastAPI `Depends` |

Tables: `resumes`, `job_profiles`, `jobs`, `applications`, `job_searches`, `daily_stats`, `follow_ups`

---

## Session / Caching / Queue

| Service | Usage | Config |
|---------|-------|--------|
| Redis | Celery task queue (configured, not yet fully wired) | `REDIS_URL` (default: `redis://localhost:6379/0`) |
| Celery | Background workers (installed, not primary path) | `celery==5.4.0` in requirements |
| APScheduler | Autonomous scheduled search | `backend/scheduler.py` — interval: `SCHEDULER_INTERVAL_MINUTES` (default 60) |
| Browser sessions | LinkedIn/Naukri login cookies | Stored in `data/session/` and `data/session_naukri/` |

**Note:** The primary background task path uses FastAPI `BackgroundTasks` (not Celery). Celery/Redis are installed for future scaling but unused in the main flow.

---

## Email Notifications

| Setting | Purpose |
|---------|---------|
| `SMTP_HOST`, `SMTP_PORT` | SMTP server |
| `SMTP_USER`, `SMTP_PASSWORD` | Auth |
| `NOTIFY_EMAIL` | Recipient for alerts |
| Library | `aiosmtplib==3.0.2` (async) |

Used by `backend/core/follow_up_engine.py` for post-application follow-up emails.

---

## Deployment Targets

| Target | Config File | Notes |
|--------|------------|-------|
| Local dev | `.env` + `uvicorn` | `python -m backend.main` |
| Docker | `docker-compose.yml` | 3 services: app + scheduler + redis |
| Render.com | `render.yaml` | Free tier, PostgreSQL, Docker deploy |
| Oracle Cloud | (separate config) | Free tier VM |

---

## Proxy Support

- `PROXY_URL` env var → passed to Playwright browser contexts
- Used to rotate IPs for scraping (not enabled by default)
