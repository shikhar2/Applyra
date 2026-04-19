"""
AI-powered job-resume matching engine — cost-optimized & high performance.

Optimizations:
- Smart Routing: Complex tasks (scoring) go to Gemini/Claude, simple tasks (QA) go to Groq/Flash.
- Prompt Compression: Removed verbosity to save tokens.
- Structured Trimming: Drastic reduction in payload size for large resumes.
"""
import json
import re
from typing import Tuple, Dict, Any
from loguru import logger
from backend.core.config import settings
from backend.ai.client import get_ai_client

# ── Optimized Prompts (Less Tokens) ───────────────────────────────────────

MATCH_PROMPT = """Score resume match for job.
RESUME: {resume_json}
JOB: {job_title} @ {company}
DESC: {job_description}

JSON ONLY:
{{
  "score": 0.0-1.0,
  "verdict": "strong_match|partial|weak",
  "matching_skills": [],
  "missing_skills": [],
  "explanation": "concise reasoning",
  "apply_recommendation": bool
}}"""

DEEP_ANALYSIS_PROMPT = """You are an expert job application analyst. Evaluate this candidate's fit for this job across 7 blocks. Be concise but specific.

CANDIDATE RESUME:
{resume_json}

JOB: {job_title} @ {company}
DESCRIPTION: {job_description}

Return ONLY valid JSON with this exact structure:
{{
  "score": <0.0-1.0 overall fit>,
  "verdict": "<strong_match|partial|weak>",
  "apply_recommendation": <true|false>,
  "archetype": "<Platform/MLOps|Agentic/AI|Technical PM|Solutions Architect|Forward Deployed|Full Stack|Backend|Frontend|Data|Other>",
  "blocks": {{
    "role_summary": {{
      "domain": "<e.g. Backend Infrastructure>",
      "seniority": "<junior|mid|senior|staff|principal>",
      "team_size": "<startup|small|mid|large|enterprise>",
      "remote": "<remote|hybrid|onsite|unknown>"
    }},
    "cv_match": {{
      "matching_skills": ["skill1", "skill2"],
      "gaps": ["gap1", "gap2"],
      "gap_severity": "<none|minor|major|dealbreaker>",
      "mitigation": "<how candidate can frame gaps>"
    }},
    "level_strategy": {{
      "fit": "<undershoot|good_fit|stretch>",
      "positioning_tip": "<one sentence on how to position>"
    }},
    "compensation": {{
      "likely_range": "<e.g. $120k-$160k or unknown>",
      "fit": "<below|within|above|unknown>"
    }},
    "legitimacy": {{
      "signals": "<real|likely_real|ghost_job|repost|unknown>",
      "red_flags": []
    }},
    "interview_angle": {{
      "key_stories": ["<story angle 1>", "<story angle 2>"],
      "likely_questions": ["<question 1>", "<question 2>"]
    }},
    "verdict_summary": "<2-3 sentence summary of why apply or not>"
  }}
}}"""

COVER_LETTER_PROMPT = """Write 3-para cover letter. No preamble. Under 250 words.
RESUME: {resume_json}
JOB: {job_title} @ {company}
HIGHLIGHTS: {match_highlights}
- Para 1: Why {company}?
- Para 2: 2 achievements + tech.
- Para 3: Call to action.
Tone: Professional, direct."""

QUESTION_PROMPT = """Answer job question using resume.
RESUME: {resume_json}
Q: {question}
Type: {field_type}
Options: {options}
Answer ONLY the value."""


