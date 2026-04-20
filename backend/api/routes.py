"""
FastAPI routes for Applyra.
"""
import asyncio
import os
import shutil
from collections import deque
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from loguru import logger

# ── In-memory run state (single-user app) ─────────────────────────────────
_run_state: dict = {
    "running": False,
    "logs": deque(maxlen=200),  # ring buffer — last 200 log lines
    "stats": {},
}

from backend.db.database import get_db
from backend.models.models import (
    Resume, Job, Application, JobProfile, DailyStats,
    ApplicationStatus, FollowUp,
)
from backend.core.config import settings
from backend.core.resume_parser import extract_text, parse_resume_with_ai
from backend.ai.matcher import JobMatcher
from backend.core.application_engine import ApplicationEngine

router = APIRouter()

# ------------------------------------------------------------------ #
#  Pydantic Schemas
# ------------------------------------------------------------------ #

class JobProfileCreate(BaseModel):
    name: str
    target_roles: List[str]
    target_locations: List[str] = ["Remote"]
    remote_only: bool = False
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    salary_currency: str = "USD"
    min_years_experience: Optional[int] = None
    max_years_experience: Optional[int] = None
    experience_levels: List[str] = ["mid", "senior"]
    company_size: List[str] = []
    excluded_companies: List[str] = []
    required_keywords: List[str] = []
    excluded_keywords: List[str] = []

class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    notes: Optional[str] = None

class RunSearchRequest(BaseModel):
    profile_id: int
    resume_id: int
    sources: List[str] = ["linkedin", "indeed", "dice", "wellfound"]
    dry_run: bool = True
    days: int = 7
    batch_size: int = 20

class MatchTestRequest(BaseModel):
    resume_id: int
    job_description: str
    job_title: str = "Software Engineer"
    company: str = "Test Company"

# ------------------------------------------------------------------ #
#  Dependency: AI client
# ------------------------------------------------------------------ #

from backend.ai.client import get_ai_client


# ------------------------------------------------------------------ #
#  Resume Endpoints
# ------------------------------------------------------------------ #

