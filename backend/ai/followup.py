"""
Auto follow-up email generator + scheduler.

Generates personalized follow-up emails at key intervals:
  - Day 3:  "Thank you" / checking in
  - Day 7:  Gentle follow-up
  - Day 14: Final follow-up with value-add

No competitor does this automatically tied to application status.
"""
import json
import re
from datetime import datetime, timedelta
from loguru import logger


FOLLOWUP_PROMPT = """Write a professional follow-up email for a job application.

CONTEXT:
Candidate: {candidate_name}
Job Title: {job_title}
Company: {company}
Applied on: {applied_date}
Days since applied: {days_since}
Follow-up type: {followup_type}

Cover letter excerpt (what was originally sent):
{cover_letter_excerpt}

Rules for {followup_type} follow-up:
{rules}

Return ONLY the email body (no subject line, no sign-off name). Keep it under 100 words.
Be warm, professional, and specific to this role. Never sound desperate."""


FOLLOWUP_RULES = {
    "thank_you": (
        "- Express genuine enthusiasm for the role\n"
        "- Mention ONE specific thing from the job description that excites you\n"
        "- Briefly reinforce your strongest qualification\n"
        "- Keep it very short (3-4 sentences)"
    ),
    "gentle_check": (
        "- Open by referencing the application date\n"
        "- Add a new piece of value (e.g., 'Since applying, I also published X')\n"
        "- Express continued interest\n"
        "- Ask if there's any additional info you can provide\n"
        "- 4-5 sentences"
    ),
    "final_followup": (
        "- Acknowledge they're busy\n"
        "- Briefly restate your strongest fit for the role\n"
        "- Offer flexibility (happy to chat at their convenience)\n"
        "- Professional sign-off without pressure\n"
        "- 3-4 sentences"
    ),
}

SUBJECT_TEMPLATES = {
    "thank_you": "Following up on {job_title} application",
    "gentle_check": "Re: {job_title} application — quick check-in",
    "final_followup": "Re: {job_title} at {company} — still interested",
}


class FollowUpGenerator:
    def __init__(self, ai_client, provider: str = "anthropic"):
        self.client = ai_client
        self.provider = provider

    async def generate_followup(
        self, candidate_name: str, job_title: str, company: str,
        applied_date: str, cover_letter: str = "", followup_type: str = "gentle_check"
    ) -> dict:
        """
        Generate a follow-up email for a specific application.
        followup_type: 'thank_you' | 'gentle_check' | 'final_followup'
        Returns {subject, body}.
        """
        try:
            applied_dt = datetime.fromisoformat(applied_date) if applied_date else datetime.utcnow()
        except ValueError:
            applied_dt = datetime.utcnow()

        days_since = (datetime.utcnow() - applied_dt).days

        prompt = FOLLOWUP_PROMPT.format(
            candidate_name=candidate_name,
            job_title=job_title,
            company=company,
            applied_date=applied_dt.strftime("%B %d, %Y"),
            days_since=days_since,
            followup_type=followup_type,
            cover_letter_excerpt=(cover_letter or "")[:500],
            rules=FOLLOWUP_RULES.get(followup_type, FOLLOWUP_RULES["gentle_check"]),
        )
        try:
            body = await self._call_ai(prompt, max_tokens=250)
            subject = SUBJECT_TEMPLATES.get(followup_type, "Follow-up: {job_title}").format(
                job_title=job_title, company=company
            )
            return {"subject": subject, "body": body.strip(), "type": followup_type}
        except Exception as e:
            logger.error(f"Follow-up generation failed: {e}")
            return {"subject": "", "body": "", "type": followup_type}

    def get_followup_schedule(self, applied_date: str) -> list[dict]:
        """
        Return scheduled follow-up dates for an application.
        """
        try:
            base = datetime.fromisoformat(applied_date)
        except (ValueError, TypeError):
            base = datetime.utcnow()

        return [
            {"type": "thank_you",      "date": (base + timedelta(days=3)).isoformat(),  "label": "Thank you (Day 3)"},
            {"type": "gentle_check",   "date": (base + timedelta(days=7)).isoformat(),  "label": "Check in (Day 7)"},
            {"type": "final_followup", "date": (base + timedelta(days=14)).isoformat(), "label": "Final follow-up (Day 14)"},
        ]

    async def _call_ai(self, prompt: str, max_tokens: int = 300) -> str:
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
