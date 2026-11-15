# schemas/agent_state.py
from typing import TypedDict
from pydantic import BaseModel, Field
from schemas.job_schema import JobPosting


class FitAnalysis(BaseModel):
    match_score: int = Field(description="Compatibility score from 0 to 100")
    key_alignments: list[str] = Field(
        description="2-3 specific matches between candidate experience and role needs"
    )
    skill_gaps: list[str] = Field(
        description="Noticeable skills required by the role not prominent on resume"
    )
    pitch_angle: str = Field(
        description="The strategic technical angle to emphasize in the email"
    )


class EmailDraft(BaseModel):
    subject: str = Field(description="Concise, high-open-rate subject line")
    recipient_email: str = Field(description="Target contact email")
    body_html: str = Field(description="Clean, well-spaced HTML body of the email")


class OutreachState(TypedDict):
    job_url: str
    target_email: str
    resume_path: str
    resume_text: str
    job_posting: JobPosting | None
    fit_analysis: FitAnalysis | None
    email_draft: EmailDraft | None
    draft_id: str | None
    error: str | None