@router.post("/resumes/upload", tags=["resumes"])
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload and parse a resume (PDF or DOCX)."""
    if not file.filename.lower().endswith((".pdf", ".docx", ".doc", ".txt")):
        raise HTTPException(400, "Unsupported file type. Use PDF, DOCX, or TXT.")

    # Save file
    os.makedirs("data/resumes", exist_ok=True)
    file_path = f"data/resumes/{file.filename}"
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Extract text
    try:
        text = extract_text(file_path)
    except Exception as e:
        raise HTTPException(422, f"Could not parse file: {e}")

    # AI parse
    ai_client = get_ai_client()
    parsed = {}
    if ai_client:
        parsed = await parse_resume_with_ai(text, ai_client, provider=settings.AI_PROVIDER)
    else:
        from backend.core.resume_parser import basic_parse
        parsed = basic_parse(text)

    resume = Resume(
        name=file.filename,
        file_path=file_path,
        content_text=text,
        parsed_data=parsed,
        is_active=True,
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    return {
        "id": resume.id,
        "name": resume.name,
        "parsed": parsed,
        "message": "Resume uploaded and parsed successfully",
    }


@router.get("/resumes", tags=["resumes"])
async def list_resumes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Resume).order_by(desc(Resume.created_at)))
    resumes = result.scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "is_active": r.is_active,
            "created_at": r.created_at,
            "parsed_data": r.parsed_data or {},
        }
        for r in resumes
    ]


@router.get("/resumes/{resume_id}", tags=["resumes"])
async def get_resume(resume_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Resume not found")
    return {"id": r.id, "name": r.name, "parsed_data": r.parsed_data}


@router.delete("/resumes/{resume_id}", tags=["resumes"])
async def delete_resume(resume_id: int, db: AsyncSession = Depends(get_db)):
    # Load resume and its applications to clean up files
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Resume)
        .where(Resume.id == resume_id)
        .options(selectinload(Resume.applications))
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Resume not found")

    # 1. Delete tailored resumes from disk for all applications
    for app in r.applications:
        if app.tailored_resume_path and os.path.exists(app.tailored_resume_path):
            try:
                os.remove(app.tailored_resume_path)
            except Exception as e:
                logger.warning(f"Failed to delete tailored resume {app.tailored_resume_path}: {e}")

    # 2. Delete the original resume file from disk
    if r.file_path and os.path.exists(r.file_path):
        try:
            os.remove(r.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete resume file {r.file_path}: {e}")

    # 3. Delete from DB (cascades to applications due to model configuration)
    await db.delete(r)
    await db.commit()

    return {"message": "Resume and associated applications deleted successfully"}


# ------------------------------------------------------------------ #
#  Job Profile Endpoints
# ------------------------------------------------------------------ #

@router.post("/profiles", tags=["profiles"])
async def create_profile(body: JobProfileCreate, db: AsyncSession = Depends(get_db)):
    profile = JobProfile(**body.model_dump())
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return {"id": profile.id, "name": profile.name, "message": "Profile created"}


@router.get("/profiles", tags=["profiles"])
async def list_profiles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(JobProfile).where(JobProfile.is_active == True))
    profiles = result.scalars().all()
    return [
        {
            "id": p.id, "name": p.name,
            "target_roles": p.target_roles,
            "target_locations": p.target_locations,
            "remote_only": p.remote_only,
            "min_salary": p.min_salary,
            "max_salary": p.max_salary,
            "salary_currency": p.salary_currency or "USD",
            "min_years_experience": p.min_years_experience,
            "max_years_experience": p.max_years_experience,
            "experience_levels": p.experience_levels,
            "company_size": p.company_size,
            "excluded_companies": p.excluded_companies,
            "required_keywords": p.required_keywords,
            "excluded_keywords": p.excluded_keywords,
        }
        for p in profiles
    ]


@router.put("/profiles/{profile_id}", tags=["profiles"])
async def update_profile(
    profile_id: int, body: JobProfileCreate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(JobProfile).where(JobProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Profile not found")
    for k, v in body.model_dump().items():
        setattr(profile, k, v)
    await db.commit()
    return {"message": "Profile updated"}


# ------------------------------------------------------------------ #
#  Job Endpoints
# ------------------------------------------------------------------ #

@router.get("/jobs", tags=["jobs"])
async def list_jobs(
    source: Optional[str] = None,
    remote: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Job)
    if source:
        stmt = stmt.where(Job.source == source)
    if remote is not None:
        stmt = stmt.where(Job.remote == remote)
    if search:
        stmt = stmt.where(Job.title.ilike(f"%{search}%") | Job.company.ilike(f"%{search}%"))
    stmt = stmt.order_by(desc(Job.discovered_at)).offset(offset).limit(limit)
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    return [
        {
            "id": j.id, "title": j.title, "company": j.company,
            "location": j.location, "remote": j.remote, "source": j.source,
            "url": j.url, "salary_min": j.salary_min, "salary_max": j.salary_max,
            "easy_apply": j.easy_apply, "discovered_at": j.discovered_at,
        }
        for j in jobs
    ]


@router.get("/jobs/{job_id}", tags=["jobs"])
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "id": job.id, "title": job.title, "company": job.company,
        "location": job.location, "description": job.description,
        "url": job.url, "apply_url": job.apply_url,
        "remote": job.remote, "easy_apply": job.easy_apply,
        "salary_min": job.salary_min, "salary_max": job.salary_max,
        "source": job.source, "posted_at": job.posted_at,
    }


# ------------------------------------------------------------------ #
#  Application Endpoints
# ------------------------------------------------------------------ #

@router.get("/applications", tags=["applications"])
async def list_applications(
    status: Optional[str] = None,
    resume_id: Optional[int] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Application, Job, Resume).join(Job).join(Resume)
    if status:
        stmt = stmt.where(Application.status == status)
    if resume_id:
        stmt = stmt.where(Application.resume_id == resume_id)
    stmt = stmt.order_by(desc(Application.created_at)).offset(offset).limit(limit)
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "id": app.id,
            "status": app.status,
            "match_score": app.match_score,
            "applied_at": app.applied_at,
            "cover_letter": app.cover_letter,
            "match_explanation": app.match_explanation,
            "deep_analysis": app.deep_analysis,
            "is_top_tier": bool(app.is_top_tier),
            "has_tailored_resume": bool(app.tailored_resume_path),
            "job": {"id": job.id, "title": job.title, "company": job.company,
                    "url": job.url, "source": job.source},
            "resume": {"id": resume.id, "name": resume.name},
        }
        for app, job, resume in rows
    ]


@router.get("/applications/review-queue", tags=["applications"])
async def get_review_queue(
    resume_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Return all applications awaiting human review (HITL queue)."""
    stmt = (
        select(Application, Job, Resume)
        .join(Job).join(Resume)
        .where(Application.status == ApplicationStatus.REVIEW)
        .order_by(Application.match_score.desc())
    )
    if resume_id:
        stmt = stmt.where(Application.resume_id == resume_id)
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "id": app.id,
            "status": app.status,
            "match_score": app.match_score,
            "match_explanation": app.match_explanation,
            "deep_analysis": app.deep_analysis,
            "is_top_tier": bool(app.is_top_tier),
            "has_tailored_resume": bool(app.tailored_resume_path),
            "job": {
                "id": job.id, "title": job.title, "company": job.company,
                "url": job.url, "source": job.source,
                "location": job.location, "remote": job.remote,
                "salary_min": job.salary_min, "salary_max": job.salary_max,
            },
            "resume": {"id": resume.id, "name": resume.name},
        }
        for app, job, resume in rows
    ]


