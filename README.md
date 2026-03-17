# Agentic Dev System

An AI-powered code generation pipeline that automatically takes a requirement (Jira story), generates a FastAPI app using a local LLM, tests it, and commits it — all orchestrated by LangGraph.

## Architecture

```
Angular UI (port 4200)
      │
FastAPI Server (port 8005)
      │
LangGraph Orchestrator
      ├── PLAN     → Fetch Jira story
      ├── BUILD    → Generate API code via Ollama (CodeLlama)
      ├── CHECK    → Test with FastAPI TestClient
      └── EVALUATE → Git commit if tests pass
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com) with CodeLlama pulled
- Git

## Setup

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd agentic-dev-system
```

### 2. Python backend

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
```

### 3. Pull the LLM

```bash
ollama pull codellama
```

### 4. Angular frontend

```bash
cd ui
npm install
```

### 5. Initialize git (for the commit stage)

```bash
cd ..
git init
git add .
git commit -m "initial commit"
```

## Running

### Start the backend

```bash
cd agentic-dev-system
venv\Scripts\activate
uvicorn api.server:app --port 8005 --reload
```

### Start the frontend (new terminal)

```bash
cd agentic-dev-system/ui
npm start
```

Open **http://localhost:4200**

## Pipeline Stages

| Stage    | What it does |
|----------|-------------|
| Plan     | Reads the Jira user story (mock) |
| Build    | Uses CodeLlama to generate `generated_api.py` |
| Check    | Tests the generated API using FastAPI TestClient |
| Evaluate | Commits the code to git if all tests pass |

## Project Structure

```
agentic-dev-system/
├── api/server.py                  # FastAPI server with PACE endpoints
├── orchestrator/pace_orchestrator.py  # LangGraph workflow
├── agents/
│   ├── builder_agent.py           # LLM code generation
│   ├── test_runner.py             # TestClient-based testing
│   ├── devops_agent.py            # Git commit
│   └── deploy_agent.py            # Uvicorn deployment
├── jira/jira_reader.py            # Mock Jira story
├── generated_api.py               # Output: AI-generated FastAPI app
├── requirements.txt
└── ui/                            # Angular frontend
```
