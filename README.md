# ⚡ Applyra — AI-Powered Job Application Engine

Automatically discover, score, and apply to jobs using AI. Supports LinkedIn Easy Apply, Indeed, and Glassdoor. Built with FastAPI + React + Claude/GPT-4.

---

## Features

- **Resume Parsing** — Upload PDF/DOCX; AI extracts skills, experience, education into structured JSON
- **Job Scraping** — Searches LinkedIn, Indeed, Glassdoor for recent jobs (last 7 days) matching your target roles
- **AI Matching** — Scores each job 0–100% against your resume; explains why, flags red flags
- **Cover Letter Generation** — Writes personalized, role-specific cover letters per application
- **Auto-Fill Forms** — Playwright fills out LinkedIn Easy Apply and external job forms automatically
- **Smart Filtering** — Block companies, require/exclude keywords, remote-only, salary filters
- **Daily Limit** — Hard cap on applications per day (default: 25); dry-run mode for safety
- **Dashboard** — Real-time stats, application funnel, history charts
- **Scheduler** — Runs searches automatically every N minutes in the background

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy (async), Alembic |
| Database | SQLite (dev) / PostgreSQL (prod) |
| AI | Claude claude-haiku-4-5-20251001 (Anthropic) or GPT-4o-mini (OpenAI) |
| Scraping | Playwright (Chromium), BeautifulSoup |
| Frontend | React 18, TypeScript, Tailwind CSS, Recharts |
| Scheduler | APScheduler |
| Container | Docker + Docker Compose |

---

## Quick Start

### Option A: Local Setup (Recommended)

```bash
# 1. Clone and run setup
git clone <repo> applyra
cd applyra
bash scripts/setup.sh

# 2. Add your API key to .env
nano .env
# Set: ANTHROPIC_API_KEY=sk-ant-...

# 3. Start backend
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# 4. Start frontend (new terminal)
cd frontend && npm run dev

# 5. Open http://localhost:5173
```

### Option B: Docker

```bash
cp .env.example .env
nano .env   # Add your API key

docker-compose up --build
# Open http://localhost:8000
```

---

## Setup Walkthrough

### 1. Upload Your Resume
Go to **Resume** tab → drag & drop your PDF/DOCX. AI will extract and display your skills and experience.

### 2. Create a Job Profile
Go to **Job Profiles** tab → click **New Profile**:
- Set target roles: `["Full Stack Engineer", "Software Engineer"]`
- Set locations: `["Remote", "New York"]`
- Add keywords to require/exclude
- Set minimum salary
- Toggle remote-only

### 3. Configure .env

```env
ANTHROPIC_API_KEY=sk-ant-...    # Required
LINKEDIN_EMAIL=you@email.com    # Required for Easy Apply
LINKEDIN_PASSWORD=yourpass      # Required for Easy Apply

DRY_RUN=true                    # ⚠️ Start with true! Simulate first
AUTO_APPLY_ENABLED=false        # ⚠️ Set to true only when ready
MAX_APPLICATIONS_PER_DAY=25     # Safety cap
MIN_MATCH_SCORE=0.75            # Only apply to 75%+ matches
```

### 4. Run a Search (Dry Run First!)
Go to **Dashboard** → select resume and profile → set mode to **Dry Run** → click **Start Search & Apply**.

The system will:
1. Search LinkedIn + Indeed for your target roles
2. Score each job with AI (0–100% match)
3. Generate cover letters for qualified jobs
4. **Simulate** submissions (dry run) or **actually submit** (live mode)

### 5. Review Results
- **Jobs Found** tab — browse all discovered jobs with salary, source, Easy Apply badge
- **Applications** tab — see status of every application, cover letters, match scores
- Click any application to update status (Interview / Rejected / Offer)

---

## Project Structure

```
Applyra/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── scheduler.py            # Background job scheduler
│   ├── api/
│   │   └── routes.py           # All API endpoints
│   ├── core/
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   ├── resume_parser.py    # PDF/DOCX parsing + AI extraction
│   │   └── application_engine.py  # Core orchestration logic
│   ├── ai/
│   │   └── matcher.py          # AI matching, cover letters, Q&A
│   ├── scrapers/
│   │   ├── base.py             # Abstract scraper interface
│   │   ├── linkedin_scraper.py # LinkedIn search + Easy Apply
│   │   ├── indeed_scraper.py   # Indeed search
│   │   └── glassdoor_scraper.py# Glassdoor search
│   ├── models/
│   │   └── models.py           # SQLAlchemy ORM models
│   └── db/
│       └── database.py         # Async DB session management
├── frontend/
│   └── src/
│       ├── pages/              # Dashboard, Resume, Jobs, Applications, Stats, AI Test
│       ├── components/         # Layout, shared UI
│       ├── api/client.ts       # Typed API client (axios)
│       └── store/useStore.ts   # Zustand global state
├── data/
│   └── resumes/                # Uploaded resume files
├── scripts/setup.sh            # One-command setup
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/resumes/upload` | Upload and parse resume |
| GET | `/api/resumes` | List all resumes |
| POST | `/api/profiles` | Create job profile |
| GET | `/api/jobs` | List discovered jobs |
| GET | `/api/applications` | List applications |
| PATCH | `/api/applications/{id}` | Update status |
| POST | `/api/run/search` | Trigger background search+apply |
| POST | `/api/test/match` | Test AI match score |
| GET | `/api/stats` | Application stats |
| GET | `/api/health` | System health |

API docs at `http://localhost:8000/docs`

---

## Safety & Ethics

- **Always start with `DRY_RUN=true`** to preview what would be applied
- Set `AUTO_APPLY_ENABLED=false` until you've reviewed the match quality
- Respect each platform's ToS — use responsibly and with reasonable delays
- The default `SCRAPER_DELAY_SECONDS=2.5` prevents aggressive scraping
- Applications are rate-limited to `MAX_APPLICATIONS_PER_DAY=25`

---

## Customization

### Add a new job board
1. Create `backend/scrapers/myboard_scraper.py` extending `BaseScraper`
2. Implement `search_jobs()` and `get_job_details()`
3. Add to `SCRAPERS` dict in `backend/scrapers/__init__.py`
4. Add to `scraper_map` in `backend/api/routes.py`

### Change AI model
In `.env`:
```env
AI_PROVIDER=anthropic
# Uses claude-haiku-4-5-20251001 for matching/cover letters (fast + cheap)
# Edit backend/ai/matcher.py to use claude-sonnet-4-6 for higher quality
```

---

## License

MIT
