from fastapi import FastAPI
from jira.jira_reader import get_user_story
from agents.builder_agent import build_code

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Working"}

@app.get("/build")
def build():
    story = get_user_story()
    build_code(story)
    return {"status": "API generated"}