"""
Background scheduler: runs job searches and follow-up emails periodically.
Can be run as a standalone process: python -m backend.scheduler
"""
import asyncio
from datetime import datetime
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.core.config import settings
from backend.db.database import AsyncSessionLocal
from backend.models.models import Resume, JobProfile, Application, ApplicationStatus, FollowUp
from backend.ai.matcher import JobMatcher
from backend.core.application_engine import ApplicationEngine
from backend.scrapers import SCRAPERS, BROWSER_SCRAPERS


# Which sources to run on each scheduled cycle (can override via config later)
DEFAULT_SOURCES = ["linkedin", "indeed", "dice", "wellfound", "glassdoor"]


async def run_scheduled_search():
    logger.info(f"[Scheduler] Running job search at {datetime.utcnow()}")
    async with AsyncSessionLocal() as db:
        profile_result = await db.execute(
            select(JobProfile).where(JobProfile.is_active == True)
        )
        profiles = profile_result.scalars().all()

        resume_result = await db.execute(
            select(Resume).where(Resume.is_active == True).limit(1)
        )
        resume = resume_result.scalar_one_or_none()

        if not resume or not profiles:
            logger.warning("No active resume or profiles configured")
            return

        if settings.AI_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
            import anthropic
            ai_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        elif settings.AI_PROVIDER == "openai" and settings.OPENAI_API_KEY:
            from openai import AsyncOpenAI
            ai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            logger.error("No AI provider configured")
            return

        matcher = JobMatcher(ai_client, settings.AI_PROVIDER)
        engine = ApplicationEngine(db, matcher, ai_client)
        cfg = {"delay": settings.SCRAPER_DELAY_SECONDS}

        for profile in profiles:
            all_scraped = []
            for source in DEFAULT_SOURCES:
                if source not in SCRAPERS:
                    continue
                scraper_cls = SCRAPERS[source]
                for role in (profile.target_roles or ["Software Engineer"]):
                    for location in (profile.target_locations or ["Remote"]):
                        try:
                            if source in BROWSER_SCRAPERS:
                                async with scraper_cls(cfg) as s:
                                    jobs = await s.search_jobs(role, location, max_results=25)
                                    all_scraped.extend(jobs)
                            else:
                                s = scraper_cls(cfg)
                                jobs = await s.search_jobs(role, location, max_results=25)
                                all_scraped.extend(jobs)
                            logger.info(f"[{source}] {len(jobs)} jobs for '{role}' @ '{location}'")
                        except Exception as e:
                            logger.error(f"Scraper {source} error for '{role}': {e}")

            new_count = await engine.ingest_jobs(all_scraped)
            queued = await engine.queue_applications(profile, resume)
            logger.info(f"Profile '{profile.name}': {new_count} new, {queued} queued")

        result = await engine.process_pending_applications(
            resume, dry_run=settings.DRY_RUN
        )
        logger.info(f"Apply result: {result}")


async def run_followup_scheduler():
    """
    1. Create FollowUp records for APPLIED applications that don't have any yet.
    2. Generate + send any follow-ups that are due.
    """
    from backend.ai.followup import FollowUpGenerator
    from backend.core.email_service import send_email

    logger.info("[FollowUp] Running follow-up scheduler")
    async with AsyncSessionLocal() as db:
        # --- Step 1: seed FollowUp rows for newly applied apps ---
        applied_result = await db.execute(
            select(Application)
            .where(Application.status == ApplicationStatus.APPLIED)
            .where(Application.applied_at.is_not(None))
        )
        for app in applied_result.scalars().all():
            exists = await db.execute(
                select(FollowUp).where(FollowUp.application_id == app.id).limit(1)
            )
            if exists.scalar_one_or_none():
                continue

            gen = FollowUpGenerator(None)
            for item in gen.get_followup_schedule(app.applied_at.isoformat()):
                db.add(FollowUp(
                    application_id=app.id,
                    followup_type=item["type"],
                    label=item["label"],
                    scheduled_for=datetime.fromisoformat(item["date"]),
                    status="pending",
                ))
        await db.commit()

        # --- Step 2: send due follow-ups ---
        now = datetime.utcnow()
        due_result = await db.execute(
            select(FollowUp)
            .where(FollowUp.status == "pending")
            .where(FollowUp.scheduled_for <= now)
        )
        due = due_result.scalars().all()
        if not due:
            logger.info("[FollowUp] No due follow-ups")
            return

        # Build AI client once
        ai_client, provider = None, None
        if settings.AI_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
            import anthropic
            ai_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            provider = "anthropic"
        elif settings.GEMINI_API_KEY:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            ai_client = genai
            provider = "gemini"
        elif settings.GROQ_API_KEY:
            from groq import AsyncGroq
            ai_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
            provider = "groq"

        if not ai_client:
            logger.error("[FollowUp] No AI provider configured")
            return

        gen = FollowUpGenerator(ai_client, provider)

        for fu in due:
            try:
                app_result = await db.execute(
                    select(Application)
                    .where(Application.id == fu.application_id)
                    .options(selectinload(Application.job), selectinload(Application.resume))
                )
                app = app_result.scalar_one_or_none()
                if not app:
                    continue

                # Skip if application reached a terminal state
                if app.status in (ApplicationStatus.REJECTED, ApplicationStatus.OFFER, ApplicationStatus.SKIPPED):
                    fu.status = "skipped"
                    await db.commit()
                    continue

                candidate_name = ""
                if app.resume and app.resume.parsed_data:
                    candidate_name = app.resume.parsed_data.get("name", "")

                result = await gen.generate_followup(
                    candidate_name=candidate_name,
                    job_title=app.job.title,
                    company=app.job.company,
                    applied_date=app.applied_at.isoformat() if app.applied_at else "",
                    cover_letter=app.cover_letter or "",
                    followup_type=fu.followup_type,
                )

                fu.subject = result["subject"]
                fu.body = result["body"]

                notify_to = settings.NOTIFY_EMAIL
                if notify_to and result["body"]:
                    sent = await send_email(notify_to, result["subject"], result["body"])
                    fu.status = "sent" if sent else "failed"
                    fu.sent_at = datetime.utcnow() if sent else None
                    if not sent:
                        fu.error_message = "SMTP send failed"
                else:
                    # Generated but no SMTP configured — mark sent so it shows in UI
                    fu.status = "sent"
                    fu.sent_at = datetime.utcnow()
                    logger.info(f"[FollowUp] Generated (no SMTP): {result['subject']}")

                await db.commit()
                logger.info(f"[FollowUp] {fu.followup_type} for app {fu.application_id}: {fu.status}")
            except Exception as e:
                logger.error(f"[FollowUp] Error for follow-up {fu.id}: {e}")
                fu.status = "failed"
                fu.error_message = str(e)
                await db.commit()


def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_scheduled_search,
        "interval",
        minutes=settings.SCHEDULER_INTERVAL_MINUTES,
        id="job_search",
        replace_existing=True,
    )
    scheduler.add_job(
        run_followup_scheduler,
        "interval",
        minutes=30,
        id="followup_scheduler",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started. Job search: {settings.SCHEDULER_INTERVAL_MINUTES}m | Follow-ups: 30m")
    return scheduler


if __name__ == "__main__":
    async def main():
        scheduler = start_scheduler()
        await run_scheduled_search()
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            scheduler.shutdown()

    asyncio.run(main())
