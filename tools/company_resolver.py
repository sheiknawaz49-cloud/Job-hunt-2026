# tools/company_resolver.py
import re
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup


def clean_company_name(raw_name: str) -> str:
    """Strips legal suffixes and trailing punctuation."""
    name = re.sub(r"(?i)\b(inc|corp|corporation|llc|ltd|limited|technologies|tech|solutions|pvt)\b", "", raw_name)
    return re.sub(r"[^\w\s]", "", name).strip()


async def resolve_company_domain(company_name: str) -> str | None:
    """Searches DuckDuckGo Lite to find the company's primary corporate domain."""
    cleaned = clean_company_name(company_name)
    query = f"{cleaned} official website"
    url = f"https://lite.duckduckgo.com/lite/?q={query}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return None

        soup = BeautifulSoup(resp.text, "lxml")
        links = soup.find_all("a", class_="result-link")

        # Exclude directories, social media, and job aggregators
        banned_domains = {
            "linkedin.com", "glassdoor.com", "indeed.com", "wikipedia.org",
            "crunchbase.com", "facebook.com", "twitter.com", "instagram.com"
        }

        for link in links:
            href = link.get("href", "")
            parsed = urlparse(href)
            netloc = parsed.netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]

            if netloc and not any(banned in netloc for banned in banned_domains):
                return netloc

    except Exception:
        pass

    # Fallback heuristic: strip whitespace and append .com
    fallback_slug = re.sub(r"\s+", "", cleaned.lower())
    return f"{fallback_slug}.com" if fallback_slug else None


async def get_candidate_recruiter_emails(company_name: str) -> dict:
    """
    Returns candidate talent acquisition emails for the company domain.
    """
    domain = await resolve_company_domain(company_name)
    if not domain:
        domain = "company.com"

    # Prioritized common HR/recruiting inboxes
    patterns = [
        f"recruiting@{domain}",
        f"careers@{domain}",
        f"talent@{domain}",
        f"jobs@{domain}",
    ]

    return {
        "domain": domain,
        "primary_email": patterns[0],
        "alternative_emails": patterns[1:]
    }