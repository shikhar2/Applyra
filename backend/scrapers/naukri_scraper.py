"""
Naukri.com scraper — Playwright-based (their REST API now requires session tokens).
"""
import asyncio
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from .base import BaseScraper, ScrapedJob


class NaukriScraper(BaseScraper):
    BASE_URL = "https://www.naukri.com"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.browser = None
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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
        )
        self.page = await self.context.new_page()
        return self

    async def __aexit__(self, *args):
        if self.browser:
            await self.browser.close()

    async def search_jobs(self, query: str, location: str = "India",
                          max_results: int = 50, days: int = 7) -> List[ScrapedJob]:
        if not self.page:
            async with self:
                return await self._do_search(query, location, max_results)
        return await self._do_search(query, location, max_results)

    async def _do_search(self, query: str, location: str, max_results: int) -> List[ScrapedJob]:
        jobs = []
        try:
            slug_query = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")
            is_remote = location.lower() in ("remote", "anywhere", "work from home")
            slug_loc = "remote-work-from-home" if is_remote else re.sub(r"[^a-z0-9]+", "-", location.lower()).strip("-")
            url = f"{self.BASE_URL}/{slug_query}-jobs-in-{slug_loc}"

            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(self.config.get("delay", 3))

            raw = await self.page.evaluate("""() => {
                const cards = document.querySelectorAll('.srp-jobtuple-wrapper, article[data-job-id], .jobTuple');
                return Array.from(cards).map(card => {
                    const titleEl = card.querySelector('.title, a.title, [class*="jobtitle"]');
                    const compEl = card.querySelector('.comp-name, .companyInfo a, [class*="company"]');
                    const locEl = card.querySelector('.locWdth, .location, [class*="location"]');
                    const expEl = card.querySelector('.expwdth, [class*="exp"]');
                    const salEl = card.querySelector('.sal-wrap, [class*="salary"]');
                    const linkEl = card.querySelector('a.title, a[href*="naukri.com"]');
                    const jobId = card.getAttribute('data-job-id') || card.getAttribute('id') || '';

                    return {
                        job_id: jobId,
                        title: titleEl ? titleEl.innerText.trim() : '',
                        company: compEl ? compEl.innerText.trim() : '',
                        location: locEl ? locEl.innerText.trim() : '',
                        experience: expEl ? expEl.innerText.trim() : '',
                        salary: salEl ? salEl.innerText.trim() : '',
                        url: linkEl ? linkEl.href : '',
                    };
                }).filter(j => j.title && j.company);
            }""")

            for item in (raw or [])[:max_results]:
                job = self._parse_raw(item, is_remote)
                if job:
                    jobs.append(job)

        except Exception as e:
            logger.error(f"Naukri search error: {e}")

        logger.info(f"Naukri scraped {len(jobs)} jobs for '{query}' in '{location}'")
        return jobs

    def _parse_raw(self, item: dict, default_remote: bool = False) -> Optional[ScrapedJob]:
        try:
            title = item.get("title", "").strip()
            company = item.get("company", "").strip()
            if not title or not company:
                return None

            job_id = item.get("job_id") or f"nk_{hash(title+company)}"
            url = item.get("url") or f"{self.BASE_URL}/job-listings-{job_id}"
            location = item.get("location", "").strip()
            is_remote = default_remote or "remote" in location.lower() or "wfh" in location.lower()

            sal_str = item.get("salary", "")
            sal_min, sal_max = self._parse_naukri_salary(sal_str)

            exp_str = item.get("experience", "")
            exp_label = self._exp_from_str(exp_str)

            return ScrapedJob(
                external_id=f"naukri_{job_id}",
                title=title,
                company=company,
                location=location or ("Remote" if is_remote else "India"),
                description="",
                url=url,
                apply_url=url,
                source="naukri",
                remote=is_remote,
                salary_min=sal_min,
                salary_max=sal_max,
                experience_level=exp_label,
            )
        except Exception as e:
            logger.debug(f"Naukri parse error: {e}")
            return None

    def _parse_naukri_salary(self, text: str):
        if not text:
            return None, None
        nums = re.findall(r"[\d.]+", text)
        if not nums:
            return None, None
        vals = [float(n) for n in nums[:2]]
        mult = 100000 if "lac" in text.lower() else 1000 if "k" in text.lower() else 1
        vals = [int(v * mult) for v in vals]
        return (vals[0], vals[-1]) if len(vals) >= 2 else (vals[0], vals[0])

    def _exp_from_str(self, text: str) -> str:
        nums = re.findall(r"\d+", text)
        if not nums:
            return "mid"
        mx = max(int(n) for n in nums)
        if mx <= 2:
            return "junior"
        if mx <= 5:
            return "mid"
        if mx <= 10:
            return "senior"
        return "lead"

    async def get_job_details(self, job_url: str) -> Dict[str, Any]:
        return {}
