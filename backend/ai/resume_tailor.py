"""
AI Resume Tailoring Engine.

For each job application, rewrites resume bullet points to emphasize
the skills and experience that match the specific job description.
Generates a tailored PDF resume on the fly.

This is the #1 feature that LazyApply/Simplify charge $30/mo for.
"""
import json
import re
from typing import Optional
from loguru import logger


TAILOR_PROMPT = """You are an expert resume writer specializing in ATS-optimized resumes.

Given a candidate's resume and a target job description, rewrite ONLY the
experience bullet points to better align with the job requirements.

ORIGINAL RESUME DATA:
{resume_json}

TARGET JOB:
Title: {job_title}
Company: {company}
Key requirements from job description:
{job_requirements}

Rules:
- Keep all facts TRUE — reword, reorder, and re-emphasize, do NOT fabricate
- Mirror keywords from the job description (ATS systems scan for exact matches)
- Lead with the most relevant achievements for THIS specific role
- Use strong action verbs and quantified results (%, $, numbers)
- If the candidate has a skill the job asks for, make sure it's prominently mentioned
- Keep each bullet under 25 words
- Do NOT change: name, email, phone, education, certifications — only experience bullets
- Return the full resume JSON with only "experience[].description" fields modified

Return ONLY valid JSON — same schema as input, with modified descriptions."""


KEYWORD_EXTRACT_PROMPT = """Extract the top 15 most important keywords/skills from this job description.
Rank them by importance (required > preferred > nice-to-have).

Job description:
{job_description}

Return ONLY a JSON array of strings, most important first:
["keyword1", "keyword2", ...]"""


ATS_SCORE_PROMPT = """Score this resume against the job description for ATS compatibility.

RESUME TEXT:
{resume_text}

JOB KEYWORDS (ranked by importance):
{keywords}

JOB DESCRIPTION:
{job_description}

Return ONLY valid JSON:
{{
  "ats_score": 85,
  "matched_keywords": ["Python", "AWS", "React"],
  "missing_critical": ["Kubernetes", "Terraform"],
  "missing_nice_to_have": ["Go", "gRPC"],
  "suggestions": [
    "Add 'Kubernetes' to your skills section",
    "Mention 'CI/CD pipeline' in your DevOps experience"
  ],
  "keyword_density": 0.72
}}"""


class ResumeTailor:
    def __init__(self, ai_client, provider: str = "anthropic"):
        self.client = ai_client
        self.provider = provider

    async def tailor_resume(self, resume_data: dict, job: dict) -> dict:
        """
        Rewrite resume experience bullets to match a specific job.
        Returns modified resume_data dict with tailored descriptions.
        """
        # Extract key requirements from job
        requirements = await self._extract_requirements(job.get("description", ""))

        prompt = TAILOR_PROMPT.format(
            resume_json=json.dumps(resume_data, indent=2)[:5000],
            job_title=job.get("title", ""),
            company=job.get("company", ""),
            job_requirements=requirements[:2000],
        )
        try:
            raw = await self._call_ai(prompt, max_tokens=2500)
            raw = re.sub(r"^```(?:json)?\n?", "", raw.strip())
            raw = re.sub(r"\n?```$", "", raw)
            tailored = json.loads(raw)
            logger.info(f"Resume tailored for {job.get('title')} @ {job.get('company')}")
            return tailored
        except Exception as e:
            logger.warning(f"Resume tailoring failed: {e}")
            return resume_data

    async def extract_keywords(self, job_description: str) -> list[str]:
        """Extract ranked keywords from a job description."""
        prompt = KEYWORD_EXTRACT_PROMPT.format(job_description=job_description[:4000])
        try:
            raw = await self._call_ai(prompt, max_tokens=300)
            raw = re.sub(r"^```(?:json)?\n?", "", raw.strip())
            raw = re.sub(r"\n?```$", "", raw)
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}")
            return []

    async def score_ats_compatibility(
        self, resume_text: str, job_description: str
    ) -> dict:
        """
        Score how well a resume will pass ATS keyword filters.
        Returns score 0-100 + actionable suggestions.
        """
        keywords = await self.extract_keywords(job_description)
        prompt = ATS_SCORE_PROMPT.format(
            resume_text=resume_text[:4000],
            keywords=json.dumps(keywords),
            job_description=job_description[:3000],
        )
        try:
            raw = await self._call_ai(prompt, max_tokens=600)
            raw = re.sub(r"^```(?:json)?\n?", "", raw.strip())
            raw = re.sub(r"\n?```$", "", raw)
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"ATS scoring failed: {e}")
            return {"ats_score": 0, "suggestions": ["Scoring unavailable"]}

    async def _extract_requirements(self, description: str) -> str:
        """Pull out structured requirements from a job description."""
        if not description:
            return ""
        prompt = f"""From this job description, extract a concise list of:
1. Required skills/technologies
2. Required years of experience
3. Required education
4. Preferred/nice-to-have skills
5. Key responsibilities

Be concise. Bullet points only.

Job description:
{description[:4000]}"""
        try:
            return await self._call_ai(prompt, max_tokens=500)
        except Exception:
            return description[:1000]

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
