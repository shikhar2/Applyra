# Coding Conventions

**Analysis Date:** 2026-04-19

## Python Naming Patterns

**Files:**
- `snake_case.py` — all backend modules use snake_case: `application_engine.py`, `resume_parser.py`, `dice_scraper.py`
- Scraper modules are suffixed `_scraper.py`; AI modules are flat names under `backend/ai/`

**Classes:**
- `PascalCase` — `ApplicationEngine`, `JobMatcher`, `BaseScraper`, `DiceScraper`, `ResumeTailor`
- Pydantic schemas in `backend/api/routes.py` are `PascalCase` with descriptive suffixes: `JobProfileCreate`, `ApplicationStatusUpdate`, `RunSearchRequest`

**Functions and Methods:**
- `snake_case` for all functions and methods: `ingest_jobs`, `queue_applications`, `score_match`, `generate_cover_letter`
- Private helpers prefixed with `_`: `_dedup_key`, `_score_one`, `_scrape_one`, `_log`, `_trim`, `_call_ai`, `_safe_get`
- Background task functions prefixed with `_run_`: `_run_search_task`, `_run_apply_task`

**Variables:**
- `snake_case` for all variables
- Module-level singletons: `settings` (from `backend/core/config.py`), `router` in `backend/api/routes.py`
- Module-level state dicts: `_run_state` (prefixed with `_` to signal internal use)
- Constants: `UPPERCASE` — `MATCH_PROMPT`, `COVER_LETTER_PROMPT`, `DEEP_ANALYSIS_PROMPT` in `backend/ai/matcher.py`

**Enums:**
- Class names `PascalCase`, values `UPPERCASE`: `ApplicationStatus.PENDING`, `JobSource.LINKEDIN` in `backend/models/models.py`
- Enums inherit from `(str, enum.Enum)` so values serialize as plain strings

## TypeScript/React Naming Patterns

**Files:**
- Pages: `PascalCase.tsx` — `Dashboard.tsx`, `Applications.tsx`, `ReviewQueue.tsx`
- Components: `PascalCase.tsx` — `Layout.tsx`
- Store: `use` prefix, camelCase file — `useStore.ts`
- API client: `client.ts` (flat, no prefix)

**Components:**
- `PascalCase` function components: `StatCard`, `StatusBadge`, `MatchScoreCircle`, `FollowUpTimeline`
- Sub-components are defined as standalone functions within the same file as their parent page (not extracted to separate files)
- Props are typed via inline object types: `{ label: string; value: number; icon: any }`

**Variables and Functions:**
- `camelCase` for variables: `selectedResume`, `loadData`, `handleRun`, `toggleSource`
- Event handlers prefixed with `handle`: `handleRun`, `handleSend`
- Toggle functions prefixed with `toggle`: `toggleSource`, `toggleTheme`
- Boolean state variables without `is` prefix: `running`, `loading`, `acting`

**Constants:**
- `SCREAMING_SNAKE_CASE` for module-level config objects: `STAT_CONFIGS`, `STATUS_CONFIG`, `REGION_STYLE`, `FOLLOWUP_TYPE_LABEL`, `FOLLOWUP_STATUS_COLOR`, `EMPTY_PROFILE`

## Python Code Style

**Docstrings:**
- Module-level docstrings with triple quotes on all backend modules
- Method docstrings are terse one-liners: `"""Upload and parse a resume (PDF or DOCX)."""`
- Internal helpers often omit docstrings
- Docstrings describe the action, not the return value

**Section Dividers:**
- Routes are grouped by entity with `# ----` comment dividers with labels: `# Resume Endpoints`, `# Application Endpoints`
- Long comment separators: `# ================================================================== #`
- Class method sections use short `# ── Label ─────` headers inside classes

**Line Style:**
- Logic is sometimes compressed onto single lines in performance-critical sections:
  ```python
  for app in r.applications:
      if app.tailored_resume_path and os.path.exists(app.tailored_resume_path):
  ```
- `application_engine.py` uses semicolons to chain related ops on one line:
  ```python
  self.db.add(job); applied_keys.add(dkey); new_count += 1
  ```
  This is an inconsistency — most code does not use semicolons.

