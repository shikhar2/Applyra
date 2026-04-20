# Directory Structure

**Analysis Date:** 2026-04-20

## Root Layout

```
AutoApply/
├── backend/                  # Python FastAPI application
│   ├── main.py               # FastAPI app factory, lifespan, static serving
│   ├── requirements.txt      # Python dependencies
│   ├── ai/                   # AI provider abstraction layer
│   │   ├── client.py         # Provider factory (Anthropic/OpenAI/Gemini/Groq/xAI)
│   │   └── matcher.py        # JobMatcher — scoring, cover letter, Q&A generation
│   ├── api/
│   │   └── routes.py         # All HTTP endpoints + background task runner
│   ├── core/
│   │   ├── application_engine.py  # Main orchestrator: ingest→score→queue→apply
│   │   ├── config.py              # Pydantic settings (env var binding)
│   │   ├── resume_parser.py       # PDF/DOCX text extraction + AI parsing
│   │   ├── tier_config.py         # Company tier classification
│   │   └── follow_up_engine.py    # Post-application follow-up scheduling
│   ├── db/
│   │   └── database.py            # Async SQLAlchemy setup, Base, session factory
│   ├── models/
│   │   └── models.py              # All ORM models + enums
│   └── scrapers/
│       ├── __init__.py            # SCRAPERS registry, BROWSER_SCRAPERS, HTTP_SCRAPERS sets
│       ├── base.py                # BaseScraper ABC, ScrapedJob dataclass, RateLimiter
│       ├── ats_applier.py         # Generic ATS form filler (Greenhouse/Lever/Workday/etc.)
│       ├── linkedin_scraper.py    # Playwright + LinkedIn Easy Apply
│       ├── indeed_scraper.py      # Playwright + stealth
│       ├── glassdoor_scraper.py   # Playwright (Cloudflare bypass)
│       ├── naukri_scraper.py      # Playwright (India market)
│       ├── dice_scraper.py        # HTTP (US tech jobs)
│       └── wellfound_scraper.py   # Playwright (startup jobs)
├── frontend/                 # React + TypeScript SPA
│   ├── src/
│   │   ├── App.tsx           # Root: routing, theme, global status poller
│   │   ├── main.tsx          # Vite entry point
│   │   ├── api/
│   │   │   └── client.ts     # Axios instance + typed API methods per domain
│   │   ├── store/
│   │   │   └── useStore.ts   # Zustand global store (running state, logs, stats)
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx     # Command center: search trigger, console
│   │   │   ├── Applications.tsx  # Application list + status management
│   │   │   ├── Jobs.tsx          # Scraped job browser
│   │   │   ├── Resume.tsx        # Resume upload + management
│   │   │   ├── Profiles.tsx      # Job profile CRUD
│   │   │   ├── Stats.tsx         # Analytics charts
│   │   │   ├── Kanban.tsx        # Application pipeline board
│   │   │   ├── ReviewQueue.tsx   # HITL approval queue
│   │   │   ├── AITest.tsx        # Match testing sandbox
│   │   │   ├── InterviewPrep.tsx # AI interview coaching
│   │   │   └── ResumeTailor.tsx  # AI resume tailoring
│   │   └── components/
│   │       └── Layout.tsx        # Sidebar nav, theme toggle
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
├── scripts/                  # Dev/test utilities (not production)
│   ├── test_scrapers.py      # Manual scraper smoke tests
│   ├── test_apply.py         # Manual application flow test
│   └── run_e2e_test.py       # End-to-end test script
├── data/                     # Runtime data (gitignored)
│   ├── applyra.db            # SQLite database
│   ├── resumes/              # Uploaded resume files
│   ├── session/              # LinkedIn browser session cookies
│   └── screenshots/          # Failure screenshots from ATS applier
├── docker-compose.yml        # 3-service stack: applyra + scheduler + redis
├── Dockerfile                # Production image (Render deploy)
├── Dockerfile.full           # Docker Compose image (includes scheduler)
├── render.yaml               # Render.com deployment manifest
└── .env                      # Local secrets (gitignored)
```

## Module Boundaries

| Module | Owns | Imports From |
|--------|------|-------------|
| `backend/api/routes.py` | HTTP layer, background task state | core, models, ai, scrapers |
| `backend/core/application_engine.py` | Orchestration pipeline | ai/matcher, models, scrapers/ats_applier |
| `backend/scrapers/` | Job discovery + form submission | base only (no circular deps) |
| `backend/ai/` | LLM calls only | config only |
| `backend/models/` | ORM definitions | db/database only |
| `frontend/src/api/` | HTTP → backend bridge | none |
| `frontend/src/store/` | Global client state | none |
| `frontend/src/pages/` | UI features | api/, store/, components/ |

## Naming Conventions

**Python:**
- Files: `snake_case.py`
- Classes: `PascalCase` (e.g., `ApplicationEngine`, `LinkedInScraper`)
- Functions/variables: `snake_case`
- Private helpers: `_prefix` (e.g., `_run_search_task`, `_score_one`)
- Pydantic models: `PascalCase` suffixed with `Create`/`Request`/`Update`
- Enums: `PascalCase` with `UPPER_CASE` values

**TypeScript/React:**
- Components: `PascalCase.tsx`
- Hooks: `use` prefix + camelCase (e.g., `useStore`)
- API namespaces: `camelCase` + `Api` suffix (e.g., `resumeApi`, `jobApi`)
- Store actions: `set` prefix (e.g., `setIsRunning`, `setLogs`)

## Key Entry Points

| Trigger | Entry Point |
|---------|-------------|
| HTTP request | `backend/main.py` → `backend/api/routes.py` |
| Frontend app | `frontend/src/main.tsx` → `frontend/src/App.tsx` |
| Scheduled run | `backend/scheduler.py` (standalone process) |
| Docker prod | `Dockerfile` → `uvicorn backend.main:app` |
| Docker scheduler | `Dockerfile.full` → `python -m backend.scheduler` |

## How Frontend Connects to Backend

- In **development**: Vite dev server proxies `/api/*` to `localhost:8000`
- In **production**: FastAPI serves `frontend/dist/` as static files, SPA catch-all at `/{full_path:path}`
- No separate frontend deploy needed — single container serves both
