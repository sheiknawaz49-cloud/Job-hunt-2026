from tools.gmail_tool import create_outreach_draft

if __name__ == "__main__":
    sample_html = """
    <p>Hi Engineering Team,</p>
    <p>I saw your opening for the Senior Python & AI Developer role. Having built scalable FastAPI backends and agentic workflows with LangGraph, I'd love to connect.</p>
    <p>I've attached my resume for your review.</p>
    <p>Best regards,<br>Nawaz</p>
    """

    result = create_outreach_draft(
        recipient_email="hiring-manager@example.com",
        subject="Application: Senior Python & AI Developer",
        body_html=sample_html,
        attachment_path="resume.pdf"
    )
    print(f"Success! Created Gmail Draft ID: {result['draft_id']}")