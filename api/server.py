import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from jira.jira_reader import get_user_story
from agents.builder_agent import build_code
from agents.test_runner import run_tests
from agents.devops_agent import commit_code, push_code
from orchestrator.pace_orchestrator import run_pace, stream_pace

app = FastAPI(title="Agentic Dev System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "Agentic Dev System is running"}


@app.get("/jira-story")
def jira_story():
    try:
        story = get_user_story()
        return {"story": story}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        result = run_tests()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/commit")
def commit():
    try:
        result = commit_code()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/push")
def push():
    try:
        result = push_code()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/run")
def run():
    try:
        result = run_pace()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stream")
def stream():
    def event_generator():
        try:
            for event in stream_pace():
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'stage': 'error', 'status': 'error', 'output': str(e)})}\n\n"
        finally:
            yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )
