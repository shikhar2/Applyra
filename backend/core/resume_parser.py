"""
Resume parser: extracts text + structured data from PDF/DOCX resumes.
Uses AI to extract skills, experience, education into structured JSON.
Also provides a flat 'form_fields' dict ready for ATS form filling.
"""
import re
import json
from pathlib import Path
from typing import Optional
from loguru import logger

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


def extract_text_from_pdf(file_path: str) -> str:
    if not HAS_PDFPLUMBER:
        raise ImportError("pdfplumber not installed")
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
            text += "\n"
    return text.strip()


def extract_text_from_docx(file_path: str) -> str:
    if not HAS_DOCX:
        raise ImportError("python-docx not installed")
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs]).strip()


def extract_text(file_path: str) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    elif suffix in (".docx", ".doc"):
        return extract_text_from_docx(file_path)
    elif suffix == ".txt":
        return path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def split_full_name(full_name: str) -> tuple[str, str]:
    """Split 'John Michael Doe' → ('John', 'Doe'). Handles edge cases."""
    if not full_name:
        return "", ""
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[-1]


def build_form_fields(parsed: dict) -> dict:
    """
    Build a flat dict of every field an ATS form might ask for.
    This is what gets passed to the form-filling engine.
    """
    full_name = parsed.get("name", "")
    first_name, last_name = split_full_name(full_name)
    location = parsed.get("location", "")
    city = location.split(",")[0].strip() if "," in location else location
    state = location.split(",")[1].strip() if "," in location else ""

    # Current company = most recent experience entry
    experience = parsed.get("experience", [])
    current_company = ""
    current_title = ""
    if experience:
        most_recent = experience[0]
        current_company = most_recent.get("company", "")
        current_title = most_recent.get("title", "")

    # Education
    education = parsed.get("education", [])
    school = education[0].get("school", "") if education else ""
    degree = education[0].get("degree", "") if education else ""
    grad_year = str(education[0].get("graduation_year", "")) if education else ""

    total_exp = parsed.get("total_years_experience", 0) or 0

    return {
        # Personal
        "full_name": full_name,
        "first_name": first_name,
        "last_name": last_name,
        "email": parsed.get("email", ""),
        "phone": parsed.get("phone", ""),
        "location": location,
        "city": city,
        "state": state,
        "country": "United States",
        "zip_code": "",

        # Professional
        "current_company": current_company,
        "current_title": current_title,
        "years_of_experience": str(int(total_exp)) if total_exp else "3",
        "total_years_experience": str(int(total_exp)) if total_exp else "3",

        # Online presence
        "linkedin_url": parsed.get("linkedin", ""),
        "github_url": parsed.get("github", ""),
        "portfolio_url": parsed.get("portfolio", ""),
        "website": parsed.get("github", "") or parsed.get("portfolio", ""),

        # Education
        "school": school,
        "university": school,
        "degree": degree,
        "graduation_year": grad_year,

        # Work authorization (default answers — user should review)
        "authorized_to_work": "Yes",
        "requires_sponsorship": "No",
        "work_authorization": "Yes, I am authorized to work",
        "visa_status": "Authorized to work (no sponsorship needed)",

        # Availability
        "earliest_start": "Immediately",
        "notice_period": "2 weeks",
        "available_start_date": "2 weeks notice",

        # Salary (defaults — user should set in profile)
        "desired_salary": "Negotiable",
        "salary_expectation": "Negotiable",

        # Misc
        "how_did_you_hear": "Job Board",
        "referral": "",
        "cover_letter": "",  # filled by AI at apply time
    }


def basic_parse(text: str) -> dict:
    email_re = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    phone_re = re.compile(r"\+?[\d\s\-().]{10,20}")
    url_re = re.compile(r"https?://[^\s]+|linkedin\.com/in/[^\s]+|github\.com/[^\s]+")

    emails = email_re.findall(text)
    phones = phone_re.findall(text)
    urls = url_re.findall(text)

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    name = lines[0] if lines else ""

    linkedin_url = next((u for u in urls if "linkedin.com/in/" in u), None)
    github_url = next((u for u in urls if "github.com/" in u), None)

    tech_skills = [
        "Python", "JavaScript", "TypeScript", "React", "Node.js", "FastAPI",
        "Django", "Flask", "Java", "Go", "Rust", "C++", "C#", "SQL", "PostgreSQL",
        "MySQL", "MongoDB", "Redis", "Docker", "Kubernetes", "AWS", "GCP", "Azure",
        "Git", "CI/CD", "REST", "GraphQL", "gRPC", "Kafka", "RabbitMQ",
        "TensorFlow", "PyTorch", "LangChain", "OpenAI", "Anthropic", "LLM",
        "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
        "Tailwind", "Next.js", "Vue.js", "Angular", "Spring Boot",
        "Terraform", "Ansible", "Linux", "Bash", "Spark", "Airflow",
    ]
    found_skills = [s for s in tech_skills if s.lower() in text.lower()]

    parsed = {
        "name": name,
        "email": emails[0] if emails else None,
        "phone": phones[0] if phones else None,
        "linkedin": linkedin_url,
        "github": github_url,
        "skills": {"languages": found_skills},
        "experience": [],
        "education": [],
        "total_years_experience": 0,
        "raw_text": text,
    }
    parsed["form_fields"] = build_form_fields(parsed)
    return parsed


async def parse_resume_with_ai(text: str, ai_client, provider: str = "anthropic") -> dict:
    """Use AI to extract structured data from resume text."""
    prompt = f"""Extract structured information from this resume. Return ONLY valid JSON with this exact schema:
{{
  "name": "Full Name",
  "email": "email@example.com",
  "phone": "+1234567890",
  "location": "City, State",
  "linkedin": "https://linkedin.com/in/handle or null",
  "github": "https://github.com/handle or null",
  "portfolio": "https://portfolio.com or null",
  "summary": "professional summary",
  "total_years_experience": 5,
  "skills": {{
    "languages": ["Python", "JavaScript"],
    "frameworks": ["React", "FastAPI"],
    "databases": ["PostgreSQL", "Redis"],
    "cloud": ["AWS", "GCP"],
    "tools": ["Docker", "Git"],
    "ai_ml": ["PyTorch", "LangChain"],
    "other": []
  }},
  "experience": [
    {{
      "company": "Company Name",
      "title": "Job Title",
      "start_date": "2022-01",
      "end_date": "2024-01 or Present",
      "description": "Key achievements and responsibilities",
      "technologies": ["Python", "AWS"]
    }}
  ],
  "education": [
    {{
      "school": "University Name",
      "degree": "BS Computer Science",
      "graduation_year": 2020
    }}
  ],
  "certifications": ["AWS Certified Developer"],
  "languages_spoken": ["English"],
  "target_roles": ["Full Stack Engineer", "Backend Engineer"]
}}

Important: List experience in reverse chronological order (most recent first).
Calculate total_years_experience from the experience dates.

Resume text:
{text[:8000]}"""

    try:
        if provider == "anthropic":
            response = await ai_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2500,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text.strip()
        elif provider == "openai":
            response = await ai_client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=2500,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.choices[0].message.content.strip()
        elif provider == "gemini":
            gem_model = ai_client.GenerativeModel("gemini-2.0-flash")
            resp = await gem_model.generate_content_async(prompt)
            content = resp.text.strip()
        else:
            raise ValueError(f"Unknown provider: {provider}")

        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
        parsed = json.loads(content)
        parsed["form_fields"] = build_form_fields(parsed)
        return parsed
    except Exception as e:
        logger.warning(f"AI resume parsing failed: {e}, falling back to basic parse")
        return basic_parse(text)
