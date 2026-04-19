import asyncio
from backend.db.database import AsyncSessionLocal as async_session
from backend.models.models import Job, Application, ApplicationStatus, JobSource, Resume
from backend.core.application_engine import ApplicationEngine
from backend.ai.matcher import JobMatcher
from backend.ai.client import get_ai_client
from sqlalchemy import select
from loguru import logger

async def test_apply_functionality():
    logger.info("🛠️ Setting up Apply Functionality Test...")
    
    async with async_session() as session:
        # 1. Ensure a resume exists
        res = await session.execute(select(Resume).limit(1))
        resume = res.scalar_one_or_none()
        if not resume:
            logger.error("❌ No resume found in database. Please upload one first.")
            return

        logger.info(f"✅ Found Resume: {resume.name} (ID: {resume.id})")

        # 2. Create a mock Pending job if none exist
        res = await session.execute(
            select(Application).where(Application.status == ApplicationStatus.PENDING)
        )
        pending_apps = res.scalars().all()
        
        if not pending_apps:
            logger.info("📝 No pending applications found. Creating a mock job...")
            job = Job(
                external_id=f"test_{int(asyncio.get_event_loop().time())}",
                title="Staff Software Engineer (AI/ML)",
                company="Applyra Test Labs",
                description="This is a test job description for verifying the lightning engine parallel application logic.",
                url="https://example.com/test-job",
                source=JobSource.LINKEDIN,
                easy_apply=True
            )
            session.add(job)
            await session.flush()
            
            app = Application(
                job_id=job.id,
                resume_id=resume.id,
                status=ApplicationStatus.PENDING,
                match_score=0.98,
                match_explanation="Perfect match for test verification."
            )
            session.add(app)
            await session.commit()
            pending_apps = [app]
            logger.info(f"✅ Mock job created for {resume.name}")

        # 3. Trigger the Lightning Engine (Dry Run)
        logger.info("⚡ Initializing Lightning Engine for Dry Run...")
        ai_client = get_ai_client()
        matcher = JobMatcher(ai_client, "gemini") # Force gemini for test
        engine = ApplicationEngine(session, matcher, ai_client)
        
        # We need to re-fetch resume to ensure it's in the current session
        res = await session.execute(select(Resume).where(Resume.id == resume.id))
        resume = res.scalar_one()

        results = await engine.process_pending_applications(resume, dry_run=True)
        
        logger.info(f"📊 Test Results: {results}")
        
        if results.get('sent', 0) > 0:
            logger.success("🚀 Apply Functionality Test PASSED (Dry Run)")
        else:
            logger.error("❌ Apply Functionality Test FAILED")

if __name__ == "__main__":
    asyncio.run(test_apply_functionality())
