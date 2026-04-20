"""
Core application engine — high-performance parallel edition.

Optimizations:
- Multi-Worker Application Architecture: Uses a Pool of browser workers.
- Parallel AI Logic: Scoring and generation happen concurrently.
- Thread-safe Job Tracking: Ensures no duplicate applications in high-concurrency mode.
"""
import asyncio
import hashlib
import re
from datetime import datetime, date
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from playwright.async_api import async_playwright

from backend.models.models import (
    Job, Application, Resume, JobProfile, DailyStats,
    ApplicationStatus, JobSource,
)
from backend.ai.matcher import JobMatcher
from backend.core.config import settings
from backend.core.tier_config import should_tailor, get_company_tier
from backend.scrapers.base import ScrapedJob
from backend.scrapers.ats_applier import ATSApplier


def _dedup_key(company: str, title: str) -> str:
    def slugify(s: str) -> str:
        s = s.lower().strip()
        s = re.sub(r"[^a-z0-9\s]", "", s)
        s = re.sub(r"\s+", " ", s)
        noise = {"senior", "sr", "jr", "junior", "staff", "principal", "lead",
                 "engineer", "developer", "software", "the", "a", "an"}
        return " ".join(w for w in s.split() if w not in noise)
    return hashlib.md5(f"{slugify(company)}|{slugify(title)}".encode()).hexdigest()[:16]


