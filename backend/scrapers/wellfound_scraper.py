"""
Wellfound (AngelList Talent) scraper — Playwright-based (GraphQL endpoint now requires auth).
"""
import asyncio
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from .base import BaseScraper, ScrapedJob


class WellfoundScraper(BaseScraper):
    BASE_URL = "https://wellfound.com"

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
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        self.page = await self.context.new_page()
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
            is_remote = location.lower() in ("remote", "anywhere", "")
            q = query.replace(" ", "+")
            url = f"{self.BASE_URL}/jobs?q={q}"
            if is_remote:
                url += "&remote=true"
            else:
                url += f"&location={location.replace(' ', '+')}"

            await self.page.goto(url, wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(self.config.get("delay", 3))

            # Scroll to load more results
            for _ in range(2):
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1.5)

            raw = await self.page.evaluate("""() => {
                // Try multiple possible card selectors
                const cards = document.querySelectorAll(
                    '[data-test="StartupResult"], ' +
                    '[class*="styles_component"], ' +
                    'div[class*="JobListing"], ' +
                    'div[class*="listing"]'
                );

                return Array.from(cards).map(card => {
                    const titleEl = card.querySelector(
                        '[class*="title"], [class*="role"], h2, h3, a[href*="/jobs/"]'
                    );
                    const companyEl = card.querySelector(
                        '[class*="company"], [class*="startup"], [class*="name"]'
                    );
                    const locEl = card.querySelector('[class*="location"], [class*="loc"]');
                    const linkEl = card.querySelector('a[href*="/jobs/"], a[href*="/l/"]');
                    const salaryEl = card.querySelector('[class*="salary"], [class*="comp"]');
                    const remoteEl = card.querySelector('[class*="remote"]');

                    return {
                        title: titleEl ? titleEl.innerText.trim() : '',
                        company: companyEl ? companyEl.innerText.trim() : '',
                        location: locEl ? locEl.innerText.trim() : '',
                        url: linkEl ? (linkEl.href.startsWith('http') ? linkEl.href : 'https://wellfound.com' + linkEl.getAttribute('href')) : '',
                        salary: salaryEl ? salaryEl.innerText.trim() : '',
                        is_remote: !!remoteEl || (locEl && locEl.innerText.toLowerCase().includes('remote')),
                    };
                }).filter(j => j.title && j.company);
            }""")

            seen = set()
            for item in (raw or []):
                key = f"{item.get('title', '')}-{item.get('company', '')}"
                if key in seen:
                    continue
                seen.add(key)
                job = self._parse_raw(item, is_remote)
                if job:
                    jobs.append(job)
                if len(jobs) >= max_results:
                    break

        except Exception as e:
            logger.error(f"Wellfound search error: {e}")

        logger.info(f"Wellfound scraped {len(jobs)} jobs for '{query}'")
        return jobs

    def _parse_raw(self, item: dict, default_remote: bool = False) -> Optional[ScrapedJob]:
        try:
            title = item.get("title", "").strip()
            company = item.get("company", "").strip()
            if not title or not company:
                return None

            url = item.get("url", "").strip() or f"{self.BASE_URL}/jobs"
            location = item.get("location", "").strip()
            is_remote = item.get("is_remote", default_remote) or "remote" in location.lower()

            sal_str = item.get("salary", "")
            sal_min, sal_max = self._parse_salary(sal_str)

            ext_id = f"wf_{abs(hash(title+company))}"

            return ScrapedJob(
                external_id=ext_id,
                title=title,
                company=company,
                location=location or ("Remote" if is_remote else "US"),
                description="",
                url=url,
                apply_url=url,
                source="wellfound",
                remote=is_remote,
                salary_min=sal_min,
                salary_max=sal_max,
                job_type="full-time",
            )
        except Exception as e:
            logger.debug(f"Wellfound parse error: {e}")
            return None

    def _parse_salary(self, text: str):
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
