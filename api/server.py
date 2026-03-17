from fastapi import FastAPI
from jira.jira_reader import get_user_story
from agents.builder_agent import build_code
from agents.devops_agent import commit_code
from orchestrator.pace_orchestrator import run_pace
app = FastAPI()

@app.get("/")
def home():
    return {"message": "Working"}

@app.get("/build")
def build():
    story = get_user_story()
    build_code(story)
    return {"status": "API generated"}
@app.get("/commit")
def commit():
    result = commit_code()
    return result
@app.get("/run")
def run():
    result = run_pace()
    return result