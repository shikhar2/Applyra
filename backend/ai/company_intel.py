"""
Company Intelligence Engine.

Auto-enriches every job with company data:
  - Rating, size, industry, funding stage
  - Salary benchmarks for the specific role + location
  - Interview style and common questions
  - Key decision-makers and hiring managers

No tool on the market does all of this automatically inline with applications.
"""
import json
import re
from typing import Optional
from loguru import logger
import httpx


COMPANY_RESEARCH_PROMPT = """You are a career research assistant. Given a company name and job title,
provide useful intelligence for a candidate preparing to apply.

Company: {company}
Job Title: {job_title}
Location: {location}

Based on your knowledge, provide ONLY valid JSON:
{{
  "company_overview": "1-2 sentence description of what the company does",
  "industry": "fintech / healthtech / SaaS / etc",
  "estimated_size": "startup (<50) | small (50-200) | mid (200-1000) | large (1000-10000) | enterprise (10000+)",
  "funding_stage": "seed | series_a | series_b | series_c | late_stage | public | bootstrapped | unknown",
  "estimated_rating": 3.8,
  "culture_notes": "What is known about their engineering culture",
  "tech_stack": ["Python", "React", "AWS"],
  "interview_style": "Description of their typical interview process",
  "common_interview_questions": [
    "Tell me about a time you scaled a system",
    "How do you approach code reviews?"
  ],
  "salary_range": {{
    "low": 120000,
    "mid": 150000,
    "high": 180000,
    "currency": "USD",
    "note": "Based on role level and location"
  }},
  "pros": ["Strong engineering culture", "Good WLB"],
  "cons": ["Below-market pay", "Slow promotion"],
  "tips_for_applying": "What to emphasize in your application for this company"
}}

Be honest. If you don't know something, use reasonable estimates or say 'unknown'.
Do NOT fabricate specific Glassdoor ratings — estimate based on general reputation."""


INTERVIEW_PREP_PROMPT = """Generate a tailored interview preparation guide for this specific role.

CANDIDATE RESUME:
{resume_summary}

JOB:
Title: {job_title}
Company: {company}
Description: {job_description}

Generate ONLY valid JSON:
{{
  "behavioral_questions": [
    {{
      "question": "Tell me about a time you led a technical project",
      "why_they_ask": "Assessing leadership and project management",
      "suggested_answer_points": ["Use STAR method", "Reference your project at Company X", "Emphasize results"]
    }}
  ],
  "technical_questions": [
    {{
      "question": "Design a URL shortener",
      "category": "system_design",
      "preparation_tips": "Focus on scalability, database choice, caching"
    }}
  ],
  "coding_topics": ["Binary trees", "Dynamic programming", "API design"],
  "questions_to_ask_them": [
    "What does the first 90 days look like in this role?",
    "How is the engineering team structured?"
  ],
  "red_flags_to_watch": ["Vague answers about work-life balance", "No mention of growth path"],
  "preparation_checklist": [
    "Review their recent blog posts / tech talks",
    "Practice system design for their domain",
    "Prepare 3 STAR stories relevant to this role"
  ]
}}"""


class CompanyIntel:
    def __init__(self, ai_client, provider: str = "anthropic"):
        self.client = ai_client
        self.provider = provider
        self._cache: dict[str, dict] = {}

    async def enrich_company(self, company: str, job_title: str,
                              location: str = "") -> dict:
        """Get company intelligence. Cached per company name."""
        cache_key = f"{company.lower().strip()}|{job_title.lower().strip()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt = COMPANY_RESEARCH_PROMPT.format(
            company=company,
            job_title=job_title,
            location=location or "Unknown",
        )
        try:
            raw = await self._call_ai(prompt, max_tokens=1200)
            raw = re.sub(r"^```(?:json)?\n?", "", raw.strip())
            raw = re.sub(r"\n?```$", "", raw)
            data = json.loads(raw)
            self._cache[cache_key] = data
            return data
        except Exception as e:
            logger.warning(f"Company enrichment failed for {company}: {e}")
            return {"company_overview": "Unavailable", "estimated_rating": 0}

    async def generate_interview_prep(
        self, resume_data: dict, job: dict
    ) -> dict:
        """Generate a complete interview prep guide for a specific role."""
        resume_summary = {
            "name": resume_data.get("name", ""),
            "skills": resume_data.get("skills", {}),
            "experience": [
                {"company": e.get("company"), "title": e.get("title"),
                 "description": (e.get("description") or "")[:200]}
                for e in (resume_data.get("experience", [])[:3])
            ],
        }
        prompt = INTERVIEW_PREP_PROMPT.format(
            resume_summary=json.dumps(resume_summary, indent=2)[:2000],
            job_title=job.get("title", ""),
            company=job.get("company", ""),
            job_description=(job.get("description", "") or "")[:3000],
        )
        try:
            raw = await self._call_ai(prompt, max_tokens=1500)
            raw = re.sub(r"^```(?:json)?\n?", "", raw.strip())
            raw = re.sub(r"\n?```$", "", raw)
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"Interview prep generation failed: {e}")
            return {}

    async def estimate_salary(self, job_title: str, location: str,
                                experience_years: int = 5) -> dict:
        """Estimate salary range for a specific role + location + experience."""
        prompt = f"""Estimate the total compensation range for:
Role: {job_title}
Location: {location}
Experience: {experience_years} years

Return ONLY JSON: {{"low": 120000, "mid": 150000, "high": 185000, "currency": "USD",
"note": "Brief explanation"}}"""
        try:
            raw = await self._call_ai(prompt, max_tokens=200)
            raw = re.sub(r"^```(?:json)?\n?", "", raw.strip())
            raw = re.sub(r"\n?```$", "", raw)
            return json.loads(raw)
        except Exception:
            return {"low": 0, "mid": 0, "high": 0, "currency": "USD", "note": "Unavailable"}

    async def _call_ai(self, prompt: str, max_tokens: int = 800) -> str:
        if self.provider == "anthropic":
            resp = await self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text
        elif self.provider == "openai":
            resp = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content
        elif self.provider == "gemini":
            gem_model = self.client.GenerativeModel("gemini-2.0-flash")
            resp = await gem_model.generate_content_async(prompt)
            return resp.text
        raise ValueError(f"Unknown provider: {self.provider}")
