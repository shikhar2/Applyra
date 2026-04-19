"""
Wellfound (formerly AngelList Talent) scraper.
Top job board for startup jobs — strong for AI/ML and full stack roles.
Uses their GraphQL API (same one the site uses).
"""
import asyncio
import hashlib
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
import httpx

from .base import BaseScraper, ScrapedJob

# Wellfound GraphQL endpoint
GRAPHQL_URL = "https://wellfound.com/graphql"

# GraphQL query to search startup jobs
JOBS_QUERY = """
query JobSearchQuery($query: String, $locationSlug: String, $jobTypes: [String], $page: Int, $perPage: Int) {
  talent {
    seoLandingPageJobSearchResults(
      query: $query
      locationSlug: $locationSlug
      jobTypes: $jobTypes
      page: $page
      perPage: $perPage
    ) {
      total
      jobListings {
        id
        title
        slug
        remote
        description
        primaryRoleTitle
        jobType
        salary
        equityMin
        equityMax
        currency
        createdAt
        url: liveJobUrl
        startup {
          id
          name
          slug
          locationTagList
          markets { displayName }
          fundingAmount
          teamSize
          isHiring
        }
      }
    }
  }
}
"""


class WellfoundScraper(BaseScraper):
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Referer": "https://wellfound.com/jobs",
        "Origin": "https://wellfound.com",
    }

    async def search_jobs(self, query: str, location: str = "Remote",
                          max_results: int = 50) -> List[ScrapedJob]:
        jobs = []
        page = 1
        per_page = 20

        # Map location to Wellfound slug
        loc_slug = self._location_slug(location)

        async with httpx.AsyncClient(headers=self.HEADERS, timeout=25) as client:
            while len(jobs) < max_results:
                payload = {
                    "query": JOBS_QUERY,
                    "variables": {
                        "query": query,
                        "locationSlug": loc_slug,
                        "jobTypes": ["full_time"],
                        "page": page,
                        "perPage": per_page,
                    }
                }
                try:
                    await self.rate_limiter.wait()
                    resp = await client.post(GRAPHQL_URL, json=payload)
                    if resp.status_code != 200:
                        self.rate_limiter.failure(resp.status_code)
                        logger.warning(f"Wellfound returned {resp.status_code}")
                        break
                    self.rate_limiter.success()

                    data = resp.json()
                    result = (data.get("data") or {}).get("talent", {}).get(
                        "seoLandingPageJobSearchResults", {}
                    )
                    items = result.get("jobListings", [])
                    if not items:
                        break

                    for item in items[:max_results - len(jobs)]:
                        job = self._parse_listing(item)
                        if job:
                            jobs.append(job)

                    total = result.get("total", 0)
                    if len(jobs) >= min(max_results, total) or len(items) < per_page:
                        break
                    page += 1
                    await asyncio.sleep(self.config.get("delay", 1.5))

                except Exception as e:
                    logger.error(f"Wellfound search error: {e}")
                    break

        logger.info(f"Wellfound scraped {len(jobs)} jobs for '{query}'")
        return jobs

    def _parse_listing(self, item: dict) -> Optional[ScrapedJob]:
        try:
            job_id = str(item.get("id", ""))
            title = item.get("title", "").strip()
            startup = item.get("startup") or {}
            company = startup.get("name", "").strip()
            locations = startup.get("locationTagList") or []
            location = ", ".join(locations[:2]) if locations else ""
            is_remote = item.get("remote", False) or "remote" in location.lower()

            url = item.get("url") or f"https://wellfound.com/jobs/{item.get('slug', job_id)}"

            # Salary
            sal_raw = item.get("salary", "")
            sal_min, sal_max = self._parse_salary(sal_raw)

            posted_str = item.get("createdAt", "")
            posted_at = None
            if posted_str:
                try:
                    posted_at = datetime.fromisoformat(posted_str.replace("Z", "+00:00"))
                except Exception:
                    pass

            markets = [m.get("displayName", "") for m in (startup.get("markets") or [])]

            return ScrapedJob(
                external_id=f"wellfound_{job_id}",
                title=title,
                company=company,
                location=location or ("Remote" if is_remote else "US"),
                description=item.get("description", ""),
                url=url,
                apply_url=url,
                source="wellfound",
                remote=is_remote,
                salary_min=sal_min,
                salary_max=sal_max,
                job_type="full-time",
                posted_at=posted_at,
                extra_data={
                    "markets": markets,
                    "team_size": startup.get("teamSize"),
                    "equity_min": item.get("equityMin"),
                    "equity_max": item.get("equityMax"),
                },
            )
        except Exception as e:
            logger.debug(f"Wellfound parse error: {e}")
            return None

    async def get_job_details(self, job_url: str) -> Dict[str, Any]:
        return {}  # Description already included in listing

    def _location_slug(self, location: str) -> str:
        """Map common location names to Wellfound slugs."""
        mapping = {
            "remote": "remote",
            "anywhere": "remote",
            "san francisco": "san-francisco-bay-area",
            "sf": "san-francisco-bay-area",
            "new york": "new-york",
            "nyc": "new-york",
            "los angeles": "los-angeles",
            "seattle": "seattle",
            "austin": "austin",
            "boston": "boston",
            "chicago": "chicago",
            "denver": "denver",
            "india": "india",
            "bangalore": "bengaluru",
            "bengaluru": "bengaluru",
            "mumbai": "mumbai",
            "london": "london",
            "berlin": "berlin",
            "toronto": "toronto",
        }
        return mapping.get(location.lower(), "remote")

    def _parse_salary(self, salary: any) -> tuple:
        if not salary:
            return None, None
        text = str(salary)
        nums = re.findall(r"[\d,]+", text)
        nums = [int(n.replace(",", "")) for n in nums]
        if not nums:
            return None, None
        if "k" in text.lower():
            nums = [n * 1000 if n < 1000 else n for n in nums]
        if len(nums) >= 2:
            return nums[0], nums[1]
        return nums[0], nums[0]