class JobMatcher:
    def __init__(self, ai_client, provider: str = "gemini"):
        self.complex_client = ai_client
        self.provider = provider
        
        # Initialize secondary 'cheap' client if available
        self.simple_client = None
        if settings.GROQ_API_KEY:
            self.simple_client = get_ai_client("groq")
        elif settings.GEMINI_API_KEY:
            self.simple_client = get_ai_client("gemini") # Uses Flash by default
            
    async def score_match(self, resume_data: dict, job: dict) -> Tuple[float, dict]:
        resume_trimmed = self._trim(resume_data, "match")
        prompt = MATCH_PROMPT.format(
            resume_json=json.dumps(resume_trimmed, indent=None),
            job_title=job.get("title", ""),
            company=job.get("company", ""),
            job_description=(job.get("description", "") or "")[:4000],
        )
        try:
            # Always use the complex client for scoring
            raw = await self._call_ai(self.complex_client, self.provider, prompt, model="gemini-1.5-pro", max_tokens=500)
            data = self._clean_json(raw)
            return float(data.get("score", 0.0)), data
        except Exception as e:
            logger.error(f"Score fail: {e}")
            return 0.0, {"score": 0.0, "explanation": str(e), "apply_recommendation": False}

    async def deep_score_match(self, resume_data: dict, job: dict) -> Tuple[float, dict]:
        """7-block structured analysis — used for HITL review queue."""
        resume_trimmed = self._trim(resume_data, "match")
        prompt = DEEP_ANALYSIS_PROMPT.format(
            resume_json=json.dumps(resume_trimmed, indent=None),
            job_title=job.get("title", ""),
            company=job.get("company", ""),
            job_description=(job.get("description", "") or "")[:4000],
        )
        try:
            raw = await self._call_ai(self.complex_client, self.provider, prompt, model="gemini-1.5-pro", max_tokens=1200)
            data = self._clean_json(raw)
            return float(data.get("score", 0.0)), data
        except Exception as e:
            logger.error(f"Deep score fail: {e}")
            return 0.0, {"score": 0.0, "apply_recommendation": False, "blocks": {}}

    async def generate_cover_letter(self, resume_data: dict, job: dict, highlights: str) -> str:
        resume_trimmed = self._trim(resume_data, "cl")
        prompt = COVER_LETTER_PROMPT.format(
            resume_json=json.dumps(resume_trimmed, indent=None),
            job_title=job.get("title", ""),
            company=job.get("company", ""),
            match_highlights=highlights[:300],
        )
        # Use simple client (Groq/Flash) for CL
        client = self.simple_client or self.complex_client
        provider = "groq" if settings.GROQ_API_KEY else self.provider
        return await self._call_ai(client, provider, prompt, model="llama-3.1-70b-versatile", max_tokens=400)

    async def answer_question(self, resume_data: dict, question: str, field_type: str = "text", options: list = None) -> str:
        prompt = QUESTION_PROMPT.format(
            resume_json=json.dumps(self._trim(resume_data, "qa"), indent=None),
            question=question, field_type=field_type,
            options=", ".join(options) if options else "free text",
        )
        client = self.simple_client or self.complex_client
        provider = "groq" if settings.GROQ_API_KEY else self.provider
        val = await self._call_ai(client, provider, prompt, model="llama-3.1-8b-instant", max_tokens=150)
        return val.strip()

    def _trim(self, data: dict, mode: str) -> dict:
        """Heuristic trimming to minimize tokens."""
        if mode == "qa":
            return {"exp_years": data.get("total_years_experience"), "skills": list(data.get("skills", {}).keys())[:15]}
        exp = data.get("experience", [])[:3]
        trimmed_exp = [{"t": e.get("title"), "c": e.get("company"), "d": (e.get("description") or "")[:200]} for e in exp]
        return {"skills": data.get("skills"), "exp": trimmed_exp}

    async def _call_ai(self, client, provider, prompt, model, max_tokens) -> str:
        if not client: return "Error: No AI client"
        
        if provider == "groq":
            # For Groq, 'model' is Llama or similar
            resp = await client.chat.completions.create(model=model, messages=[{"role":"user","content":prompt}], max_tokens=max_tokens)
            return resp.choices[0].message.content
        elif provider == "gemini":
            # If using flash for simple tasks, use 1.5-flash
            m_name = "gemini-1.5-pro" if "pro" in model else "gemini-1.5-flash"
            gem_model = client.GenerativeModel(m_name)
            resp = await gem_model.generate_content_async(prompt)
            return resp.text
        elif provider == "anthropic":
            resp = await client.messages.create(model="claude-3-5-sonnet-20241022", max_tokens=max_tokens, messages=[{"role":"user","content":prompt}])
            return resp.content[0].text
        else: # OpenAI
            resp = await client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], max_tokens=max_tokens)
            return resp.choices[0].message.content

    def _clean_json(self, raw: str) -> dict:
        raw = re.sub(r"^```(?:json)?\n?", "", raw.strip(), flags=re.I)
        raw = re.sub(r"\n?```$", "", raw, flags=re.I)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Extract first JSON object from response if AI added surrounding text
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                return json.loads(m.group())
            return {"score": 0.0, "explanation": "parse_error", "apply_recommendation": False}
