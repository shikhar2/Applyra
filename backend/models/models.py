from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text,
    ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from backend.db.database import Base


class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    REVIEW = "review"       # HITL: awaiting human approval before applying
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    SKIPPED = "skipped"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    OFFER = "offer"


class JobSource(str, enum.Enum):
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    NAUKRI = "naukri"
    DICE = "dice"
    WELLFOUND = "wellfound"
    LEVELS_FYI = "levels_fyi"
    MANUAL = "manual"


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    file_path = Column(String(500))
    content_text = Column(Text)
    parsed_data = Column(JSON)  # skills, experience, education, etc.
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    applications = relationship("Application", back_populates="resume", cascade="all, delete-orphan")


class JobProfile(Base):
    """Target job profile configuration."""
    __tablename__ = "job_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # e.g. "Full Stack Engineer"
    target_roles = Column(JSON)  # ["Full Stack", "Software Engineer", "Backend"]
    target_locations = Column(JSON)  # ["Remote", "New York", "San Francisco"]
    remote_only = Column(Boolean, default=False)
    min_salary = Column(Integer, nullable=True)
    max_salary = Column(Integer, nullable=True)
    salary_currency = Column(String(10), default="USD")  # "USD" or "INR"
    min_years_experience = Column(Integer, nullable=True)  # e.g. 3
    max_years_experience = Column(Integer, nullable=True)  # e.g. 8, null = no cap
    experience_levels = Column(JSON)  # ["mid", "senior"]
    company_size = Column(JSON)  # ["startup", "mid", "enterprise"]
    excluded_companies = Column(JSON, default=list)
    required_keywords = Column(JSON, default=list)
    excluded_keywords = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    searches = relationship("JobSearch", back_populates="profile")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), unique=True, index=True)
    title = Column(String(500), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255))
    description = Column(Text)
    requirements = Column(Text)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    job_type = Column(String(50))  # full-time, part-time, contract
    experience_level = Column(String(50))
    remote = Column(Boolean, default=False)
    source = Column(SAEnum(JobSource), nullable=False)
    url = Column(String(1000))
    apply_url = Column(String(1000))
    posted_at = Column(DateTime, nullable=True)
    discovered_at = Column(DateTime, default=func.now())
    easy_apply = Column(Boolean, default=False)  # LinkedIn Easy Apply etc.
    extra_data = Column(JSON, default=dict)

    applications = relationship("Application", back_populates="job")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    status = Column(SAEnum(ApplicationStatus), default=ApplicationStatus.PENDING)
    match_score = Column(Float, default=0.0)
    match_explanation = Column(Text)
    cover_letter = Column(Text)
    answers = Column(JSON, default=dict)  # Q&A for application forms
    applied_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    tailored_resume_path = Column(String(500), nullable=True)
    is_top_tier = Column(Boolean, default=False)
    deep_analysis = Column(JSON, nullable=True)   # structured 7-block analysis from deep scorer
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    job = relationship("Job", back_populates="applications")
    resume = relationship("Resume", back_populates="applications")


class JobSearch(Base):
    __tablename__ = "job_searches"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("job_profiles.id"))
    source = Column(SAEnum(JobSource))
    query = Column(String(500))
    results_count = Column(Integer, default=0)
    new_jobs_count = Column(Integer, default=0)
    ran_at = Column(DateTime, default=func.now())
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    profile = relationship("JobProfile", back_populates="searches")


class DailyStats(Base):
    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), unique=True)  # YYYY-MM-DD
    jobs_discovered = Column(Integer, default=0)
    applications_sent = Column(Integer, default=0)
    applications_failed = Column(Integer, default=0)
    applications_skipped = Column(Integer, default=0)
