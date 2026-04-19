"""
LaTeX Resume Generator.

Flow:
  1. AI generates a complete, job-tailored LaTeX document from resume JSON + job description.
  2. pdflatex compiles it to PDF  (if available on the system).
  3. If pdflatex is missing, falls back to a reportlab-rendered PDF with the same content.

The output PDF is saved to data/tailored_resumes/<app_id>_<company_slug>.pdf
"""
import asyncio
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from loguru import logger


# ── Prompt ────────────────────────────────────────────────────────────────────

LATEX_RESUME_PROMPT = """You are an expert LaTeX resume writer. Create a complete, compilable LaTeX resume
tailored to the specific job below.

CANDIDATE RESUME DATA (JSON):
{resume_json}

TARGET JOB:
Title: {job_title}
Company: {company}
Job Description:
{job_description}

INSTRUCTIONS:
1. Use the Jake's Resume template style (clean, ATS-friendly, single-column or two-column).
2. Rewrite EVERY experience bullet point to mirror keywords from this specific job description.
3. Reorder skills to put the most relevant ones first.
4. Add a 2-line "Summary" / "Objective" section at the top, specifically written for {company}.
5. Keep all facts TRUE — rephrase and reorder, do NOT fabricate experience or skills.
6. Use \\textbf{{}} for important keywords so they stand out to human reviewers.
7. Make sure the LaTeX is 100% compilable — no undefined commands or missing packages.
8. Use only standard packages: geometry, hyperref, enumitem, fontenc, inputenc, titlesec, xcolor, multicol.

OUTPUT: Return ONLY the complete LaTeX source code, starting with \\documentclass and ending with \\end{{document}}.
Do NOT wrap in markdown code fences. Do NOT include any explanation — only LaTeX."""


# ── Main class ────────────────────────────────────────────────────────────────

