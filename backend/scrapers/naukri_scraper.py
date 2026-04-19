"""
Naukri.com scraper — India's largest job portal.
Uses Naukri's internal API (same one their website calls).
No login required for search. Supports location, experience, salary filters.
"""
import asyncio
import hashlib
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import httpx

from .base import BaseScraper, ScrapedJob


class NaukriScraper(BaseScraper):
    """
    Scrapes Naukri via their internal REST API.
    Works without login for job listings; login needed for Easy Apply.
    """
    SEARCH_URL = "https://www.naukri.com/jobapi/v3/search"
    JOB_DETAIL_URL = "https://www.naukri.com/jobapi/v4/job/{job_id}"

    BASE_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    }

    API_HEADERS = {
        **BASE_HEADERS,
        "Accept": "application/json, text/plain, */*",
        "appid": "109",
        "systemid": "Naukri",
        "clientid": "d3skt0p",
        "gid": "LOCATION,INDUSTRY,EDUCATION,FAREA_ROLE",
        "Referer": "https://www.naukri.com/",
        "Origin": "https://www.naukri.com",
        "x-requested-with": "XMLHttpRequest",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    # Naukri experience level codes
    EXP_MAP = {
        "fresher": (0, 0),
        "junior": (0, 2),
        "mid": (2, 5),
        "senior": (5, 10),
        "lead": (8, 15),
    }

    async def search_jobs(self, query: str, location: str = "India",
                          max_results: int = 50, days: int = 7) -> List[ScrapedJob]:
        jobs = []
        page = 1
        page_size = 20

        async with httpx.AsyncClient(headers=self.BASE_HEADERS, timeout=20, follow_redirects=True) as client:
            # Seed session cookies so the API accepts the request
            try:
                await client.get("https://www.naukri.com/", headers={"Accept": "text/html,application/xhtml+xml,*/*"})
            except Exception:
                pass
            client.headers.update(self.API_HEADERS)

            while len(jobs) < max_results:
                params = {
                    "noOfResults": page_size,
                    "urlType": "search_by_keyword",
                    "searchType": "adv",
                    "keyword": query,
                    "location": location if location.lower() not in ("remote", "anywhere") else "",
                    "jobAge": days,          # Dynamic job age in days
                    "experience": 2,       # Min 2 years (adjust via config)
                    "pageNo": page,
                    "sort": "1",          # Sort by date
                    "k": query,
                    "l": location if location.lower() not in ("remote", "anywhere") else "",
                    "nignbevent_src": "jobsearchDeskGNB",
                }
                if location.lower() in ("remote", "anywhere", "work from home"):
                    params["wfhType"] = "1"  # Work from home flag

                try:
                    resp = await self._safe_get(client, self.SEARCH_URL, params=params)
                    if resp.status_code != 200:
                        logger.warning(f"Naukri returned {resp.status_code}")
                        if self.rate_limiter.is_blocked:
                            break
                        continue

                    data = resp.json()
                    job_list = data.get("jobDetails", [])
                    if not job_list:
                        break

                    for item in job_list[:max_results - len(jobs)]:
                        job = self._parse_job(item)
                        if job:
                            jobs.append(job)

                    if len(job_list) < page_size:
                        break
                    page += 1
                    await asyncio.sleep(self.config.get("delay", 1.5))

                except Exception as e:
                    logger.error(f"Naukri search error page {page}: {e}")
                    break

        logger.info(f"Naukri scraped {len(jobs)} jobs for '{query}' in '{location}'")
        return jobs

    def _parse_job(self, item: dict) -> Optional[ScrapedJob]:
        try:
            job_id = str(item.get("jobId", ""))
            title = item.get("title", "").strip()
            company = item.get("companyName", "").strip()
            location_raw = ", ".join(item.get("placeholders", {}).get("location", "").split(",")[:2])

            is_remote = bool(item.get("isWfhJob")) or "remote" in location_raw.lower()
            url = item.get("jdURL") or f"https://www.naukri.com/job-listings-{job_id}"
            apply_url = item.get("applyNowLink") or url

            # Salary
            salary_str = item.get("placeholders", {}).get("salary", "")
            sal_min, sal_max = self._parse_naukri_salary(salary_str)

            # Posted date
            posted_epoch = item.get("createdDate")
            posted_at = datetime.fromtimestamp(posted_epoch / 1000) if posted_epoch else None

            # Experience
            exp_min = item.get("minimumExperience", 0)
            exp_max = item.get("maximumExperience", 0)
            exp_label = self._exp_label(exp_min, exp_max)

            description = item.get("jobDescription", "") or ""

            return ScrapedJob(
                external_id=f"naukri_{job_id}",
                title=title,
                company=company,
                location=location_raw or ("Remote" if is_remote else "India"),
                description=description,
                url=url,
                apply_url=apply_url,
                source="naukri",
                remote=is_remote,
                salary_min=sal_min,
                salary_max=sal_max,
                experience_level=exp_label,
                posted_at=posted_at,
                extra_data={
                    "skills": item.get("tagsAndSkills", ""),
                    "experience": f"{exp_min}-{exp_max} yrs",
                },
            )
        except Exception as e:
            logger.debug(f"Naukri parse error: {e}")
            return None

    async def get_job_details(self, job_url: str) -> Dict[str, Any]:
        """Fetch full job description from Naukri API."""
        job_id = self._extract_job_id(job_url)
        if not job_id:
            return {}
        try:
            async with httpx.AsyncClient(headers=self.API_HEADERS, timeout=15) as client:
                resp = await client.get(self.JOB_DETAIL_URL.format(job_id=job_id))
                if resp.status_code != 200:
                    return {}
                data = resp.json().get("jobDetails", {})
                return {
                    "description": data.get("jobDescription", ""),
                    "easy_apply": bool(data.get("applyNowLink")),
                }
        except Exception as e:
            logger.warning(f"Naukri detail fetch failed: {e}")
            return {}

    def _extract_job_id(self, url: str) -> Optional[str]:
        m = re.search(r"(\d{7,12})", url)
        return m.group(1) if m else None

    def _parse_naukri_salary(self, salary_str: str) -> tuple:
        """Parse Naukri salary like '8-15 Lacs PA' → (800000, 1500000)."""
        if not salary_str:
            return None, None
        nums = re.findall(r"[\d.]+", salary_str)
        if not nums:
            return None, None
        vals = [float(n) for n in nums[:2]]
        # Convert Lacs to absolute
        multiplier = 100000 if "lac" in salary_str.lower() else 1000 if "k" in salary_str.lower() else 1
        vals = [int(v * multiplier) for v in vals]
        if len(vals) == 2:
            return vals[0], vals[1]
        return vals[0], vals[0]

    def _exp_label(self, mn: int, mx: int) -> str:
        if mx <= 2:
            return "junior"
        if mx <= 5:
            return "mid"
        if mx <= 10:
            return "senior"
        return "lead"
