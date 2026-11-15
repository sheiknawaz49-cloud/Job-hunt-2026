# main.py
import uuid
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from tools.scraper import scrape_job_page
from parsers.job_parser import parse_job_description
from tools.resume_extractor import extract_resume_text
from tools.company_resolver import get_candidate_recruiter_emails
from agent.outreach_graph import outreach_graph
from schemas.agent_state import EmailDraft

app = FastAPI(title="OutreachFlow Agent Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

latest_session = {"thread_id": None}


class AnalyzeRequest(BaseModel):
    job_url: str
    target_email: str
    resume_path: str = "resume.pdf"


class LinkedInIngestRequest(BaseModel):
    job_title: str
    company_name: str
    job_url: str
    description_text: str
    resume_path: str = "resume.pdf"


class ApproveRequest(BaseModel):
    thread_id: str
    subject: str
    body_html: str


@app.post("/api/linkedin-ingest")
async def linkedin_ingest(req: LinkedInIngestRequest):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    try:
        resume_text = extract_resume_text(req.resume_path)
    except Exception:
        # Graceful fallback if resume.pdf is not present yet
        resume_text = "Python Developer with experience in FastAPI, automation, and backend systems."

    contact_info = await get_candidate_recruiter_emails(req.company_name)
    target_email = contact_info.get("primary_email", f"recruiting@{req.company_name.lower().replace(' ', '')}.com")

    try:
        job_posting = await parse_job_description(req.description_text)
        job_posting.company_name = req.company_name or job_posting.company_name
        job_posting.job_title = req.job_title or job_posting.job_title
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job parser error: {str(e)}")

    initial_state = {
        "job_url": req.job_url,
        "target_email": target_email,
        "resume_path": req.resume_path,
        "resume_text": resume_text,
        "job_posting": job_posting,
        "fit_analysis": None,
        "email_draft": None,
        "draft_id": None,
        "error": None
    }

    await outreach_graph.ainvoke(initial_state, config=config)
    latest_session["thread_id"] = thread_id

    state_snapshot = await outreach_graph.aget_state(config)
    paused_data = state_snapshot.values or {}
    fit = paused_data.get("fit_analysis")

    def get_val(obj, key, default=0):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    return {
        "status": "success",
        "thread_id": thread_id,
        "company_name": job_posting.company_name,
        "job_title": job_posting.job_title,
        "domain": contact_info.get("domain", ""),
        "target_email": target_email,
        "match_score": get_val(fit, "match_score", 80)
    }


@app.get("/api/latest-thread")
async def get_latest_thread():
    thread_id = latest_session.get("thread_id")
    if not thread_id:
        return {"active": False}

    config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = await outreach_graph.aget_state(config)
    if not state_snapshot or not state_snapshot.values:
        return {"active": False}

    data = state_snapshot.values
    job = data.get("job_posting")
    fit = data.get("fit_analysis")
    draft = data.get("email_draft")

    def get_val(obj, key, default=""):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    return {
        "active": True,
        "thread_id": thread_id,
        "job_title": get_val(job, "job_title", "Software Engineer"),
        "company_name": get_val(job, "company_name", "Company"),
        "fit_analysis": {
            "match_score": get_val(fit, "match_score", 80),
            "pitch_angle": get_val(fit, "pitch_angle", "Technical Alignment")
        },
        "email_draft": {
            "subject": get_val(draft, "subject", "Application"),
            "body_html": get_val(draft, "body_html", "")
        }
    }


@app.post("/api/approve")
async def approve_outreach(req: ApproveRequest):
    try:
        config = {"configurable": {"thread_id": req.thread_id}}
        state_snapshot = await outreach_graph.aget_state(config)

        if not state_snapshot or not state_snapshot.values:
            raise HTTPException(status_code=404, detail="Session expired or thread not found. Please re-ingest the job.")

        target_email = state_snapshot.values.get("target_email", "recruiting@company.com")
        updated_draft = EmailDraft(
            subject=req.subject,
            recipient_email=target_email,
            body_html=req.body_html
        )

        # Update state directly (omitting as_node prevents LangGraph task-scheduling conflicts)
        await outreach_graph.aupdate_state(
            config,
            {"email_draft": updated_draft}
        )

        # Resume execution to run stage_gmail_draft
        resumed_state = await outreach_graph.ainvoke(None, config=config)

        draft_id = resumed_state.get("draft_id", "STAGED_SUCCESS")
        return {
            "status": "success",
            "draft_id": draft_id,
            "message": "Draft created in your Gmail account."
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history():
    from db.database import get_all_outreach_history
    return get_all_outreach_history(limit=25)


@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>OutreachFlow Dashboard</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-950 text-slate-100 min-h-screen p-6 font-sans">
      <div class="max-w-4xl mx-auto space-y-6">
        <header class="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h1 class="text-2xl font-bold text-white tracking-tight">OutreachFlow</h1>
            <p class="text-sm text-slate-400">Agentic Cold Outreach &bull; Ingestion + Gmail API</p>
          </div>
          <button onclick="ingestFromClipboard()" class="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition shadow-md">
            <span>📋</span> Paste &amp; Ingest from Clipboard
          </button>
        </header>

        <!-- Status Spinner -->
        <div id="loader" class="hidden text-center py-8">
          <div class="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent"></div>
          <p id="loaderText" class="text-sm text-slate-400 mt-2">Processing...</p>
        </div>

        <!-- Review / HITL Approval Section -->
        <div id="reviewCard" class="hidden bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-5">
          <div class="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h2 id="jobHeader" class="text-lg font-semibold text-white"></h2>
              <p id="pitchAngle" class="text-xs text-blue-400 mt-0.5"></p>
            </div>
            <div id="scoreBadge" class="px-3 py-1 bg-blue-950 text-blue-300 border border-blue-800 rounded-full text-xs font-bold"></div>
          </div>

          <div class="space-y-3">
            <div>
              <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Subject Line</label>
              <input id="emailSubject" type="text" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Email Body (HTML/Text)</label>
              <textarea id="emailBody" rows="7" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-sm font-mono text-slate-200 focus:outline-none focus:border-blue-500"></textarea>
            </div>
          </div>

          <div class="flex items-center justify-between pt-2">
            <span class="text-xs text-slate-500">Resume (<code class="text-slate-400">resume.pdf</code>) attached automatically if present.</span>
            <button onclick="approveDraft()" class="bg-emerald-600 hover:bg-emerald-500 text-white font-medium px-5 py-2 rounded-lg text-sm transition">Approve &amp; Create Gmail Draft</button>
          </div>
        </div>

        <!-- Success Toast -->
        <div id="successBanner" class="hidden bg-emerald-950 border border-emerald-800 text-emerald-200 p-4 rounded-xl text-sm flex items-center justify-between">
          <span id="successMsg"></span>
          <a href="https://mail.google.com" target="_blank" class="underline text-white font-semibold ml-4">Open Gmail &rarr;</a>
        </div>
      </div>

      <script>
        let currentThreadId = null;

        window.onload = () => {
          syncLatestThread();
        };

        async function syncLatestThread() {
          try {
            const res = await fetch('/api/latest-thread');
            if (!res.ok) return;
            const data = await res.json();
            if (data.active) {
              currentThreadId = data.thread_id;
              document.getElementById('jobHeader').innerText = `${data.job_title} at ${data.company_name}`;
              document.getElementById('pitchAngle').innerText = `Angle: ${data.fit_analysis.pitch_angle}`;
              document.getElementById('scoreBadge').innerText = `${data.fit_analysis.match_score}/100 Match`;
              document.getElementById('emailSubject').value = data.email_draft.subject;
              document.getElementById('emailBody').value = data.email_draft.body_html;
              document.getElementById('reviewCard').classList.remove('hidden');
            }
          } catch (e) {
            console.error('Sync error', e);
          }
        }

        async function ingestFromClipboard() {
          try {
            const clipText = await navigator.clipboard.readText();
            let payload;
            try {
              payload = JSON.parse(clipText);
            } catch (e) {
              return alert('Clipboard does not contain valid OutreachFlow JSON. Click the bookmark on LinkedIn first!');
            }

            document.getElementById('loader').classList.remove('hidden');
            document.getElementById('loaderText').innerText = `Evaluating alignment for ${payload.company_name}...`;
            document.getElementById('reviewCard').classList.add('hidden');
            document.getElementById('successBanner').classList.add('hidden');

            const res = await fetch('/api/linkedin-ingest', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify(payload)
            });

            if (!res.ok) {
              const err = await res.json();
              throw new Error(err.detail || 'Ingest failed');
            }

            await syncLatestThread();
          } catch (err) {
            alert('Ingest Error: ' + err.message);
          } finally {
            document.getElementById('loader').classList.add('hidden');
          }
        }

        async function approveDraft() {
          if (!currentThreadId) return;
          const subject = document.getElementById('emailSubject').value;
          const body_html = document.getElementById('emailBody').value;

          try {
            const res = await fetch('/api/approve', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({ thread_id: currentThreadId, subject, body_html })
            });

            if (!res.ok) {
              let errMsg = 'Server error (' + res.status + ')';
              try {
                const errJson = await res.json();
                errMsg = errJson.detail || errMsg;
              } catch (_) {
                errMsg = await res.text();
              }
              throw new Error(errMsg);
            }

            const data = await res.json();
            document.getElementById('reviewCard').classList.add('hidden');
            document.getElementById('successBanner').classList.remove('hidden');
            document.getElementById('successMsg').innerText = `Success! Draft created: ${data.draft_id}`;
          } catch (err) {
            alert('Approval Error: ' + err.message);
          }
        }
      </script>
    </body>
    </html>
    """