from .linkedin_scraper import LinkedInScraper
from .indeed_scraper import IndeedScraper
from .glassdoor_scraper import GlassdoorScraper
from .naukri_scraper import NaukriScraper
from .dice_scraper import DiceScraper
from .wellfound_scraper import WellfoundScraper

SCRAPERS = {
    "linkedin": LinkedInScraper,
    "indeed": IndeedScraper,
    "glassdoor": GlassdoorScraper,
    "naukri": NaukriScraper,
    "dice": DiceScraper,
    "wellfound": WellfoundScraper,
}

# Scrapers that use Playwright (need browser launch)
BROWSER_SCRAPERS = {"linkedin", "indeed"}

# Scrapers that use plain HTTP (faster, no browser needed)
HTTP_SCRAPERS = {"glassdoor", "naukri", "dice", "wellfound"}

__all__ = [
    "LinkedInScraper", "IndeedScraper", "GlassdoorScraper",
    "NaukriScraper", "DiceScraper", "WellfoundScraper",
    "SCRAPERS", "BROWSER_SCRAPERS", "HTTP_SCRAPERS",
]
