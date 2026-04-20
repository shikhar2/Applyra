"""
Glassdoor job scraper — Playwright-based (bypasses Cloudflare).
"""
import asyncio
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from .base import BaseScraper, ScrapedJob


class GlassdoorScraper(BaseScraper):
    BASE_URL = "https://www.glassdoor.com"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.browser = None
        self.context = None
        self.page = None

    async def __aenter__(self):
        from playwright.async_api import async_playwright
        self._pw_ctx = async_playwright()
        pw = await self._pw_ctx.__aenter__()
        self.browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        self.page = await self.context.new_page()
        try:
            from playwright_stealth import Stealth
            await Stealth().apply_stealth_async(self.page)
        except Exception:
            pass
        return self

    async def __aexit__(self, *args):
        if self.browser:
            await self.browser.close()

    async def search_jobs(self, query: str, location: str = "Remote",
                          max_results: int = 50, days: int = 7) -> List[ScrapedJob]:
        if not self.page:
            async with self:
                return await self._do_search(query, location, max_results)
        return await self._do_search(query, location, max_results)

    async def _do_search(self, query: str, location: str, max_results: int) -> List[ScrapedJob]:
        jobs = []
        try:
            q = query.replace(" ", "+")
            loc = location.replace(" ", "+") if location.lower() not in ("remote", "anywhere") else ""
            url = f"{self.BASE_URL}/Job/jobs.htm?sc.keyword={q}&locT=N&fromAge=7&jobType=fulltime"
            if loc:
                url += f"&locKeyword={loc}"

            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(self.config.get("delay", 3))

            # Dismiss login modal if present
            try:
                close_btn = await self.page.query_selector('[alt="Close"], .modal_closeIcon, [data-test="modal-header-close-button"]')
                if close_btn:
                    await close_btn.click()
                    await asyncio.sleep(0.5)
            except Exception:
                pass

            # Extract job cards via JS — more robust than CSS selectors
            raw = await self.page.evaluate("""() => {
                const cards = document.querySelectorAll('[data-test="jobListing"], li[data-jobid], .JobCard_jobCardContent__o4iPH');
                return Array.from(cards).map(card => {
                    const titleEl = card.querySelector('[data-test="job-title"], .JobCard_jobTitle__GLyJ1, a[class*="jobTitle"]');
                    const companyEl = card.querySelector('[data-test="employer-name"], .EmployerProfile_compactEmployerName__9MGcV, [class*="employerName"]');
                    const locEl = card.querySelector('[data-test="emp-location"], [class*="location"]');
                    const linkEl = card.querySelector('a[href*="/job-listing/"], a[href*="/partner/"]');
                    const salaryEl = card.querySelector('[data-test="detailSalary"], [class*="salary"]');
                    const jobId = card.getAttribute('data-jobid') || card.getAttribute('data-id') || '';

                    return {
                        job_id: jobId,
                        title: titleEl ? titleEl.innerText.trim() : '',
                        company: companyEl ? companyEl.innerText.trim() : '',
                        location: locEl ? locEl.innerText.trim() : '',
                        url: linkEl ? linkEl.href : '',
                        salary: salaryEl ? salaryEl.innerText.trim() : '',
                    };
                }).filter(j => j.title && j.company);
            }""")

            for item in (raw or [])[:max_results]:
                job = self._parse_raw(item)
                if job:
                    jobs.append(job)

        except Exception as e:
            logger.error(f"Glassdoor search error: {e}")

        logger.info(f"Glassdoor scraped {len(jobs)} jobs for '{query}'")
        return jobs

    def _parse_raw(self, item: dict) -> Optional[ScrapedJob]:
        try:
            title = item.get("title", "").strip()
            company = item.get("company", "").strip()
            if not title or not company:
                return None

            job_id = item.get("job_id") or f"gd_{hash(title+company)}"
            url = item.get("url") or f"{self.BASE_URL}/job-listing/{job_id}"
            location = item.get("location", "").strip()
            is_remote = "remote" in location.lower()

            sal_str = item.get("salary", "")
            sal_min, sal_max = self._parse_salary_text(sal_str)

            return ScrapedJob(
                external_id=f"gd_{job_id}",
                title=title,
                company=company,
                location=location or ("Remote" if is_remote else "US"),
                description="",
                url=url,
                apply_url=url,
                source="glassdoor",
                remote=is_remote,
                salary_min=sal_min,
                salary_max=sal_max,
            )
        except Exception as e:
            logger.debug(f"Glassdoor parse error: {e}")
            return None

    def _parse_salary_text(self, text: str):
        if not text:
            return None, None
        nums = re.findall(r"[\d,]+", text)
        vals = [int(n.replace(",", "")) for n in nums if int(n.replace(",", "")) > 0]
        if not vals:
            return None, None
        if "k" in text.lower():
            vals = [v * 1000 if v < 1000 else v for v in vals]
        return (vals[0], vals[-1]) if len(vals) >= 2 else (vals[0], vals[0])

    async def get_job_details(self, job_url: str) -> Dict[str, Any]:
        return {}
