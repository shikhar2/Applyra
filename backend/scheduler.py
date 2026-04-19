"""
Background scheduler: runs job searches periodically.
Can be run as a standalone process: python -m backend.scheduler
"""
import asyncio
from datetime import datetime
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from backend.core.config import settings
from backend.db.database import AsyncSessionLocal
from backend.models.models import Resume, JobProfile
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


def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_scheduled_search,
        "interval",
        minutes=settings.SCHEDULER_INTERVAL_MINUTES,
        id="job_search",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started. Interval: {settings.SCHEDULER_INTERVAL_MINUTES}m")
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