@router.post("/applications/{app_id}/approve", tags=["applications"])
async def approve_review(app_id: int, db: AsyncSession = Depends(get_db)):
    """Approve a HITL-review application → moves to pending for next apply run."""
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(404, "Application not found")
    if app.status != ApplicationStatus.REVIEW:
        raise HTTPException(400, "Application is not in review status")
    app.status = ApplicationStatus.PENDING
    await db.commit()
    return {"message": "Approved — queued for next apply run"}


@router.post("/applications/{app_id}/skip", tags=["applications"])
async def skip_review(app_id: int, db: AsyncSession = Depends(get_db)):
    """Skip a HITL-review application → moves to skipped."""
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(404, "Application not found")
    app.status = ApplicationStatus.SKIPPED
    await db.commit()
    return {"message": "Skipped"}


@router.post("/applications/retry-failed", tags=["applications"])
async def retry_failed_applications(db: AsyncSession = Depends(get_db)):
    """Reset all failed applications back to pending so the next run retries them."""
    result = await db.execute(
        select(Application).where(Application.status == ApplicationStatus.FAILED)
    )
    failed = result.scalars().all()
    count = len(failed)
    for app in failed:
        app.status = ApplicationStatus.PENDING
    await db.commit()
    return {"message": f"Reset {count} failed applications to pending", "count": count}


