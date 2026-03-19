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
from pydantic import BaseModel

from jira.jira_reader import get_user_story
from jira.jira_client import search_tickets
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


# ── LLM Settings ──────────────────────────────────────────────────────────────

PROVIDER_KEY_MAP = {
    "claude": "ANTHROPIC_API_KEY",
    "groq":   "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "ollama": None,
}

class LLMSettings(BaseModel):
    provider: str
    api_key: str = ""

@app.get("/settings/llm")
def get_llm_settings():
    provider = os.environ.get("LLM_PROVIDER", "claude")
    key_var  = PROVIDER_KEY_MAP.get(provider)
    key_set  = bool(os.environ.get(key_var, "")) if key_var else True
    return {"provider": provider, "api_key_set": key_set}

@app.post("/settings/llm")
def save_llm_settings(body: LLMSettings):
    provider = body.provider.lower()
    if provider not in PROVIDER_KEY_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    # Update env vars in the running process
    os.environ["LLM_PROVIDER"] = provider
    import llm_client
    llm_client.PROVIDER = provider

    key_var = PROVIDER_KEY_MAP[provider]
    if key_var and body.api_key.strip():
        os.environ[key_var] = body.api_key.strip()

    # Persist to .env file
    _save_to_env("LLM_PROVIDER", provider)
    if key_var and body.api_key.strip():
        _save_to_env(key_var, body.api_key.strip())

    return {"status": "saved", "provider": provider, "api_key_set": bool(body.api_key or not key_var)}

def _save_to_env(key: str, value: str):
    env_path = Path(__file__).parent.parent / ".env"
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    updated = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
            new_lines.append(f"{key}={value}")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(new_lines) + "\n")


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
