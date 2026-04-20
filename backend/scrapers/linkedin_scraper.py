"""
LinkedIn job scraper using Playwright.
Supports both public job search (no login) and Easy Apply (login required).
"""
import asyncio
import hashlib
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseScraper, ScrapedJob


class LinkedInScraper(BaseScraper):
    BASE_URL = "https://www.linkedin.com"
    JOBS_URL = "https://www.linkedin.com/jobs/search"

    def __init__(self, config: dict = None, playwright=None):
        super().__init__(config)
        self.playwright = playwright
        self.browser = None
        self.context = None
        self.page = None
        self.logged_in = False

    async def __aenter__(self):
        await self._start_browser()
        return self

    async def __aexit__(self, *args):
        await self._close_browser()

    async def _start_browser(self):
        from playwright.async_api import async_playwright
        self.playwright_ctx = async_playwright()
        pw = await self.playwright_ctx.__aenter__()
        self.browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        self.page = await self.context.new_page()
        try:
            from playwright_stealth import Stealth
            await Stealth().apply_stealth_async(self.page)
        except Exception:
            await self.page.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
            )

    async def _close_browser(self):
        if self.browser:
            await self.browser.close()

    async def login(self, email: str, password: str) -> bool:
        """Login to LinkedIn for Easy Apply access."""
        try:
            await self.page.goto(f"{self.BASE_URL}/login", wait_until="networkidle")
            await self.page.fill("#username", email)
            await self.page.fill("#password", password)
            await self.page.click('[type="submit"]')
            await self.page.wait_for_url("**/feed/**", timeout=15000)
            self.logged_in = True
            logger.info("LinkedIn login successful")
            return True
        except Exception as e:
            logger.error(f"LinkedIn login failed: {e}")
            return False

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def search_jobs(self, query: str, location: str = "Remote",
                          max_results: int = 50, days: int = 7) -> List[ScrapedJob]:
        jobs = []
        page_num = 0
        
        # Map days to LinkedIn f_TPR parameter
        tpr_map = {1: "r86400", 7: "r604800", 30: "r2592000"}
        tpr = tpr_map.get(days) or f"r{days * 86400}"

        while len(jobs) < max_results:
            offset = page_num * 25
            url = (
                f"{self.JOBS_URL}?keywords={query.replace(' ', '%20')}"
                f"&location={location.replace(' ', '%20')}"
                f"&f_TPR={tpr}"  # Dynamic time filtering
                f"&sortBy=DD"  # Sort by date
                f"&start={offset}"
            )

            try:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(self.config.get("delay", 2))

                # Wait for job cards
                await self.page.wait_for_selector(".job-search-card", timeout=10000)

                cards = await self.page.query_selector_all(".job-search-card")
                if not cards:
                    break

                for card in cards[:max_results - len(jobs)]:
                    job = await self._parse_job_card(card)
                    if job:
                        jobs.append(job)

                page_num += 1
                if len(cards) < 25:
                    break  # No more pages

            except Exception as e:
                logger.warning(f"LinkedIn search page {page_num} failed: {e}")
                break

        logger.info(f"LinkedIn scraped {len(jobs)} jobs for '{query}'")
        return jobs

    async def _parse_job_card(self, card) -> Optional[ScrapedJob]:
        try:
            title_el = await card.query_selector(".base-search-card__title")
            company_el = await card.query_selector(".base-search-card__subtitle")
            location_el = await card.query_selector(".job-search-card__location")
            link_el = await card.query_selector("a.base-card__full-link")
            listed_el = await card.query_selector("time")

            title = (await title_el.inner_text()).strip() if title_el else ""
            company = (await company_el.inner_text()).strip() if company_el else ""
            location = (await location_el.inner_text()).strip() if location_el else ""
            url = await link_el.get_attribute("href") if link_el else ""
            if url and "?" in url:
                url = url.split("?")[0]

            posted_str = await listed_el.get_attribute("datetime") if listed_el else None
            posted_at = datetime.fromisoformat(posted_str) if posted_str else None

            is_remote, norm_location = self.normalize_location(location)

            # Generate stable ID from URL
            ext_id = "li_" + hashlib.md5(url.encode()).hexdigest()[:12] if url else None
            if not ext_id or not title:
                return None

            return ScrapedJob(
                external_id=ext_id,
                title=title,
                company=company,
                location=norm_location,
                description="",  # Fetched separately
                url=url,
                apply_url=url,
                source="linkedin",
                remote=is_remote,
                posted_at=posted_at,
                easy_apply=False,  # Updated in get_job_details
            )
        except Exception as e:
            logger.debug(f"Failed to parse job card: {e}")
            return None

    async def get_job_details(self, job_url: str) -> Dict[str, Any]:
        """Fetch full job description and check for Easy Apply."""
        try:
            await self.page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(1.5)

            # Click "See more" if present
            try:
                see_more = await self.page.query_selector(".show-more-less-html__button")
                if see_more:
                    await see_more.click()
                    await asyncio.sleep(0.5)
            except Exception:
                pass

            desc_el = await self.page.query_selector(".show-more-less-html__markup, .job-details-jobs-unified-top-card__primary-description-container")
            description = (await desc_el.inner_text()).strip() if desc_el else ""

            # Check Easy Apply button
            easy_apply = False
            try:
                btn = await self.page.query_selector(".jobs-apply-button--top-card")
                if btn:
                    btn_text = (await btn.inner_text()).lower()
                    easy_apply = "easy apply" in btn_text
            except Exception:
                pass

            # Salary info
            salary_el = await self.page.query_selector(".compensation__salary")
            salary_text = (await salary_el.inner_text()).strip() if salary_el else ""
            salary_min, salary_max = self._parse_salary(salary_text)

            return {
                "description": description,
                "easy_apply": easy_apply,
                "salary_min": salary_min,
                "salary_max": salary_max,
            }
        except Exception as e:
            logger.warning(f"Failed to get job details for {job_url}: {e}")
            return {}

    def _parse_salary(self, salary_text: str) -> tuple:
        """Parse salary range from text like '$120K - $180K/yr'."""
        numbers = re.findall(r"[\d,]+", salary_text)
        numbers = [int(n.replace(",", "")) for n in numbers]
        if len(numbers) >= 2:
            a, b = numbers[0], numbers[1]
            # Handle K suffix
            if "k" in salary_text.lower():
                if a < 1000:
                    a *= 1000
                if b < 1000:
                    b *= 1000
            return a, b
        elif len(numbers) == 1:
            v = numbers[0]
            if v < 1000:
                v *= 1000
            return v, v
        return None, None

    async def easy_apply(self, job_url: str, resume_path: str,
                          answers: dict, cover_letter: str = "") -> bool:
        """Submit a LinkedIn Easy Apply application."""
        if not self.logged_in:
            logger.error("Must be logged in for Easy Apply")
            return False

        try:
            await self.page.goto(job_url, wait_until="networkidle", timeout=20000)
            await asyncio.sleep(2)

            # Click Easy Apply button
            apply_btn = await self.page.wait_for_selector(
                ".jobs-apply-button--top-card", timeout=5000
            )
            await apply_btn.click()
            await asyncio.sleep(1.5)

            # Handle multi-step modal
            max_steps = 10
            for step in range(max_steps):
                # Upload resume if file input appears
                file_input = await self.page.query_selector('input[type="file"]')
                if file_input:
                    await file_input.set_input_files(resume_path)
                    await asyncio.sleep(1)

                # Fill cover letter if textarea
                cover_letter_field = await self.page.query_selector(
                    'textarea[name*="cover"], textarea[placeholder*="cover"]'
                )
                if cover_letter_field and cover_letter:
                    await cover_letter_field.fill(cover_letter)

                # Auto-fill form fields using answers dict
                await self._fill_form_fields(answers)

                # Check for Next/Submit button
                next_btn = await self.page.query_selector(
                    'button[aria-label="Continue to next step"], '
                    'button[aria-label="Submit application"]'
                )
                if not next_btn:
                    # Try generic next button
                    buttons = await self.page.query_selector_all('button[type="button"]')
                    for btn in buttons:
                        text = (await btn.inner_text()).lower()
                        if text in ("next", "continue", "submit application", "review"):
                            next_btn = btn
                            break

                if next_btn:
                    btn_text = (await next_btn.inner_text()).lower()
                    await next_btn.click()
                    await asyncio.sleep(1.5)
                    if "submit" in btn_text:
                        logger.success(f"Application submitted for {job_url}")
                        return True
                else:
                    break

            logger.warning(f"Could not complete Easy Apply for {job_url}")
            return False

        except Exception as e:
            logger.error(f"Easy Apply failed for {job_url}: {e}")
            return False

    async def _fill_form_fields(self, answers: dict):
        """Auto-fill visible form inputs."""
        try:
            inputs = await self.page.query_selector_all("input[type='text'], input[type='tel'], input[type='number']")
            for inp in inputs:
                label = await self._get_input_label(inp)
                if label:
                    for key, value in answers.items():
                        if key.lower() in label.lower():
                            current = await inp.input_value()
                            if not current:
                                await inp.fill(str(value))
                            break

            selects = await self.page.query_selector_all("select")
            for sel in selects:
                label = await self._get_input_label(sel)
                if label:
                    for key, value in answers.items():
                        if key.lower() in label.lower():
                            await sel.select_option(label=str(value))
                            break
        except Exception as e:
            logger.debug(f"Form fill error: {e}")

    async def _get_input_label(self, element) -> str:
        try:
            label_id = await element.get_attribute("id")
            if label_id:
                label_el = await self.page.query_selector(f'label[for="{label_id}"]')
                if label_el:
                    return await label_el.inner_text()
            aria = await element.get_attribute("aria-label")
            return aria or ""
        except Exception:
            return ""