class ApplicationEngine:
    def __init__(self, db: AsyncSession, matcher: JobMatcher, ai_client, log_fn=None):
        self.db = db
        self.matcher = matcher
        self.ai_client = ai_client
        self._log = log_fn or (lambda msg, level="info": None)

    # ── Job ingestion ──────────────────────────────────────────────────────

    async def ingest_jobs(self, scraped_jobs: list[ScrapedJob]) -> int:
        applied_result = await self.db.execute(
            select(Job.company, Job.title).join(Application).where(Application.status.in_([
                ApplicationStatus.APPLIED, ApplicationStatus.PENDING, ApplicationStatus.APPLYING,
            ]))
        )
        applied_keys = {_dedup_key(r.company, r.title) for r in applied_result}

        all_ext_ids = [sj.external_id for sj in scraped_jobs]
        existing_result = await self.db.execute(select(Job.external_id).where(Job.external_id.in_(all_ext_ids)))
        existing_ids = {row[0] for row in existing_result}

        new_count = 0
        for sj in scraped_jobs:
            if sj.external_id in existing_ids: continue
            dkey = _dedup_key(sj.company, sj.title)
            if dkey in applied_keys: continue

            job = Job(
                external_id=sj.external_id, title=sj.title, company=sj.company,
                location=sj.location, description=sj.description, url=sj.url,
                apply_url=sj.apply_url, source=JobSource(sj.source),
                remote=sj.remote, salary_min=sj.salary_min, salary_max=sj.salary_max,
                job_type=sj.job_type, easy_apply=sj.easy_apply, posted_at=sj.posted_at,
                extra_data=sj.extra_data,
            )
            self.db.add(job); applied_keys.add(dkey); new_count += 1

        await self.db.commit()
        return new_count

    # ── Matching & queuing ─────────────────────────────────────────────────

    async def queue_applications(self, profile: JobProfile, resume: Resume) -> int:
        resume_data = resume.parsed_data or {}
        subq = select(Application.job_id).where(Application.resume_id == resume.id)
        stmt = select(Job).where(and_(~Job.id.in_(subq), Job.company.notin_(profile.excluded_companies or []))).order_by(Job.discovered_at.desc()).limit(300)
        result = await self.db.execute(stmt)
        jobs = result.scalars().all()
        
        ai_sem = asyncio.Semaphore(settings.MAX_AI_CONCURRENCY)
        scored = 0
        total = len(jobs)

        async def _score_one(job):
            nonlocal scored
            if not self._profile_filter(job, profile):
                await self._create_application(job, resume, 0.0, {}, ApplicationStatus.SKIPPED)
                scored += 1
                return
            job_dict = {"title": job.title, "company": job.company, "description": job.description or "", "location": job.location}
            async with ai_sem:
                score, analysis = await self.matcher.score_match(resume_data, job_dict)
            scored += 1
            verdict = "✓" if score >= settings.MIN_MATCH_SCORE and analysis.get("apply_recommendation", False) else "✗"
            self._log(f"  [{scored}/{total}] {verdict} {job.title} @ {job.company} — {score:.0%}")
            if score >= settings.MIN_MATCH_SCORE and analysis.get("apply_recommendation", False):
                if score >= settings.HITL_REVIEW_THRESHOLD:
                    async with ai_sem:
                        _, deep = await self.matcher.deep_score_match(resume_data, job_dict)
                    app = await self._create_application(job, resume, score, analysis, ApplicationStatus.REVIEW)
                    app.deep_analysis = deep
                else:
                    await self._create_application(job, resume, score, analysis, ApplicationStatus.PENDING)
            else:
                await self._create_application(job, resume, score, analysis, ApplicationStatus.SKIPPED)

        await asyncio.gather(*[_score_one(j) for j in jobs])
        await self.db.commit()

        q_res = await self.db.execute(select(func.count(Application.id)).where(
            Application.status.in_([ApplicationStatus.PENDING, ApplicationStatus.REVIEW]),
            Application.resume_id == resume.id,
        ))
        return q_res.scalar() or 0

    def _profile_filter(self, job: Job, profile: JobProfile) -> bool:
        t_l, d_l = (job.title or "").lower(), (job.description or "").lower()
        if profile.required_keywords:
            if not any(kw.lower() in t_l or kw.lower() in d_l for kw in profile.required_keywords): return False
        if profile.excluded_keywords:
            if any(kw.lower() in t_l or kw.lower() in d_l for kw in profile.excluded_keywords): return False
        if profile.remote_only and not job.remote: return False
        return True

    async def _create_application(self, job: Job, resume: Resume, score: float, data: dict, status: ApplicationStatus) -> Application:
        app = Application(job_id=job.id, resume_id=resume.id, status=status, match_score=score, match_explanation=data.get("explanation", ""))
        self.db.add(app)
        return app

    # ── Parallel Application Submission ─────────────────────────────────────

    async def process_pending_applications(self, resume: Resume, dry_run: bool = True) -> dict:
        today = date.today().isoformat()
        stats = await self._get_daily_stats(today)
        
        sent_count = stats.applications_sent or 0
        remaining = max(0, settings.MAX_APPLICATIONS_PER_DAY - sent_count)
        if remaining <= 0:
            logger.warning("Daily limit reached")
            return {"sent": 0, "failed": 0, "reason": "limit"}

        res = await self.db.execute(
            select(Application)
            .options(selectinload(Application.job))
            .where(
                Application.status == ApplicationStatus.PENDING,
                Application.resume_id == resume.id,
            )
            .order_by(Application.match_score.desc()).limit(remaining)
        )
        pending = res.scalars().all()
        if not pending: return {"sent": 0, "failed": 0, "reason": "none"}

        if dry_run:
            logger.info(f"Parallel Dry Run: Processing {len(pending)} applications")
            await asyncio.gather(*[self._prepare_application(app, resume) for app in pending])
            for app in pending:
                app.status = ApplicationStatus.APPLIED; app.applied_at = datetime.utcnow()
                stats.applications_sent = (stats.applications_sent or 0) + 1
            await self.db.commit()
            return {"sent": len(pending), "failed": 0, "dry_run": True}

        # Multi-Worker Parallel Submission
        num_workers = min(settings.MAX_BROWSER_SCRAPERS, len(pending))
        logger.info(f"🚀 Launching Lightning Engine: {num_workers} parallel browser workers")
        
        queue = asyncio.Queue()
        for app in pending: queue.put_nowait(app)
        
        results = {"sent": 0, "failed": 0}
        lock = asyncio.Lock()

        async def worker(_worker_id: int):
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
                context = await browser.new_context(viewport={"width": 1280, "height": 800})
                page = await context.new_page()
                applier = ATSApplier(page, self.ai_client)
                
                # Try LinkedIn & Naukri login if configured
                li_ok = False
                naukri_ok = False
                if settings.LINKEDIN_EMAIL:
                    li_ok = await self._linkedin_login(page, context, settings.LINKEDIN_EMAIL, settings.LINKEDIN_PASSWORD, "data/session")
                if settings.NAUKRI_EMAIL:
                    naukri_ok = await self._naukri_login(page, context, settings.NAUKRI_EMAIL, settings.NAUKRI_PASSWORD, "data/session_naukri")

                while not queue.empty():
                    app = await queue.get()
                    async with lock:
                        if (stats.applications_sent or 0) >= settings.MAX_APPLICATIONS_PER_DAY:
                            queue.task_done(); continue
                        app.status = ApplicationStatus.APPLYING; await self.db.commit()

                    success, msg = await self._submit_one(app, resume, applier, page, li_ok, naukri_ok)
                    
                    async with lock:
                        if success:
                            app.status = ApplicationStatus.APPLIED; app.applied_at = datetime.utcnow()
                            results["sent"] += 1
                            stats.applications_sent = (stats.applications_sent or 0) + 1
                        else:
                            app.status = ApplicationStatus.FAILED; app.error_message = msg
                            results["failed"] += 1
                            stats.applications_failed = (stats.applications_failed or 0) + 1
                        await self.db.commit()
                    
                    queue.task_done()
                    await asyncio.sleep(2) # Minor delay per worker
                await browser.close()

        # Run workers in parallel
        await asyncio.gather(*[worker(i) for i in range(num_workers)])
        return results

    async def _prepare_application(self, app: Application, resume: Resume):
        resume_data = resume.parsed_data or {}
        job_dict = {"title": app.job.title, "company": app.job.company, "description": app.job.description or ""}

        qs = [
            ("years_of_experience", "How many total years of professional software experience do you have?", "number"),
            ("authorized_to_work",  "Are you currently authorized to work in this country without sponsorship?", "yes_no"),
        ]

        async def _ans(question, ftype):
            return await self.matcher.answer_question(resume_data, question, ftype)

        # Run cover letter, Q&A, and (if top-tier) LaTeX resume concurrently
        tier = get_company_tier(app.job.company)
        app.is_top_tier = tier > 0

        coros = [
            self.matcher.generate_cover_letter(resume_data, job_dict, app.match_explanation or ""),
            *[_ans(q, t) for _, q, t in qs],
        ]

        if should_tailor(app.job.company, app.match_score or 0.0):
            from backend.ai.latex_resume import LatexResumeGenerator
            generator = LatexResumeGenerator(self.ai_client, settings.AI_PROVIDER)
            coros.append(generator.generate_tailored_pdf(resume_data, job_dict, app.id))
            logger.info(f"Top-tier company detected: {app.job.company} (tier {tier}) — generating LaTeX resume")
        else:
            async def _noop(): return None
            coros.append(_noop())

        res = await asyncio.gather(*coros, return_exceptions=True)

        app.cover_letter = res[0] if not isinstance(res[0], Exception) else ""
        app.answers = {qs[i][0]: res[i + 1] for i in range(len(qs)) if not isinstance(res[i + 1], Exception)}

        tailored_path = res[len(qs) + 1]
        if tailored_path and isinstance(tailored_path, str):
            app.tailored_resume_path = tailored_path
            logger.info(f"Tailored resume saved: {tailored_path}")

    async def _submit_one(self, app, resume, applier, page, li_ok, naukri_ok):
        if not app.cover_letter:
            await self._prepare_application(app, resume)

        # Use tailored resume PDF for top-tier companies, fall back to original
        resume_path = app.tailored_resume_path or resume.file_path
        source = app.job.source.value if hasattr(app.job.source, 'value') else str(app.job.source)
        apply_url = app.job.apply_url or app.job.url

        if app.tailored_resume_path:
            logger.info(f"Using tailored resume for {app.job.company}: {app.tailored_resume_path}")

        try:
            if source == "linkedin" and app.job.easy_apply and li_ok:
                from backend.scrapers.linkedin_scraper import LinkedInScraper
                li = LinkedInScraper.__new__(LinkedInScraper)
                li.page = page; li.logged_in = True; li.config = {"delay": 1.0}
                success = await li.easy_apply(app.job.url, resume_path, app.answers or {}, app.cover_letter or "")
                return success, "LinkedIn Easy Apply"
            
            # Handle Naukri Native (In-House) Jobs
            elif source == "naukri" and "naukri.com" in apply_url and naukri_ok:
                from backend.scrapers.naukri_scraper import NaukriScraper
                nk = NaukriScraper.__new__(NaukriScraper)
                nk.page = page
                success = await self._apply_naukri_native(page, resume_path, apply_url)
                return success, "Naukri Native Apply"

            else:
                success, msg = await applier.apply(
                    apply_url,
                    resume_path,
                    resume.parsed_data,
                    {"title": app.job.title, "company": app.job.company},
                    app.cover_letter or "",
                )
                return success, msg
        except Exception as e:
            return False, str(e)

    async def _linkedin_login(self, page, _context, email, password, _path):
        try:
            await page.goto("https://www.linkedin.com/login", wait_until="networkidle")
            await page.fill("#username", email); await page.fill("#password", password); await page.click('[type="submit"]')
            await page.wait_for_url("**/feed/**", timeout=15000); return True
        except: return False

    async def _naukri_login(self, page, _context, email, password, _path):
        """
        Logs into Naukri. Handles the initial login and checks for dashboard.
        """
        try:
            logger.info(f"Attempting Naukri login as {email}")
            await page.goto("https://www.naukri.com/nlogin/login", wait_until="networkidle")
            await page.fill("#usernameField", email)
            await page.fill("#passwordField", password)
            await page.click("button[type='submit']")
            await asyncio.sleep(5)
            
            # Check for OTP or success
            if "nlogin/otp" in page.url:
                logger.warning("Naukri login blocked by OTP. Please login manually once in a browser to trust this device.")
                return False
            
            # Wait for dashboard indicator
            await page.wait_for_selector(".n-card", timeout=10000)
            logger.success("Naukri login successful")
            return True
        except Exception as e:
            logger.warning(f"Naukri login failed: {e}")
            return False

    async def _apply_naukri_native(self, page, _resume_path, job_url):
        """Automates the 'Apply' button click on a native Naukri job page."""
        try:
            await page.goto(job_url, wait_until="domcontentloaded")
            apply_btn = await page.wait_for_selector("#apply-button, .apply-button, button:has-text('Apply')", timeout=10000)
            if apply_btn:
                await apply_btn.click()
                await asyncio.sleep(3)
                # Check for 'Already Applied' or 'Successfully Applied'
                content = (await page.content()).lower()
                if "applied" in content or "success" in content:
                    return True
            return False
        except:
            return False

    async def _get_daily_stats(self, today: str) -> DailyStats:
        res = await self.db.execute(select(DailyStats).where(DailyStats.date == today))
        stats = res.scalar_one_or_none()
        if not stats:
            stats = DailyStats(date=today); self.db.add(stats)
        return stats

    async def get_stats_summary(self) -> dict:
        sc = await self.db.execute(select(func.count(Job.id))); app = await self.db.execute(select(func.count(Application.id)))
        return {"total_jobs_discovered": sc.scalar(), "total_applications": app.scalar()}