**Type Hints:**
- All function signatures use type hints: `async def ingest_jobs(self, scraped_jobs: list[ScrapedJob]) -> int:`
- `Optional[T]` from `typing` for nullable fields
- `Tuple`, `Dict`, `List`, `Any` imported from `typing` in older modules; newer modules use built-in generics `list[T]`, `dict`, `tuple`

## TypeScript Code Style

**Strict mode:** Enabled in `frontend/tsconfig.json` (`"strict": true`), but `noUnusedLocals` and `noUnusedParameters` are both `false`.

**`any` usage:** Widespread and intentional — API response shapes are typed as `any` throughout all page files. No shared response type interfaces exist.

**Interface vs type:** Interfaces are used for state shape in Zustand store (`interface AppState`, `interface LogEntry` in `frontend/src/store/useStore.ts`). Inline object types are used everywhere else.

**JSX patterns:**
- Self-closing tags for all void elements
- Ternary expressions used for conditional rendering, not `&&` short-circuit when the falsy case has JSX implications

## Import Organization

**Python — order:**
1. Standard library (`asyncio`, `os`, `re`, `hashlib`, `datetime`)
2. Third-party (`fastapi`, `sqlalchemy`, `loguru`, `playwright`, `httpx`)
3. Local imports (`from backend.xxx import ...`)
- No blank line between stdlib and third-party in some files (minor inconsistency)
- Lazy imports inside functions are used for optional heavy deps: `from backend.ai.resume_tailor import ResumeTailor` inside route handlers

**TypeScript — order:**
1. React (`import React, { ... } from 'react'`)
2. API clients (`from '../api/client'`)
3. Third-party UI libs (`toast`, `motion`, `lucide-react`)
4. Internal store (`from '../store/useStore'`)
- No path aliases configured; all imports use relative paths (`../api/client`, `../store/useStore`)

## Logging

**Framework:** `loguru` — used everywhere in the backend. Never `print()` or stdlib `logging`.

**Import:** `from loguru import logger` at the top of each module that logs.

**Log levels used:**
- `logger.info(...)` — normal operation milestones
- `logger.warning(...)` — recoverable issues (login blocked, rate limits, missing files)
- `logger.error(...)` — operational failures (AI call failures, DB misses)
- `logger.exception(e)` — used after `except` blocks to capture full traceback: `logger.exception(e)` in `_run_search_task`
- `logger.success(...)` — used on positive terminal conditions: `logger.success("Naukri login successful")`

**In-memory log sink:** `backend/api/routes.py` maintains `_run_state["logs"]` (a `deque(maxlen=200)`) to stream log lines to the frontend. The `_log()` helper writes to both loguru and this ring buffer:
```python
def _log(msg: str, level: str = "info"):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    _run_state["logs"].append({"ts": ts, "level": level, "msg": msg})
    getattr(logger, level)(msg)
```

**Frontend:** `console.error()` used only in `App.tsx` for background polling failures. Pages use `toast` (react-hot-toast) for user-facing errors — no structured logging.

## Async Patterns

**Python:**
- All route handlers are `async def` using FastAPI's native async support
- Database calls use `await db.execute(...)`, `await db.commit()`, `await db.refresh(...)`
- Background tasks use `BackgroundTasks.add_task()` from FastAPI — the task function creates its own `AsyncSessionLocal` session since the request session is closed
- Parallelism uses `asyncio.gather()` heavily:
  ```python
  scrape_results = await asyncio.gather(*scrape_tasks)
  await asyncio.gather(*[self._prepare_application(app, resume) for app in pending])
  ```
- `asyncio.Semaphore` used for concurrency control: `ai_sem = asyncio.Semaphore(settings.MAX_AI_CONCURRENCY)` and `browser_sem = asyncio.Semaphore(settings.MAX_BROWSER_SCRAPERS)`
- `asyncio.Queue` used for worker pool pattern in `process_pending_applications` in `backend/core/application_engine.py`
- `asyncio.Lock` guards shared counters in multi-worker sections
- `return_exceptions=True` passed to `asyncio.gather` in `_prepare_application` to prevent one failure killing all parallel coroutines

**TypeScript:**
- All API calls are `async/await` inside `async function` or `useEffect` with inner async function
- Parallel data loading uses `Promise.all`:
  ```typescript
  const [s, h, r, p, sc] = await Promise.all([statsApi.get(), statsApi.health(), ...])
  ```
