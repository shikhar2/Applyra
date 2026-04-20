from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Applyra"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/applyra.db"

    # AI
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    XAI_API_KEY: Optional[str] = None
    AI_PROVIDER: str = "gemini"  # "gemini", "anthropic", "openai", "groq", or "xai"
    AI_MODEL: str = "gemini-1.5-flash"
    
    # Cost Optimization
    SIMPLER_AI_PROVIDER: str = "groq" # Use for simpler tasks (answers, CL) if available

    # Job Search
    LINKEDIN_EMAIL: Optional[str] = None
    LINKEDIN_PASSWORD: Optional[str] = None
    NAUKRI_EMAIL: Optional[str] = None
    NAUKRI_PASSWORD: Optional[str] = None
    INDEED_API_KEY: Optional[str] = None

    # Application Settings
    MAX_APPLICATIONS_PER_DAY: int = 25
    MIN_MATCH_SCORE: float = 0.70        # minimum match to queue for applying
    HITL_REVIEW_THRESHOLD: float = 0.85  # above this → deep analysis + human review queue
    AUTO_APPLY_ENABLED: bool = False  # Safety: off by default
    DRY_RUN: bool = True  # Simulate without actually submitting

    # Scheduler
    SCHEDULER_INTERVAL_MINUTES: int = 60

    # Redis (for Celery)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Email Notifications
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    NOTIFY_EMAIL: Optional[str] = None

    # Proxy (for scraping)
    PROXY_URL: Optional[str] = None

    # Rate limiting
    SCRAPER_DELAY_SECONDS: float = 1.0
    MAX_RETRIES: int = 3

    # Concurrency
    MAX_AI_CONCURRENCY: int = 8       # parallel AI scoring/generation calls
    MAX_BROWSER_SCRAPERS: int = 2     # concurrent browser scraper instances
    SEARCH_BATCH_SIZE: int = 20       # jobs per batch (ingest → score → apply cycle)

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
