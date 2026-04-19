"""
Glassdoor job scraper using their public jobs API endpoint.
"""
import asyncio
import hashlib
import re
from typing import List, Dict, Any, Optional
from loguru import logger
import httpx

from .base import BaseScraper, ScrapedJob


class GlassdoorScraper(BaseScraper):
    """Uses Glassdoor's undocumented jobs API."""
    BASE_URL = "https://www.glassdoor.com"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://www.glassdoor.com/",
        }

    async def search_jobs(self, query: str, location: str = "Remote",
                          max_results: int = 50) -> List[ScrapedJob]:
        jobs = []
        async with httpx.AsyncClient(headers=self.headers, timeout=20) as client:
            page = 1
            while len(jobs) < max_results:
                try:
                    url = (
                        f"{self.BASE_URL}/api/jobs/listing-search/job-listing"
                        f"?keyword={query.replace(' ', '+')}"
                        f"&location={location.replace(' ', '+')}"
                        f"&fromAge=7"
                        f"&pageSize=30"
                        f"&page={page}"
                    )
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        break
                    data = resp.json()
                    listing = data.get("data", {}).get("jobListings", [])
                    if not listing:
                        break
                    for item in listing[:max_results - len(jobs)]:
                        job = self._parse_listing(item)
                        if job:
                            jobs.append(job)
                    page += 1
                    if len(listing) < 30:
                        break
                    await asyncio.sleep(self.config.get("delay", 2))
                except Exception as e:
                    logger.warning(f"Glassdoor search failed: {e}")
                    break

        logger.info(f"Glassdoor scraped {len(jobs)} jobs for '{query}'")
        return jobs

    def _parse_listing(self, item: dict) -> Optional[ScrapedJob]:
        try:
            jid = str(item.get("jobListingId", ""))
            title = item.get("jobTitleText", "")
            company = item.get("employerName", "")
            location = item.get("locationName", "")
            url = f"{self.BASE_URL}/job-listing/j?jl={jid}"
            apply_url = item.get("applyUrl") or url
            is_remote, norm_location = self.normalize_location(location)

            # Salary
            pay = item.get("payPeriodAdjustedPay", {})
            sal_min = pay.get("p10")
            sal_max = pay.get("p90")

            return ScrapedJob(
                external_id=f"gd_{jid}",
                title=title,
                company=company,
                location=norm_location,
                description=item.get("jobDescription", ""),
                url=url,
                apply_url=apply_url,
                source="glassdoor",
                remote=is_remote,
                salary_min=int(sal_min) if sal_min else None,
                salary_max=int(sal_max) if sal_max else None,
            )
        except Exception as e:
            logger.debug(f"Glassdoor parse error: {e}")
            return None

    async def get_job_details(self, job_url: str) -> Dict[str, Any]:
        return {}  # Description included in listing
