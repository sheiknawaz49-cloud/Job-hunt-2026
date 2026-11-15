# test_phase3.py
import asyncio
from tools.scraper import scrape_job_page
from parsers.job_parser import parse_job_description
from tools.resume_extractor import extract_resume_text
from agent.outreach_graph import build_outreach_graph


async def main():
    # 1. Target Job & Recruiter Settings
    # Tip: Use an active, specific role page (not an overview page)
    job_url = "https://jobs.lever.co/postman/e6c9b456-11f2-4bc4-b892-d35dbeff2369"  # Example or any live tech role
    target_recruiter_email = "hiring-team@example.com"
    resume_file = "resume.pdf"

    print("Step 1: Extracting resume content...")
    resume_text = extract_resume_text(resume_file)
    print(f"Loaded resume ({len(resume_text)} chars).\n")

    print(f"Step 2: Scraping job posting: {job_url}")
    raw_job_text = await scrape_job_page(job_url)
    job_posting = await parse_job_description(raw_job_text)
    print(f"Target: {job_posting.job_title} at {job_posting.company_name}")
    print(f"Skills Found: {job_posting.required_skills}\n")

    print("Step 3: Executing LangGraph workflow...")
    graph = build_outreach_graph()

    initial_state = {
        "job_url": job_url,
        "target_email": target_recruiter_email,
        "resume_path": resume_file,
        "resume_text": resume_text,
        "job_posting": job_posting,
        "fit_analysis": None,
        "email_draft": None,
        "draft_id": None,
        "error": None
    }

    final_state = await graph.ainvoke(initial_state)

    print("\n--- Pipeline Results ---")
    fit = final_state["fit_analysis"]
    print(f"Match Score:     {fit.match_score}/100")
    print(f"Key Alignments:  {fit.key_alignments}")
    print(f"Skill Gaps:      {fit.skill_gaps}")
    print(f"Pitch Angle:     {fit.pitch_angle}\n")

    draft = final_state["email_draft"]
    print(f"Subject:         {draft.subject}")
    print(f"Gmail Draft ID:  {final_state['draft_id']}")
    print("\nCheck your Gmail 'Drafts' folder to see the complete email with your resume attached!")


if __name__ == "__main__":
    asyncio.run(main())