# tools/scraper.py
import re
import asyncio
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


def _scrape_sync(url: str, timeout_ms: int = 20000) -> str:
    """Synchronous scraper running in a dedicated worker thread."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            html_content = page.content()
        except Exception:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            html_content = page.content()
        finally:
            browser.close()

    soup = BeautifulSoup(html_content, "lxml")

    # Drop non-content elements
    for element in soup(["script", "style", "noscript", "svg", "nav", "footer", "iframe"]):
        element.decompose()

    # Locate main posting container
    main_container = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id=re.compile(r"job|content|posting", re.I))
        or soup.find(class_=re.compile(r"job|description|posting", re.I))
        or soup.body
    )

    raw_text = main_container.get_text(separator="\n") if main_container else soup.get_text(separator="\n")
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    return "\n".join(lines)[:12000]


async def scrape_job_page(url: str, timeout_ms: int = 20000) -> str:
    """Async entrypoint for FastAPI and LangGraph."""
    return await asyncio.to_thread(_scrape_sync, url, timeout_ms)