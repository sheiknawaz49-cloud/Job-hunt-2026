import os
import base64
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# gmail.compose allows creating drafts and sending emails without full inbox deletion risk
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
CREDENTIALS_DIR = Path(__file__).resolve().parent.parent / "credentials"
CLIENT_SECRET_FILE = CREDENTIALS_DIR / "client_secret.json"
TOKEN_FILE = CREDENTIALS_DIR / "token.json"


def get_gmail_service():
    """Handles OAuth 2.0 flow and returns an authenticated Gmail API service."""
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # Refresh expired token or trigger browser login on first run
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def create_outreach_draft(
    recipient_email: str,
    subject: str,
    body_html: str,
    attachment_path: str | None = None,
) -> dict:
    """Builds a MIME email with an optional PDF attachment and saves it to Gmail Drafts."""
    service = get_gmail_service()

    # 1. Construct the RFC 2822 Multipart Container
    mime_message = MIMEMultipart()
    mime_message["To"] = recipient_email
    mime_message["Subject"] = subject

    # 2. Attach the HTML email body
    mime_message.attach(MIMEText(body_html, "html"))

    # 3. Attach the PDF Resume if provided
    if attachment_path and os.path.exists(attachment_path):
        filename = os.path.basename(attachment_path)
        with open(attachment_path, "rb") as f:
            pdf_part = MIMEApplication(f.read(), _subtype="pdf")
            pdf_part.add_header(
                "Content-Disposition", "attachment", filename=filename
            )
            mime_message.attach(pdf_part)

    # 4. Encode the entire MIME tree into URL-safe Base64
    encoded_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")
    create_draft_request = {"message": {"raw": encoded_message}}

    # 5. Execute the Gmail API call
    draft = (
        service.users()
        .drafts()
        .create(userId="me", body=create_draft_request)
        .execute()
    )
    return {"draft_id": draft["id"], "message_id": draft["message"]["id"]}

def search_emails(query: str = "is:unread", max_results: int = 5) -> list[dict]:
    """
    Search messages matching a standard Gmail search query 
    (e.g., 'from:recruiter@company.com', 'subject:Interview', 'label:INBOX').
    """
    service = get_gmail_service()
    response = service.users().messages().list(
        userId="me", 
        q=query, 
        maxResults=max_results
    ).execute()

    return response.get("messages", [])


def read_email(message_id: str) -> dict:
    """Fetches and parses subject, sender, date, snippet, and plain text body."""
    service = get_gmail_service()
    message = service.users().messages().get(
        userId="me", 
        id=message_id, 
        format="full"
    ).execute()

    payload = message.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}

    # Extract body content
    body = ""
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                break
    elif "data" in payload.get("body", {}):
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    return {
        "id": message_id,
        "thread_id": message.get("threadId"),
        "from": headers.get("from", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "snippet": message.get("snippet", ""),
        "body": body
    }


def trash_email(message_id: str) -> dict:
    """Moves an email to the Trash folder (recoverable for 30 days)."""
    service = get_gmail_service()
    return service.users().messages().trash(userId="me", id=message_id).execute()


def untrash_email(message_id: str) -> dict:
    """Restores an email from the Trash back to the Inbox."""
    service = get_gmail_service()
    return service.users().messages().untrash(userId="me", id=message_id).execute()


def permanently_delete_email(message_id: str) -> None:
    """
    Permanently deletes an email bypassing the Trash.
    Requires the 'https://mail.google.com/' scope.
    """
    service = get_gmail_service()
    service.users().messages().delete(userId="me", id=message_id).execute()