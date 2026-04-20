"""
Quick scraper health check — tests each job board with a small search.
Run: source venv/bin/activate && python scripts/test_scrapers.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.scrapers import SCRAPERS, BROWSER_SCRAPERS, HTTP_SCRAPERS

ROLE = "Software Engineer"
LOCATION = "Remote"
MAX = 5
CFG = {"delay": 1.0}

RESULTS = {}


TIMEOUT = 30  # seconds per scraper

async def test_scraper(name: str):
    cls = SCRAPERS[name]
    try:
        print(f"\n[{name.upper()}] Testing...")
        async def _run():
            if name in BROWSER_SCRAPERS:
                async with cls(CFG) as scraper:
                    return await scraper.search_jobs(ROLE, LOCATION, max_results=MAX)
            else:
                scraper = cls(CFG)
                return await scraper.search_jobs(ROLE, LOCATION, max_results=MAX)

        jobs = await asyncio.wait_for(_run(), timeout=TIMEOUT)
        count = len(jobs)
        sample = jobs[0].title if jobs else "—"
        RESULTS[name] = {"status": "✅ WORKING", "count": count, "sample": sample}
        print(f"  → {count} jobs found. Sample: {sample}")
    except asyncio.TimeoutError:
        RESULTS[name] = {"status": "⏱  TIMEOUT", "count": 0, "error": f">{TIMEOUT}s"}
        print(f"  → TIMED OUT after {TIMEOUT}s")
    except Exception as e:
        RESULTS[name] = {"status": "❌ FAILED", "count": 0, "error": str(e)[:120]}
        print(f"  → FAILED: {e}")


async def main():
    print("=" * 60)
    print("APPLYRA SCRAPER HEALTH CHECK")
    print(f"Query: '{ROLE}' in '{LOCATION}' (max {MAX} results each)")
    print("=" * 60)

    # HTTP scrapers first (faster)
    print("\n--- HTTP Scrapers (no browser) ---")
    for name in HTTP_SCRAPERS:
        await test_scraper(name)

    # Browser scrapers
    print("\n--- Browser Scrapers (Playwright) ---")
    for name in BROWSER_SCRAPERS:
        await test_scraper(name)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, r in RESULTS.items():
        if r["status"].startswith("✅"):
            print(f"  {r['status']}  {name.upper():12s}  {r['count']} jobs  |  {r.get('sample', '')}")
        else:
            print(f"  {r['status']}  {name.upper():12s}  {r.get('error', '')}")
    print()


asyncio.run(main())
