"""
Indeed job scraper using Playwright (public search, no login needed).
"""
import asyncio
import hashlib
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseScraper, ScrapedJob


class IndeedScraper(BaseScraper):
    BASE_URL = "https://www.indeed.com"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.page = None

    async def __aenter__(self):
        from playwright.async_api import async_playwright
        self.playwright_ctx = async_playwright()
        pw = await self.playwright_ctx.__aenter__()
        self.browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox"],
        )
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        self.page = await self.context.new_page()
        return self

    async def __aexit__(self, *args):
        if self.browser:
            await self.browser.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=3, max=15))
    async def search_jobs(self, query: str, location: str = "Remote",
                          max_results: int = 50) -> List[ScrapedJob]:
        jobs = []
        start = 0

        while len(jobs) < max_results:
            url = (
                f"{self.BASE_URL}/jobs?q={query.replace(' ', '+')}"
                f"&l={location.replace(' ', '+')}"
                f"&fromage=7"  # Last 7 days
                f"&sort=date"
                f"&start={start}"
            )

            try:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(self.config.get("delay", 2.5))

                cards = await self.page.query_selector_all('[data-testid="slider_item"], .job_seen_beacon')
                if not cards:
                    break

                for card in cards[:max_results - len(jobs)]:
                    job = await self._parse_card(card)
                    if job:
                        jobs.append(job)

                start += 10
                if len(cards) < 10:
                    break

            except Exception as e:
                logger.warning(f"Indeed search failed at start={start}: {e}")
                break

        logger.info(f"Indeed scraped {len(jobs)} jobs for '{query}'")
        return jobs

    async def _parse_card(self, card) -> Optional[ScrapedJob]:
        try:
            title_el = await card.query_selector('[data-testid="jobTitle"] span, h2.jobTitle span')
            company_el = await card.query_selector('[data-testid="company-name"], .companyName')
            location_el = await card.query_selector('[data-testid="text-location"], .companyLocation')
            link_el = await card.query_selector('a[id^="job_"], a[data-jk]')

            title = (await title_el.inner_text()).strip() if title_el else ""
            company = (await company_el.inner_text()).strip() if company_el else ""
            location = (await location_el.inner_text()).strip() if location_el else ""

            if link_el:
                href = await link_el.get_attribute("href")
                job_url = href if href.startswith("http") else self.BASE_URL + href
                jk = await link_el.get_attribute("data-jk") or hashlib.md5(job_url.encode()).hexdigest()[:12]
            else:
                return None

            ext_id = f"indeed_{jk}"
            is_remote, norm_location = self.normalize_location(location)

            # Salary
            salary_el = await card.query_selector('[data-testid="attribute_snippet_testid"], .salary-snippet-container')
            salary_text = (await salary_el.inner_text()).strip() if salary_el else ""
            salary_min, salary_max = self._parse_salary(salary_text)

            return ScrapedJob(
                external_id=ext_id,
                title=title,
                company=company,
                location=norm_location,
                description="",
                url=job_url,
                apply_url=job_url,
                source="indeed",
                remote=is_remote,
                salary_min=salary_min,
                salary_max=salary_max,
            )
        except Exception as e:
            logger.debug(f"Failed to parse Indeed card: {e}")
            return None

    async def get_job_details(self, job_url: str) -> Dict[str, Any]:
        try:
            await self.page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(1.5)

            desc_el = await self.page.query_selector('#jobDescriptionText, .jobsearch-jobDescriptionText')
            description = (await desc_el.inner_text()).strip() if desc_el else ""

            return {"description": description, "easy_apply": False}
        except Exception as e:
            logger.warning(f"Indeed job details failed: {e}")
            return {}

    def _parse_salary(self, text: str) -> tuple:
        nums = re.findall(r"[\d,]+", text)
        nums = [int(n.replace(",", "")) for n in nums]
        if not nums:
            return None, None
        if "k" in text.lower():
            nums = [n * 1000 if n < 1000 else n for n in nums]
        if len(nums) >= 2:
            return nums[0], nums[1]
        return nums[0], nums[0]
