import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

# Load .env from project root automatically
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from jira.jira_reader import get_user_story
from jira.jira_client import search_tickets
from agents.builder_agent import build_code
from agents.test_runner import run_tests
from agents.devops_agent import commit_code, push_code
from orchestrator.pace_orchestrator import run_pace, stream_pace
import jira_poller

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    jira_poller.start_poller()
    jira_poller.start_worker()
    yield
    jira_poller.stop_poller()


app = FastAPI(title="Agentic Dev System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/")
def home():
    return {"message": "Agentic Dev System is running"}


# ── Jira ──────────────────────────────────────────────────────────────────────

@app.get("/jira/tickets")
def jira_tickets():
    """Return all To Do tickets in the project for the UI ticket picker."""
    try:
        tickets = search_tickets('project=AA ORDER BY created DESC', max_results=50)
        return {"tickets": tickets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jira-story")
def jira_story(ticket_id: str = "JIRA-101"):
    try:
        return {"story": get_user_story(ticket_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── New PACE pipeline  (PRIME → FORGE → GATE|SENTINEL|CONDUIT → SCRIBE) ───────

@app.post("/pace/run")
def pace_run(ticket_id: str):
    """Run the full new pipeline for a specific Jira ticket (blocking)."""
    try:
        return run_pace(ticket_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pace/stream")
def pace_stream(ticket_id: str):
    """SSE stream of pipeline events for a specific Jira ticket."""
    def gen():
        try:
            for event in stream_pace(ticket_id):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'stage':'error','status':'error','output':str(e)})}\n\n"
        finally:
            yield f"data: {json.dumps({'done': True})}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/pace/status")
def pace_status():
    """Poller queue depth and number of tickets seen this session."""
    return {"queue_depth": jira_poller.queue_depth(), "seen_count": jira_poller.seen_count()}


# ── Legacy endpoints (kept so the old UI still works) ─────────────────────────

@app.post("/build")
def build():
    try:
        story = get_user_story()
        code = build_code(story)
        return {"status": "code generated", "code": code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test")
def test():
    try:
        return run_tests()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/commit")
def commit():
    try:
        return commit_code()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/push")
def push():
    try:
        return push_code()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/run")
def run_legacy():
    try:
        return run_pace()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stream")
def stream_legacy():
    def gen():
        try:
            for event in stream_pace():
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'stage':'error','status':'error','output':str(e)})}\n\n"
        finally:
            yield f"data: {json.dumps({'done': True})}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