@router.patch("/applications/{app_id}", tags=["applications"])
async def update_application(
    app_id: int, body: ApplicationStatusUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(404, "Application not found")
    app.status = body.status
    if body.notes:
        app.notes = body.notes
    await db.commit()
    return {"message": "Updated", "status": app.status}


@router.get("/applications/{app_id}/tailored-resume", tags=["applications"])
async def download_tailored_resume(app_id: int, db: AsyncSession = Depends(get_db)):
    """Download the LaTeX-generated tailored resume PDF for a top-tier application."""
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(404, "Application not found")
    if not app.tailored_resume_path or not os.path.exists(app.tailored_resume_path):
        raise HTTPException(404, "No tailored resume found for this application")
    return FileResponse(
        app.tailored_resume_path,
        media_type="application/pdf",
        filename=f"tailored_resume_app_{app_id}.pdf",
    )


# ------------------------------------------------------------------ #
#  Run / Automation Endpoints
# ------------------------------------------------------------------ #

@router.post("/run/search", tags=["automation"])
async def run_search(
    body: RunSearchRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger a background job search and queueing pass."""
    if _run_state["running"]:
        return {"message": "Already running", "dry_run": body.dry_run}
    _run_state["running"] = True
    _run_state["logs"].clear()
    _run_state["stats"] = {}
    background_tasks.add_task(_run_search_task, body)
    return {"message": "Job search started in background", "dry_run": body.dry_run}


@router.get("/run/status", tags=["automation"])
async def run_status():
    """Poll this to get live progress during a search run."""
    return {
        "running": _run_state["running"],
        "logs": list(_run_state["logs"]),
        "stats": _run_state["stats"],
    }


def _log(msg: str, level: str = "info"):
    """Emit a log line to both loguru and the in-memory run state."""
    ts = datetime.utcnow().strftime("%H:%M:%S")
    _run_state["logs"].append({"ts": ts, "level": level, "msg": msg})
    getattr(logger, level)(msg)


async def _run_search_task(body: RunSearchRequest):
    from backend.scrapers import SCRAPERS, BROWSER_SCRAPERS, HTTP_SCRAPERS
    from backend.db.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            profile_result = await db.execute(select(JobProfile).where(JobProfile.id == body.profile_id))
            profile = profile_result.scalar_one_or_none()
            resume_result = await db.execute(select(Resume).where(Resume.id == body.resume_id))
            resume = resume_result.scalar_one_or_none()

            if not profile or not resume:
                _log("Profile or resume not found", "error")
                return

            _log(f"Starting search for profile: {profile.name}")
            _log(f"Sources: {', '.join(body.sources)} | Dry run: {body.dry_run}")

            ai_client = get_ai_client()
            if not ai_client:
                _log(f"No AI API key set for provider '{settings.AI_PROVIDER}'. Set it in .env.", "error")
                return

            matcher = JobMatcher(ai_client, settings.AI_PROVIDER)
            engine = ApplicationEngine(db, matcher, ai_client, log_fn=_log)

            cfg = {"delay": settings.SCRAPER_DELAY_SECONDS}
            browser_sem = asyncio.Semaphore(settings.MAX_BROWSER_SCRAPERS)

            async def _scrape_one(source, role, location):
                if source not in SCRAPERS:
                    _log(f"Unknown scraper: {source}", "warning")
                    return []
                scraper_cls = SCRAPERS[source]
                try:
                    _log(f"Searching {source}: '{role}' in '{location}'...")
                    if source in BROWSER_SCRAPERS:
                        async with browser_sem:
                            async with scraper_cls(cfg) as scraper:
                                jobs = await scraper.search_jobs(role, location, max_results=30, days=body.days)
                    else:
                        scraper = scraper_cls(cfg)
                        jobs = await scraper.search_jobs(role, location, max_results=30, days=body.days)
                    _log(f"  {source}: found {len(jobs)} jobs for '{role}' in '{location}'")
                    return jobs
                except Exception as e:
                    _log(f"  {source} failed for '{role}' in '{location}': {e}", "error")
                    return []

            scrape_tasks = [
                _scrape_one(source, role, location)
                for source in body.sources
                for role in (profile.target_roles or ["Software Engineer"])
                for location in (profile.target_locations or ["Remote"])
            ]
            scrape_results = await asyncio.gather(*scrape_tasks)
            all_scraped = [job for batch in scrape_results for job in batch]

            batch_size = max(1, body.batch_size or settings.SEARCH_BATCH_SIZE)
            total_batches = max(1, (len(all_scraped) + batch_size - 1) // batch_size)
            _log(f"Total scraped: {len(all_scraped)} jobs — processing in {total_batches} batches of {batch_size}")

            dry = not (not body.dry_run and settings.AUTO_APPLY_ENABLED)
            if dry:
                _log("Dry run mode — simulating applications (not submitting)")
            else:
                _log("LIVE mode — submitting applications now!")

            new_count = queued = sent = failed = 0
            for batch_idx in range(0, len(all_scraped), batch_size):
                batch = all_scraped[batch_idx:batch_idx + batch_size]
                bn = batch_idx // batch_size + 1
                _log(f"Batch {bn}/{total_batches}: ingesting {len(batch)} jobs...")
                b_new = await engine.ingest_jobs(batch)
                new_count += b_new

                _log(f"Batch {bn}/{total_batches}: scoring {b_new} new jobs with AI...")
                b_queued = await engine.queue_applications(profile, resume)
                queued = b_queued  # cumulative pending count

                _log(f"Batch {bn}/{total_batches}: applying to pending jobs...")
                result = await engine.process_pending_applications(resume, dry_run=dry)
                b_sent = result.get('sent', 0)
                b_failed = result.get('failed', 0)
                sent += b_sent
                failed += b_failed
                _log(f"Batch {bn}/{total_batches} done — new: {b_new} | applied: {b_sent} | failed: {b_failed}")

            _log(f"All done! Scraped: {len(all_scraped)} | New: {new_count} | Applied: {sent} | Failed: {failed}")
            _run_state["stats"] = {
                "scraped": len(all_scraped),
                "new": new_count,
                "queued": queued,
                "applied": sent,
                "failed": failed,
            }
        except Exception as e:
            _log(f"Search task crashed: {e}", "error")
            logger.exception(e)
        finally:
            _run_state["running"] = False


@router.post("/run/apply", tags=["automation"])
async def run_apply(
    resume_id: int,
    dry_run: bool = True,
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Process queued applications."""
    background_tasks.add_task(_run_apply_task, resume_id, dry_run)
    return {"message": "Apply run started", "dry_run": dry_run}


async def _run_apply_task(resume_id: int, dry_run: bool):
    from backend.db.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        resume_result = await db.execute(select(Resume).where(Resume.id == resume_id))
        resume = resume_result.scalar_one_or_none()
        if not resume:
            return
        ai_client = get_ai_client()
        matcher = JobMatcher(ai_client, settings.AI_PROVIDER)
        engine = ApplicationEngine(db, matcher, ai_client)
        result = await engine.process_pending_applications(resume, dry_run=dry_run)
        logger.info(f"Apply run complete: {result}")


# ------------------------------------------------------------------ #
#  AI Test Endpoint
# ------------------------------------------------------------------ #

@router.post("/test/match", tags=["ai"])
async def test_match(body: MatchTestRequest, db: AsyncSession = Depends(get_db)):
    """Test AI matching for a resume against a job description."""
    resume_result = await db.execute(select(Resume).where(Resume.id == body.resume_id))
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(404, "Resume not found")

    ai_client = get_ai_client()
    if not ai_client:
        raise HTTPException(503, "No AI provider configured")

    matcher = JobMatcher(ai_client, settings.AI_PROVIDER)
    job = {"title": body.job_title, "company": body.company, "description": body.job_description}
    score, analysis = await matcher.score_match(resume.parsed_data or {}, job)
    cover_letter = await matcher.generate_cover_letter(
        resume.parsed_data or {}, job, analysis.get("explanation", "")
    )
    return {
        "score": score,
        "analysis": analysis,
        "cover_letter": cover_letter,
    }


# ------------------------------------------------------------------ #
#  Stats
# ------------------------------------------------------------------ #

@router.get("/stats", tags=["stats"])
async def get_stats(db: AsyncSession = Depends(get_db)):
    ai_client = get_ai_client()
    matcher = JobMatcher(ai_client, settings.AI_PROVIDER) if ai_client else None
    engine = ApplicationEngine(db, matcher, ai_client)
    return await engine.get_stats_summary()


@router.get("/stats/history", tags=["stats"])
async def get_stats_history(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DailyStats).order_by(desc(DailyStats.date)).limit(30))
    rows = result.scalars().all()
    return [
        {
            "date": r.date,
            "jobs_discovered": r.jobs_discovered,
            "applications_sent": r.applications_sent,
            "applications_failed": r.applications_failed,
        }
        for r in rows
    ]


@router.get("/scrapers", tags=["system"])
async def list_scrapers():
    """Return metadata about all available job board scrapers."""
    return [
        {
            "id": "linkedin",
            "name": "LinkedIn",
            "description": "World's largest professional network. Supports Easy Apply.",
            "region": "Global",
            "requires_login": True,
            "easy_apply": True,
            "type": "browser",
        },
        {
            "id": "indeed",
            "name": "Indeed",
            "description": "Largest general job board globally.",
            "region": "Global (US/IN/UK/CA/AU)",
            "requires_login": False,
            "easy_apply": False,
            "type": "browser",
        },
        {
            "id": "glassdoor",
            "name": "Glassdoor",
            "description": "Jobs with company reviews and salary data.",
            "region": "Global",
            "requires_login": False,
            "easy_apply": False,
            "type": "http",
        },
        {
            "id": "naukri",
            "name": "Naukri",
            "description": "India's #1 job portal. Best for India-based roles.",
            "region": "India",
            "requires_login": False,
            "easy_apply": False,
            "type": "http",
        },
        {
            "id": "dice",
            "name": "Dice",
            "description": "Top US tech job board. Strong for full stack and AI roles.",
            "region": "USA",
            "requires_login": False,
            "easy_apply": True,
            "type": "http",
        },
        {
            "id": "wellfound",
            "name": "Wellfound (AngelList)",
            "description": "Startup jobs. Strong for AI/ML, full stack at funded startups.",
            "region": "Global (startup-focused)",
            "requires_login": False,
            "easy_apply": False,
            "type": "http",
        },
    ]


@router.get("/health", tags=["system"])
async def health():
    return {
        "status": "ok",
        "auto_apply_enabled": settings.AUTO_APPLY_ENABLED,
        "dry_run": settings.DRY_RUN,
        "ai_provider": settings.AI_PROVIDER,
        "max_apps_per_day": settings.MAX_APPLICATIONS_PER_DAY,
        "available_scrapers": ["linkedin", "indeed", "glassdoor", "naukri", "dice", "wellfound"],
    }


# ================================================================== #
#  PREMIUM AI FEATURES — beats every competitor
# ================================================================== #

class TailorRequest(BaseModel):
    resume_id: int
    job_description: str
    job_title: str = "Software Engineer"
    company: str = ""

class CompanyIntelRequest(BaseModel):
    company: str
    job_title: str
    location: str = ""

class InterviewPrepRequest(BaseModel):
    resume_id: int
    job_id: Optional[int] = None
    job_title: str = ""
    company: str = ""
    job_description: str = ""

class FollowUpRequest(BaseModel):
    application_id: int
    followup_type: str = "gentle_check"  # thank_you | gentle_check | final_followup

class SalaryRequest(BaseModel):
    job_title: str
    location: str = "Remote"
    experience_years: int = 5


# ── Resume Tailoring ─────────────────────────────────────────────────

@router.post("/ai/tailor-resume", tags=["ai-premium"])
async def tailor_resume(body: TailorRequest, db: AsyncSession = Depends(get_db)):
    """AI rewrites resume bullet points to match a specific job. No competitor does this free."""
    resume_result = await db.execute(select(Resume).where(Resume.id == body.resume_id))
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(404, "Resume not found")
    ai_client = get_ai_client()
    if not ai_client:
        raise HTTPException(503, "No AI provider configured")

    from backend.ai.resume_tailor import ResumeTailor
    tailor = ResumeTailor(ai_client, settings.AI_PROVIDER)

    job = {"title": body.job_title, "company": body.company, "description": body.job_description}
    tailored = await tailor.tailor_resume(resume.parsed_data or {}, job)
    ats_score = await tailor.score_ats_compatibility(
        resume.content_text or "", body.job_description
    )
    keywords = await tailor.extract_keywords(body.job_description)

    return {
        "tailored_resume": tailored,
        "ats_score": ats_score,
        "job_keywords": keywords,
    }


@router.post("/ai/ats-score", tags=["ai-premium"])
async def ats_score(body: TailorRequest, db: AsyncSession = Depends(get_db)):
    """Score how well your resume will pass ATS keyword filters."""
    resume_result = await db.execute(select(Resume).where(Resume.id == body.resume_id))
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(404, "Resume not found")
    ai_client = get_ai_client()
    if not ai_client:
        raise HTTPException(503, "No AI provider configured")

    from backend.ai.resume_tailor import ResumeTailor
    tailor = ResumeTailor(ai_client, settings.AI_PROVIDER)
    score = await tailor.score_ats_compatibility(
        resume.content_text or "", body.job_description
    )
    return score


# ── Company Intelligence ─────────────────────────────────────────────

@router.post("/ai/company-intel", tags=["ai-premium"])
async def company_intel(body: CompanyIntelRequest):
    """Get AI-powered intelligence about any company — ratings, culture, salary, tips."""
    ai_client = get_ai_client()
    if not ai_client:
        raise HTTPException(503, "No AI provider configured")

    from backend.ai.company_intel import CompanyIntel
    intel = CompanyIntel(ai_client, settings.AI_PROVIDER)
    return await intel.enrich_company(body.company, body.job_title, body.location)


@router.post("/ai/salary-estimate", tags=["ai-premium"])
async def salary_estimate(body: SalaryRequest):
    """Estimate salary range for a role + location + experience level."""
    ai_client = get_ai_client()
    if not ai_client:
        raise HTTPException(503, "No AI provider configured")

    from backend.ai.company_intel import CompanyIntel
    intel = CompanyIntel(ai_client, settings.AI_PROVIDER)
    return await intel.estimate_salary(body.job_title, body.location, body.experience_years)


# ── Interview Preparation ────────────────────────────────────────────

@router.post("/ai/interview-prep", tags=["ai-premium"])
async def interview_prep(body: InterviewPrepRequest, db: AsyncSession = Depends(get_db)):
    """Generate complete interview prep: behavioral + technical questions + tips."""
    resume_result = await db.execute(select(Resume).where(Resume.id == body.resume_id))
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(404, "Resume not found")

    job_desc = body.job_description
    job_title = body.job_title
    company = body.company

    # If job_id provided, load from DB
    if body.job_id:
        job_result = await db.execute(select(Job).where(Job.id == body.job_id))
        job = job_result.scalar_one_or_none()
        if job:
            job_desc = job_desc or job.description or ""
            job_title = job_title or job.title
            company = company or job.company

    ai_client = get_ai_client()
    if not ai_client:
        raise HTTPException(503, "No AI provider configured")

    from backend.ai.company_intel import CompanyIntel
    intel = CompanyIntel(ai_client, settings.AI_PROVIDER)
    prep = await intel.generate_interview_prep(
        resume.parsed_data or {},
        {"title": job_title, "company": company, "description": job_desc},
    )
    # Also include company intel
    company_data = await intel.enrich_company(company, job_title)
    prep["company_intel"] = company_data
    return prep


# ── Follow-Up Emails ────────────────────────────────────────────────

@router.post("/ai/follow-up", tags=["ai-premium"])
async def generate_followup(body: FollowUpRequest, db: AsyncSession = Depends(get_db)):
    """Generate a personalized follow-up email for an application."""
    stmt = select(Application, Job, Resume).join(Job).join(Resume).where(Application.id == body.application_id)
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(404, "Application not found")
    app, job, resume = row

    ai_client = get_ai_client()
    if not ai_client:
        raise HTTPException(503, "No AI provider configured")

    from backend.ai.followup import FollowUpGenerator
    gen = FollowUpGenerator(ai_client, settings.AI_PROVIDER)

    candidate_name = (resume.parsed_data or {}).get("name", "")
    applied_str = app.applied_at.isoformat() if app.applied_at else ""

    email = await gen.generate_followup(
        candidate_name, job.title, job.company,
        applied_str, app.cover_letter or "", body.followup_type,
    )
    schedule = gen.get_followup_schedule(applied_str)
    return {"email": email, "schedule": schedule}


# ── Follow-Up Tracking (scheduler-driven) ───────────────────────────

@router.get("/applications/{app_id}/followups", tags=["followups"])
async def list_followups(app_id: int, db: AsyncSession = Depends(get_db)):
    """Return all scheduled follow-ups for an application."""
    result = await db.execute(
        select(FollowUp)
        .where(FollowUp.application_id == app_id)
        .order_by(FollowUp.scheduled_for)
    )
    fus = result.scalars().all()
    return [
        {
            "id": fu.id,
            "followup_type": fu.followup_type,
            "label": fu.label,
            "scheduled_for": fu.scheduled_for,
            "sent_at": fu.sent_at,
            "subject": fu.subject,
            "body": fu.body,
            "status": fu.status,
            "error_message": fu.error_message,
        }
        for fu in fus
    ]


@router.post("/followups/{followup_id}/send", tags=["followups"])
async def send_followup_now(followup_id: int, db: AsyncSession = Depends(get_db)):
    """Manually trigger a follow-up — generates email and sends (or marks sent if no SMTP)."""
    from sqlalchemy.orm import selectinload
    from backend.ai.followup import FollowUpGenerator
    from backend.core.email_service import send_email

    result = await db.execute(
        select(FollowUp).where(FollowUp.id == followup_id)
    )
    fu = result.scalar_one_or_none()
    if not fu:
        raise HTTPException(404, "Follow-up not found")
    if fu.status == "sent":
        raise HTTPException(400, "Follow-up already sent")

    app_result = await db.execute(
        select(Application)
        .where(Application.id == fu.application_id)
        .options(selectinload(Application.job), selectinload(Application.resume))
    )
    app = app_result.scalar_one_or_none()
    if not app:
        raise HTTPException(404, "Application not found")

    ai_client = get_ai_client()
    if not ai_client:
        raise HTTPException(503, "No AI provider configured")

    gen = FollowUpGenerator(ai_client, settings.AI_PROVIDER)
    candidate_name = (app.resume.parsed_data or {}).get("name", "") if app.resume else ""

    email = await gen.generate_followup(
        candidate_name=candidate_name,
        job_title=app.job.title,
        company=app.job.company,
        applied_date=app.applied_at.isoformat() if app.applied_at else "",
        cover_letter=app.cover_letter or "",
        followup_type=fu.followup_type,
    )
    fu.subject = email["subject"]
    fu.body = email["body"]

    notify_to = settings.NOTIFY_EMAIL
    if notify_to and email["body"]:
        sent = await send_email(notify_to, email["subject"], email["body"])
        fu.status = "sent" if sent else "failed"
        fu.sent_at = datetime.utcnow() if sent else None
        fu.error_message = None if sent else "SMTP send failed"
    else:
        fu.status = "sent"
        fu.sent_at = datetime.utcnow()

    await db.commit()
    return {"message": f"Follow-up {fu.status}", "subject": fu.subject, "body": fu.body}


@router.post("/followups/{followup_id}/skip", tags=["followups"])
async def skip_followup(followup_id: int, db: AsyncSession = Depends(get_db)):
    """Skip a pending follow-up."""
    result = await db.execute(select(FollowUp).where(FollowUp.id == followup_id))
    fu = result.scalar_one_or_none()
    if not fu:
        raise HTTPException(404, "Follow-up not found")
    fu.status = "skipped"
    await db.commit()
    return {"message": "Follow-up skipped"}


# ── Cover Letter A/B Analytics ───────────────────────────────────────

@router.get("/ai/cover-letter-analytics", tags=["ai-premium"])
async def cover_letter_analytics(db: AsyncSession = Depends(get_db)):
    """Track which cover letter patterns lead to interviews — A/B testing for job apps."""
    # Applications that got interviews vs those that didn't
    interview_apps = await db.execute(
        select(Application).where(Application.status == ApplicationStatus.INTERVIEW)
    )
    rejected_apps = await db.execute(
        select(Application).where(Application.status == ApplicationStatus.REJECTED)
    )

    interviews = interview_apps.scalars().all()
    rejected = rejected_apps.scalars().all()

    # Analyze patterns
    interview_count = len(interviews)
    rejected_count = len(rejected)
    total = interview_count + rejected_count

    # Word frequency in successful vs failed cover letters
    def extract_lengths(apps):
        return [len(a.cover_letter or "") for a in apps if a.cover_letter]

    return {
        "total_tracked": total,
        "interview_rate": round(interview_count / total * 100, 1) if total else 0,
        "interviews": interview_count,
        "rejections": rejected_count,
        "avg_cover_letter_length_interviews": round(
            sum(extract_lengths(interviews)) / max(len(interviews), 1)
        ),
        "avg_cover_letter_length_rejections": round(
            sum(extract_lengths(rejected)) / max(len(rejected), 1)
        ),
        "insight": (
            "Cover letters that led to interviews were on average "
            f"{round(sum(extract_lengths(interviews)) / max(len(interviews), 1))} chars. "
            "Keep cover letters concise and specific."
            if interviews else "Not enough data yet. Apply to more jobs to see patterns."
        ),
    }
