# agent/outreach_graph.py
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from schemas.agent_state import OutreachState, FitAnalysis, EmailDraft
from parsers.job_parser import get_llm
from tools.gmail_tool import create_outreach_draft
from db.template_matcher import find_best_pitch_bm25
from db.sqlite_db import log_outreach_attempt


class SinglePassOutreach(BaseModel):
    match_score: int = Field(description="Score between 0 and 100")
    key_alignments: list[str] = Field(description="2-3 specific technical matches")
    skill_gaps: list[str] = Field(description="Missing skills or gaps")
    pitch_angle: str = Field(description="Strategic technical angle emphasized")
    subject: str = Field(description="High-converting email subject line")
    body_html: str = Field(description="Full personalized email body in clean HTML format")


COMBINED_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an expert technical talent strategist. Perform TWO tasks in a single pass:\n"
        "1. Assess technical alignment between the candidate's resume and the job posting.\n"
        "2. Draft a concise cold email (under 130 words) from the candidate to the hiring team.\n"
        "Lead with technical impact. Explicitly mention the resume is attached."
    ),
    (
        "human",
        "Company: {company}\n"
        "Role: {title}\n"
        "Candidate Resume Details:\n{resume_text}\n\n"
        "Job Description:\n{job_data}"
    )
])


async def generate_outreach_node(state: OutreachState) -> dict:
    job = state.get("job_posting")
    company_name = job.company_name if job else "Engineering Team"
    job_title = job.job_title if job else "Software Engineer"
    target_email = state.get("target_email", "recruiting@company.com")

    try:
        # 1. Primary: Single-Pass Gemini LLM Generation
        llm = get_llm()
        structured_llm = llm.with_structured_output(SinglePassOutreach)
        chain = COMBINED_PROMPT | structured_llm

        job_data_str = job.model_dump_json(indent=2) if job else "Not available"
        result: SinglePassOutreach = await chain.ainvoke({
            "company": company_name,
            "title": job_title,
            "resume_text": state["resume_text"][:3500],
            "job_data": job_data_str
        })

        fit = FitAnalysis(
            match_score=result.match_score,
            key_alignments=result.key_alignments,
            skill_gaps=result.skill_gaps,
            pitch_angle=result.pitch_angle
        )
        draft = EmailDraft(
            subject=result.subject,
            recipient_email=target_email,
            body_html=result.body_html
        )
        pitch_source = "Gemini LLM"

    except Exception as e:
        # 2. Resilient Offline Fallback: SQLite FTS5 (BM25 Semantic Ranking)
        print(f"[OutreachFlow Warning] LLM call failed ({str(e)}). Using offline SQLite BM25...")

        search_corpus = f"{job_title} {company_name} " + (job.summary if job else "")
        best_pitch = find_best_pitch_bm25(search_corpus)

        formatted_subject = best_pitch["subject"].format(company_name=company_name, job_title=job_title)
        formatted_body = (
            f"<p>Hi {company_name} Hiring Team,</p>"
            f"<p>I saw the opening for <strong>{job_title}</strong>. {best_pitch['pitch']}</p>"
            f"<p>Given your focus, my hands-on background aligns directly with what you are scaling. "
            f"I have attached my resume for your review.</p>"
            f"<p>Best regards,<br>Nawaz</p>"
        )

        fit = FitAnalysis(
            match_score=80,
            key_alignments=["Offline Relevance Match", best_pitch["category"]],
            skill_gaps=["N/A (Generated via offline fallback)"],
            pitch_angle=f"Offline Archetype: {best_pitch['category']}"
        )
        draft = EmailDraft(
            subject=formatted_subject,
            recipient_email=target_email,
            body_html=formatted_body
        )
        pitch_source = f"Offline BM25 ({best_pitch['category']})"

    return {
        "fit_analysis": fit,
        "email_draft": draft,
        "error": pitch_source
    }


def stage_gmail_draft_node(state: OutreachState) -> dict:
    draft = state["email_draft"]
    fit = state.get("fit_analysis")
    job = state.get("job_posting")
    pitch_source = state.get("error", "Unknown")

    company_name = job.company_name if job else "Unknown Company"
    job_title = job.job_title if job else "Unknown Role"

    # 1. Stage Draft in Gmail
    result = create_outreach_draft(
        recipient_email=draft.recipient_email,
        subject=draft.subject,
        body_html=draft.body_html,
        attachment_path=state.get("resume_path", "resume.pdf")
    )
    draft_id = result["draft_id"]

    # 2. Persist to SQLite History Table
    log_outreach_attempt(
        company_name=company_name,
        job_title=job_title,
        target_email=draft.recipient_email,
        subject=draft.subject,
        body_html=draft.body_html,
        match_score=fit.match_score if fit else 0,
        pitch_source=pitch_source,
        gmail_draft_id=draft_id,
        status="DRAFT_STAGED"
    )

    return {"draft_id": draft_id}


# Compile LangGraph with human approval checkpoint
checkpointer = MemorySaver()
builder = StateGraph(OutreachState)

builder.add_node("generate_outreach", generate_outreach_node)
builder.add_node("stage_gmail_draft", stage_gmail_draft_node)

builder.add_edge(START, "generate_outreach")
builder.add_edge("generate_outreach", "stage_gmail_draft")
builder.add_edge("stage_gmail_draft", END)

outreach_graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["stage_gmail_draft"]
)

# In agent/outreach_graph.py

import os

def stage_gmail_draft_node(state: OutreachState) -> dict:
    draft = state["email_draft"]
    fit = state.get("fit_analysis")
    job = state.get("job_posting")
    pitch_source = state.get("error", "LLM Generation")

    def get_val(obj, key, default=""):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    recipient = get_val(draft, "recipient_email", state.get("target_email", "recruiting@company.com"))
    subject = get_val(draft, "subject", "Job Application")
    body_html = get_val(draft, "body_html", "")

    company_name = get_val(job, "company_name", "Unknown Company")
    job_title = get_val(job, "job_title", "Unknown Role")
    match_score = get_val(fit, "match_score", 80)

    # Attach resume.pdf only if the file exists on disk
    resume_file = state.get("resume_path", "resume.pdf")
    attachment = resume_file if os.path.exists(resume_file) else None

    # 1. Create Draft via Gmail Tool
    result = create_outreach_draft(
        recipient_email=recipient,
        subject=subject,
        body_html=body_html,
        attachment_path=attachment
    )
    draft_id = result.get("draft_id", "DRAFT_STAGED")

    # 2. Persist record to SQLite
    try:
        log_outreach_attempt(
            company_name=company_name,
            job_title=job_title,
            target_email=recipient,
            subject=subject,
            body_html=body_html,
            match_score=match_score,
            pitch_source=pitch_source,
            gmail_draft_id=draft_id,
            status="DRAFT_STAGED"
        )
    except Exception as db_err:
        print(f"[Warning] SQLite logging error: {db_err}")

    return {"draft_id": draft_id}