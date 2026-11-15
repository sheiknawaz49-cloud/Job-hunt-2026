# schemas/job_schema.py
from pydantic import BaseModel, Field


class JobPosting(BaseModel):
    company_name: str = Field(description="The name of the hiring company")
    job_title: str = Field(description="The title of the position")
    location: str = Field(default="Not specified", description="Office location or Remote status")
    work_mode: str = Field(
        default="Unknown",
        description="Work model: Remote, Hybrid, or On-site"
    )
    required_skills: list[str] = Field(
        default_factory=list,
        description="Explicit must-have technical skills, frameworks, or languages"
    )
    preferred_skills: list[str] = Field(
        default_factory=list,
        description="Nice-to-have or bonus qualifications"
    )
    responsibilities: list[str] = Field(
        default_factory=list,
        description="Key day-to-day duties and project scope"
    )
    hiring_contact_hint: str | None = Field(
        default=None,
        description="Any specific recruiter, engineering manager, or contact email mentioned"
    )
    summary: str = Field(
        description="A concise 2-3 sentence overview of what the role entails"
    )