class LatexResumeGenerator:
    def __init__(self, ai_client, provider: str = "anthropic"):
        self.client = ai_client
        self.provider = provider
        self._output_dir = Path("data/tailored_resumes")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_tailored_pdf(
        self,
        resume_data: dict,
        job: dict,
        app_id: int,
    ) -> Optional[str]:
        """
        Generate a job-tailored PDF resume.
        Returns the output PDF path, or None on failure.
        """
        company_slug = re.sub(r"[^a-z0-9]", "_", job.get("company", "company").lower())[:30]
        out_path = str(self._output_dir / f"app_{app_id}_{company_slug}.pdf")

        # Already generated for this application
        if os.path.exists(out_path):
            return out_path

        logger.info(f"Generating tailored LaTeX resume for {job.get('company')} → app #{app_id}")

        latex_src = await self._generate_latex(resume_data, job)
        if not latex_src:
            return None

        pdf_path = await self._compile_to_pdf(latex_src, out_path)
        if pdf_path:
            logger.info(f"Tailored PDF saved: {pdf_path}")
        return pdf_path

    # ── AI generation ─────────────────────────────────────────────────────────

    async def _generate_latex(self, resume_data: dict, job: dict) -> Optional[str]:
        # Trim resume to keep within context limits
        trimmed = {
            "name": resume_data.get("name", ""),
            "email": resume_data.get("email", ""),
            "phone": resume_data.get("phone", ""),
            "linkedin": resume_data.get("linkedin", ""),
            "github": resume_data.get("github", ""),
            "location": resume_data.get("location", ""),
            "summary": resume_data.get("summary", ""),
            "skills": resume_data.get("skills", [])[:40],
            "experience": (resume_data.get("experience") or [])[:5],
            "education": resume_data.get("education", []),
            "certifications": resume_data.get("certifications", []),
        }

        prompt = LATEX_RESUME_PROMPT.format(
            resume_json=json.dumps(trimmed, indent=2)[:4000],
            job_title=job.get("title", ""),
            company=job.get("company", ""),
            job_description=(job.get("description") or "")[:3000],
        )

        try:
            raw = await self._call_ai(prompt, max_tokens=4000)
            # Strip any accidental markdown fences
            raw = re.sub(r"^```(?:latex|tex)?\n?", "", raw.strip())
            raw = re.sub(r"\n?```$", "", raw)
            if "\\documentclass" not in raw:
                logger.warning("AI did not return valid LaTeX — no \\documentclass found")
                return None
            return raw
        except Exception as e:
            logger.error(f"LaTeX generation failed: {e}")
            return None

    # ── PDF compilation ────────────────────────────────────────────────────────

    async def _compile_to_pdf(self, latex_src: str, out_path: str) -> Optional[str]:
        # Try pdflatex first (highest quality)
        if shutil.which("pdflatex") or shutil.which("xelatex"):
            return await self._compile_pdflatex(latex_src, out_path)
        # Fall back to reportlab renderer
        return await asyncio.get_event_loop().run_in_executor(
            None, self._render_reportlab, latex_src, out_path
        )

    async def _compile_pdflatex(self, latex_src: str, out_path: str) -> Optional[str]:
        compiler = shutil.which("xelatex") or shutil.which("pdflatex")
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_file = os.path.join(tmpdir, "resume.tex")
            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(latex_src)
            try:
                proc = await asyncio.create_subprocess_exec(
                    compiler, "-interaction=nonstopmode", "-output-directory", tmpdir, tex_file,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
                pdf_tmp = os.path.join(tmpdir, "resume.pdf")
                if os.path.exists(pdf_tmp):
                    shutil.move(pdf_tmp, out_path)
                    return out_path
                logger.warning(f"pdflatex produced no PDF: {stderr.decode()[:300]}")
            except asyncio.TimeoutError:
                logger.error("pdflatex timed out after 60s")
            except Exception as e:
                logger.error(f"pdflatex error: {e}")
        return None

    def _render_reportlab(self, latex_src: str, out_path: str) -> Optional[str]:
        """
        Fallback renderer: parse key sections from LaTeX source and build
        a clean PDF with reportlab. Not pixel-perfect but produces a
        readable, correctly-structured resume.
        """
        try:
            from reportlab.lib.pagesizes import LETTER
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem
            )
            from reportlab.lib.enums import TA_LEFT, TA_CENTER

            doc = SimpleDocTemplate(
                out_path,
                pagesize=LETTER,
                leftMargin=0.6 * inch, rightMargin=0.6 * inch,
                topMargin=0.5 * inch, bottomMargin=0.5 * inch,
            )

            styles = getSampleStyleSheet()
            name_style   = ParagraphStyle("Name",   fontSize=20, leading=24, alignment=TA_CENTER, textColor=colors.HexColor("#1a1a2e"), fontName="Helvetica-Bold")
            contact_style= ParagraphStyle("Contact",fontSize=9,  leading=12, alignment=TA_CENTER, textColor=colors.HexColor("#555555"))
            heading_style= ParagraphStyle("Heading",fontSize=11, leading=14, textColor=colors.HexColor("#1a1a2e"), fontName="Helvetica-Bold", spaceAfter=2)
            body_style   = ParagraphStyle("Body",   fontSize=9,  leading=13, textColor=colors.HexColor("#333333"))
            bullet_style = ParagraphStyle("Bullet", fontSize=9,  leading=13, textColor=colors.HexColor("#333333"), leftIndent=12, bulletIndent=0)
            job_style    = ParagraphStyle("Job",    fontSize=10, leading=13, fontName="Helvetica-Bold", textColor=colors.HexColor("#1a1a2e"))
            date_style   = ParagraphStyle("Date",   fontSize=9,  leading=12, textColor=colors.HexColor("#666666"))

            story = []

            # ── Extract name ─────────────────────────────────────────────────
            name = _tex_extract(latex_src, r"\\name\{([^}]+)\}") or \
                   _tex_extract(latex_src, r"\\textbf\{([^}]{3,40})\}") or "Candidate"
            story.append(Paragraph(_tex_clean(name), name_style))

            # ── Contact line ─────────────────────────────────────────────────
            contacts = []
            for pat in [r"\\email\{([^}]+)\}", r"\\href\{mailto:([^}]+)\}", r"\\phone\{([^}]+)\}"]:
                val = _tex_extract(latex_src, pat)
                if val:
                    contacts.append(_tex_clean(val))
            email_inline = re.search(r"[\w.+-]+@[\w.-]+\.\w+", latex_src)
            if email_inline and email_inline.group() not in " ".join(contacts):
                contacts.append(email_inline.group())
            if contacts:
                story.append(Paragraph("  |  ".join(contacts), contact_style))

            story.append(Spacer(1, 0.12 * inch))

            # ── Sections ─────────────────────────────────────────────────────
            sections = _tex_extract_sections(latex_src)
            for sec_title, sec_body in sections:
                story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#1a1a2e"), spaceAfter=3))
                story.append(Paragraph(sec_title.upper(), heading_style))

                lines = [l.strip() for l in sec_body.split("\n") if l.strip()]
                for line in lines:
                    clean = _tex_clean(line)
                    if not clean or len(clean) < 2:
                        continue
                    if line.startswith(("\\item", "-", "•", "*")):
                        story.append(Paragraph(f"• {clean.lstrip('•-* ')}", bullet_style))
                    else:
                        story.append(Paragraph(clean, body_style))
                story.append(Spacer(1, 0.08 * inch))

            doc.build(story)
            return out_path
        except Exception as e:
            logger.error(f"reportlab render failed: {e}")
            return None

    # ── AI helper ─────────────────────────────────────────────────────────────

    async def _call_ai(self, prompt: str, max_tokens: int = 4000) -> str:
        if self.provider == "anthropic":
            resp = await self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text
        elif self.provider == "openai":
            resp = await self.client.chat.completions.create(
                model="gpt-4o",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content
        elif self.provider == "gemini":
            gem_model = self.client.GenerativeModel("gemini-2.0-flash")
            resp = await gem_model.generate_content_async(prompt)
            return resp.text
        raise ValueError(f"Unknown provider: {self.provider}")


# ── LaTeX parsing helpers ─────────────────────────────────────────────────────

def _tex_extract(src: str, pattern: str) -> Optional[str]:
    m = re.search(pattern, src)
    return m.group(1) if m else None


def _tex_clean(text: str) -> str:
    """Strip common LaTeX commands to get plain text."""
    text = re.sub(r"\\textbf\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\textit\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\emph\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\url\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\*?\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", text)
    text = re.sub(r"[{}]", "", text)
    text = re.sub(r"\\\\", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _tex_extract_sections(src: str) -> list[tuple[str, str]]:
    """Extract (section_title, body_text) pairs from LaTeX source."""
    # Match \section{...} or \resumeSection{...} etc.
    pat = re.compile(
        r"\\(?:section|resumesection|cvsection)\*?\{([^}]+)\}(.*?)(?=\\(?:section|resumesection|cvsection)\*?\{|\\end\{document\})",
        re.IGNORECASE | re.DOTALL,
    )
    results = []
    for m in pat.finditer(src):
        title = _tex_clean(m.group(1))
        body = m.group(2)
        # Skip preamble/empty sections
        if len(body.strip()) > 5:
            results.append((title, body))
    return results
