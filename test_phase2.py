# test_phase2.py
import asyncio
from tools.scraper import scrape_job_page
from parsers.job_parser import parse_job_description


async def main():
    # Use any live public job URL (e.g., from Greenhouse, Lever, or a company site)
    test_url = "https://job-boards.greenhouse.io/anthropic" 

    print(f"1. Scraping: {test_url}")
    raw_content = await scrape_job_page(test_url)
    print(f"Scraped {len(raw_content)} characters of clean text.\n")

    print("2. Parsing into structured Pydantic schema...")
    job = await parse_job_description(raw_content)

    print("\n--- Extracted Job Details ---")
    print(f"Company:       {job.company_name}")
    print(f"Title:         {job.job_title}")
    print(f"Location:      {job.location} ({job.work_mode})")
    print(f"Required:      {job.required_skills}")
    print(f"Preferred:     {job.preferred_skills}")
    print(f"Summary:       {job.summary}")


if __name__ == "__main__":
    asyncio.run(main())