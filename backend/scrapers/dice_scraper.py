"""
Dice.com scraper — top US tech job board.
Uses Dice's public search API (same endpoint their site calls).
"""
import asyncio
import hashlib
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
import httpx

from .base import BaseScraper, ScrapedJob


class DiceScraper(BaseScraper):
    SEARCH_URL = "https://job-search-api.svc.dhigroupinc.com/v1/dice/jobs/search"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "x-api-key": "1YAt0R9wBg4WfsF9VB2778F5CHLAPMVW3WAZcKd8",  # Public key from Dice site
        "Referer": "https://www.dice.com/",
    }

    async def search_jobs(self, query: str, location: str = "Remote",
                          max_results: int = 50) -> List[ScrapedJob]:
        jobs = []
        page = 1
        page_size = 20

        async with httpx.AsyncClient(headers=self.HEADERS, timeout=20) as client:
            while len(jobs) < max_results:
                params = {
                    "q": query,
                    "countryCode2": "US",
                    "radius": "30",
                    "radiusUnit": "mi",
                    "page": page,
                    "pageSize": page_size,
                    "facets": "employmentType|postedDate|workFromHomeAvailability|employerType|easyApply|isRemote",
                    "fields": "id,guid,summary,title,postedDate,modifiedDate,jobLocation,salary,clientBrandId,companyPageUrl,companyLogoUrl,positionId,companyName,employmentType,isHighlighted,score,easyApply,employerType,hitCount,isRemote,jobLink",
                    "datePosted": "ONE_WEEK",
                    "sort": "-score",
                    "language": "en",
                }
                if location.lower() in ("remote", "anywhere"):
                    params["isRemote"] = "true"
                else:
                    params["location"] = location

                try:
                    resp = await self._safe_get(client, self.SEARCH_URL, params=params)
                    if resp.status_code != 200:
                        logger.warning(f"Dice returned {resp.status_code}")
                        break

                    data = resp.json()
                    items = data.get("data", [])
                    if not items:
                        break

                    for item in items[:max_results - len(jobs)]:
                        job = self._parse_job(item)
                        if job:
                            jobs.append(job)

                    total = data.get("meta", {}).get("totalHits", 0)
                    if len(jobs) >= min(max_results, total):
                        break
                    page += 1
                    await asyncio.sleep(self.config.get("delay", 1.5))

                except Exception as e:
                    logger.error(f"Dice search error page {page}: {e}")
                    break

        logger.info(f"Dice scraped {len(jobs)} jobs for '{query}'")
        return jobs

    def _parse_job(self, item: dict) -> Optional[ScrapedJob]:
        try:
            job_id = item.get("id", "") or item.get("guid", "")
            title = item.get("title", "").strip()
            company = item.get("companyName", "").strip()

            loc_obj = item.get("jobLocation", {})
            location = loc_obj.get("displayName", "") if isinstance(loc_obj, dict) else str(loc_obj)
            is_remote = item.get("isRemote", False) or "remote" in location.lower()

            job_link = item.get("jobLink", "")
            url = f"https://www.dice.com/job-detail/{job_id}" if not job_link else job_link

            salary_raw = item.get("salary", "")
            sal_min, sal_max = self._parse_salary_text(salary_raw)

            posted_str = item.get("postedDate", "")
            posted_at = None
            if posted_str:
                try:
                    posted_at = datetime.fromisoformat(posted_str.replace("Z", "+00:00"))
                except Exception:
                    pass

            easy_apply = bool(item.get("easyApply"))
            emp_type = item.get("employmentType", ["FULLTIME"])
            job_type = "full-time" if "FULLTIME" in str(emp_type) else "contract"

            return ScrapedJob(
                external_id=f"dice_{job_id}",
                title=title,
                company=company,
                location=location or ("Remote" if is_remote else "US"),
                description=item.get("summary", ""),
                url=url,
                apply_url=url,
                source="dice",
                remote=is_remote,
                salary_min=sal_min,
                salary_max=sal_max,
                job_type=job_type,
                easy_apply=easy_apply,
                posted_at=posted_at,
            )
        except Exception as e:
            logger.debug(f"Dice parse error: {e}")
            return None

    async def get_job_details(self, job_url: str) -> Dict[str, Any]:
        """Dice job details via their API."""
        job_id = job_url.rstrip("/").split("/")[-1]
        try:
            async with httpx.AsyncClient(headers=self.HEADERS, timeout=15) as client:
                resp = await client.get(
                    f"https://job-search-api.svc.dhigroupinc.com/v1/dice/jobs/{job_id}"
                )
                if resp.status_code != 200:
                    return {}
                data = resp.json()
                return {
                    "description": data.get("jobDescription", ""),
                    "easy_apply": data.get("easyApply", False),
                }
        except Exception as e:
            logger.warning(f"Dice detail fetch failed: {e}")
            return {}

    def _parse_salary_text(self, salary: str) -> tuple:
        if not salary:
            return None, None
        nums = re.findall(r"[\d,]+", str(salary))
        nums = [int(n.replace(",", "")) for n in nums]
        if not nums:
            return None, None
        if "k" in salary.lower():
            nums = [n * 1000 if n < 1000 else n for n in nums]
        if len(nums) >= 2:
            return nums[0], nums[1]
        return nums[0], nums[0]
