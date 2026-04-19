"""
Top-tier company detection.

Tier 1: FAANG+ and equivalent — always generate a custom LaTeX resume.
Tier 2: Strong brands — tailor if match score >= 0.80.
"""
import re

TIER1_COMPANIES = {
    # Big Tech
    "google", "alphabet", "deepmind",
    "meta", "facebook", "instagram", "whatsapp",
    "apple",
    "amazon", "aws",
    "microsoft", "azure", "github",
    "netflix",
    # AI leaders
    "openai", "anthropic", "cohere", "mistral", "inflection",
    "xai", "grok",
    # Cloud / infra
    "nvidia", "amd",
    "salesforce", "slack",
    "oracle",
    "ibm",
    # Fintech unicorns
    "stripe", "square", "block", "plaid", "robinhood", "coinbase",
    "brex", "ramp",
    # Top startups / unicorns
    "databricks", "snowflake", "palantir",
    "airbnb", "uber", "lyft", "doordash", "instacart",
    "figma", "notion", "linear", "vercel", "supabase",
    "canva",
    # India tier-1
    "flipkart", "meesho", "razorpay", "phonepe", "zepto", "blinkit",
    "swiggy", "zomato", "cred", "groww",
    "infosys", "wipro", "tcs", "hcl",
}

TIER2_COMPANIES = {
    "shopify", "atlassian", "zendesk", "hubspot", "docusign",
    "twilio", "cloudflare", "fastly", "hashicorp",
    "mongodb", "elastic", "redis",
    "gitlab", "bitbucket",
    "dropbox", "box", "zoom", "slack",
    "okta", "auth0", "datadog", "pagerduty", "splunk",
    "confluent", "dbt", "fivetran",
    "bytedance", "tiktok",
    "spotify", "soundcloud",
    "booking", "expedia", "airbnb",
    "wix", "squarespace", "webflow",
    "ola", "nykaa", "paytm", "freshworks",
}

# Minimum match score required to trigger tailoring for each tier
TIER1_MIN_SCORE = 0.70   # always tailor for FAANG-tier if relevant at all
TIER2_MIN_SCORE = 0.80   # only tailor strong matches at tier-2


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def get_company_tier(company: str) -> int:
    """
    Returns 1, 2, or 0.
    1 = Top-tier (FAANG+), always tailor.
    2 = Strong brand, tailor if match score >= TIER2_MIN_SCORE.
    0 = Regular, no tailoring.
    """
    n = _normalize(company)
    for t1 in TIER1_COMPANIES:
        if _normalize(t1) in n or n in _normalize(t1):
            return 1
    for t2 in TIER2_COMPANIES:
        if _normalize(t2) in n or n in _normalize(t2):
            return 2
    return 0


def should_tailor(company: str, match_score: float) -> bool:
    tier = get_company_tier(company)
    if tier == 1:
        return match_score >= TIER1_MIN_SCORE
    if tier == 2:
        return match_score >= TIER2_MIN_SCORE
    return False
