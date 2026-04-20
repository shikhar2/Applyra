# Testing

**Analysis Date:** 2026-04-20

## Summary

**No automated test suite exists.** There are manual/dev scripts in `scripts/` but no pytest unit tests, no frontend test framework (jest/vitest), and no CI pipeline.

---

## What Exists

### Manual Dev Scripts (`scripts/`)

| File | Purpose |
|------|---------|
| `scripts/test_scrapers.py` | Run individual scrapers against live job boards, print results |
| `scripts/test_apply.py` | Manually trigger the application flow against a real job URL |
| `scripts/run_e2e_test.py` | End-to-end smoke test: search → ingest → score → apply (dry run) |

These are run by hand during development. They are **not** integrated into any CI pipeline and have no assertions — they print output for human review.

### No Automated Tests

- No `tests/` directory
- No `pytest.ini` / `setup.cfg` / `pyproject.toml` with test config
- No `*.test.ts` / `*.spec.ts` in frontend
- No `test_*.py` in backend proper
- No GitHub Actions / CI config (no `.github/` directory)

---

## Test Coverage

| Area | Coverage | Notes |
|------|---------|-------|
| API endpoints | ❌ None | No route tests |
| ApplicationEngine | ❌ None | Core orchestration untested |
| AI scoring/matching | ❌ None | Matcher untested |
| Scrapers | ⚠️ Manual only | `scripts/test_scrapers.py` — live network |
| ATS form filling | ⚠️ Manual only | `scripts/test_apply.py` — requires live browser |
| Frontend components | ❌ None | No component tests |
| Data models | ❌ None | No schema/migration tests |
| Config validation | ❌ None | Pydantic validates at startup only |

---

## Testing Patterns in Use (Informal)

**Dev workflow:**
1. Run `scripts/test_scrapers.py` with a target job board and query
2. Check console output for scraped job count and data quality
3. Run `scripts/run_e2e_test.py` with `dry_run=True` to verify full pipeline
4. Check `data/applyra.db` directly with SQLite browser for DB state

**ATS testing:**
- Navigate to a real job posting apply URL
- Run `scripts/test_apply.py` with `dry_run=True`
- Review `data/screenshots/` for failure captures

---

## Recommended Test Strategy (Not Yet Implemented)

### Backend (pytest + pytest-asyncio)

```
tests/
├── unit/
│   ├── test_matcher.py         # Mock AI client, test score thresholds
│   ├── test_application_engine.py  # Mock DB + matcher, test state transitions
│   ├── test_resume_parser.py   # Test PDF/DOCX extraction
│   └── test_dedup.py           # Test _dedup_key hash collisions
├── integration/
│   ├── test_routes.py          # FastAPI TestClient, real SQLite in-memory
│   └── test_scraper_base.py    # Test RateLimiter, ScrapedJob validation
└── conftest.py                 # Shared fixtures: async DB, mock AI client
```

### Frontend (Vitest + React Testing Library)

```
src/
└── __tests__/
    ├── Dashboard.test.tsx      # Render, mock API, test batch size selector
    ├── useStore.test.ts        # Zustand store state transitions
    └── api/client.test.ts      # Axios interceptor behavior
```

### CI (GitHub Actions — not yet created)

```yaml
# .github/workflows/test.yml
on: [push, pull_request]
jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - pytest tests/ --asyncio-mode=auto
  frontend-tests:
    steps:
      - npm run test
```

---

## Risks from Missing Tests

1. **Scraper selector rot** — Job board HTML changes break scrapers silently
2. **AI scoring threshold drift** — No regression baseline for match quality
3. **ApplicationEngine state bugs** — Concurrent batch processing race conditions unverified
4. **Daily limit bypass** — No test ensures `MAX_APPLICATIONS_PER_DAY` is respected under concurrency
5. **Database migration safety** — No schema change tests