- Errors are caught with `catch (e: any)` and surfaced via `toast.error(e.message)`
- Silent catch blocks (empty `catch {}` or `catch { /* silent */ }`) are used where failures should not interrupt UX

## Error Handling

**Python — routes:**
- `HTTPException(status_code, detail)` for all user-facing errors: `raise HTTPException(404, "Resume not found")`
- Error codes used: 400, 404, 422, 503
- Try/except wraps file I/O and AI calls; failures logged with `logger.warning` or `logger.error` before re-raising or returning fallback
- Background tasks catch all exceptions at top level: `except Exception as e: _log(f"...: {e}", "error")` with `finally: _run_state["running"] = False`
- `get_db()` dependency in `backend/db/database.py` auto-rolls-back on exception:
  ```python
  except Exception:
      await session.rollback()
      raise
  ```

**Python — scrapers:**
- `try/except Exception as e` around all external HTTP and browser calls
- Returns empty list `[]` on failure rather than raising
- Rate limiter `failure()` is called on non-200 responses to trigger exponential backoff

**TypeScript:**
- `catch (e: any)` with `toast.error(e.message)` in all user-triggered async handlers
- The axios response interceptor in `frontend/src/api/client.ts` normalizes errors:
  ```typescript
  const message = error.response?.data?.detail || error.message || 'An error occurred'
  return Promise.reject(new Error(message))
  ```
- Background polling failures are caught silently with `console.error()`

## State Management (Zustand)

**Store location:** `frontend/src/store/useStore.ts`

**Pattern:** Single flat store, no slices. All state and setters in one `create<AppState>()` call.

**State shape:**
- `activeResume`, `activeProfile` — globally selected entities (used as defaults across pages)
- `isRunning`, `logs`, `runStats` — background job status mirrored from backend polling in `App.tsx`

**Usage:** Components select only what they need via selector functions:
```typescript
const running = useStore(state => state.isRunning)
const setLogs = useStore(state => state.setLogs)
```

**Local vs global state:** Pages keep their own UI state (`useState`) for list data, filters, and form values. Only cross-page shared state (run status, logs) lives in Zustand.

## API Client Patterns

**File:** `frontend/src/api/client.ts`

**Structure:** A named default `axios` instance (`api`) with interceptors, plus named export objects grouping related methods:
```typescript
export const resumeApi = { upload, list, get, delete }
export const profileApi = { create, list, update }
export const jobApi = { list, get }
export const applicationApi = { list, update }
export const automationApi = { runSearch, runApply, testMatch }
export const statsApi = { get, history, health }
export const followupApi = { list, send, skip }
```

**Base config:**
- `baseURL: '/api'` — proxied to `http://localhost:8000` in dev via `vite.config.ts`
- Default timeout: `60000ms` (60s); extended to `120000ms` for resume upload

**Error normalization:** Response interceptor extracts `error.response?.data?.detail` (FastAPI error format) before rejecting.

**Return value:** All methods return the raw `axios` response — callers access `.data` directly: `r.data`, `s.data`.

## Component Structure

**Pattern:** All page-level logic and sub-components are co-located in a single file per page.

**Typical page file anatomy (`frontend/src/pages/*.tsx`):**
1. Imports
2. Module-level config constants (`STATUS_CONFIG`, `EMPTY_PROFILE`, etc.)
3. Small sub-components (e.g., `StatusBadge`, `MatchScoreCircle`) — not exported, only used locally
4. Main default-exported page component with `useEffect` data loading, `useState` for local state, handler functions, return JSX

**Animation:** `framer-motion` (`motion.div`, `AnimatePresence`) wraps nearly every major UI element. Standard entry animation:
```tsx
<motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.08 }}>
```

**Toast notifications:** `react-hot-toast` used for all success/error feedback. `toast.success(...)` and `toast.error(...)` called directly in handlers.

**Styling:** Tailwind CSS utility classes. CSS custom properties (`var(--text-primary)`, `var(--card-bg)`, `var(--accent-primary)`) used for theme-aware colors. Custom utility classes (`glass`, `btn-primary`, `input-glass`) defined in `frontend/src/index.css`.

**Icons:** `lucide-react` exclusively. Icons are typed as `any` when passed as props.

---

*Convention analysis: 2026-04-19*
