"""
FORGE Agent — reads story-card.yaml, creates a git branch, and for each
acceptance criterion runs a TDD loop: write failing test → write implementation
to pass it → retry up to 3× on failure → refactor → commit → push.
"""
import os
import re
import subprocess
import yaml
import git
import llm_client
from jira.jira_client import post_comment
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_TDD_ATTEMPTS = 3

TEST_PROMPT = """\
You are a senior Python test engineer using pytest and FastAPI TestClient.

Story: {title}
Acceptance Criterion {ac_id}: {ac_description}
Test hint: {test_hint}

The FastAPI app is importable as:
  from generated.{slug}.app import app

Current contents of generated/{slug}/app.py (use this to match real endpoint paths and function names):
```python
{current_code}
```

Write a pytest test file that:
1. Imports TestClient from fastapi.testclient and imports app from generated.{slug}.app
2. Has exactly one test function: def test_{ac_id}():
3. Tests ONLY this acceptance criterion: {ac_description}
4. Asserts the expected behaviour described in the test hint
5. Uses ONLY routes, functions and variable names that exist in the current app code above — never invent endpoints or mock functions that are not there

Output ONLY valid Python code. No markdown fences. No explanations.
"""

IMPL_PROMPT = """\
You are a senior Python engineer writing FastAPI code.

Story: {title}
Framework: fastapi  Language: python
Acceptance Criterion {ac_id}: {ac_description}
Implementation hint: {implementation_hint}
{error_section}
Current contents of generated/{slug}/app.py:
```
{current_code}
```

Instructions:
- If the file is empty, start with: from fastapi import FastAPI; app = FastAPI()
- If app already exists, ADD new routes/logic — do NOT redefine app or existing routes
- Make ONLY the changes needed for this acceptance criterion
- The variable holding the FastAPI instance MUST be named `app`

Output ONLY valid Python code. No markdown fences. No explanations.
"""

REFACTOR_PROMPT = """\
You are a senior Python engineer. Refactor the following code for clarity,
remove duplication, and ensure PEP 8. Do not change any behaviour.

```python
{current_code}
```

Output ONLY valid Python code. No markdown fences. No explanations.
"""


def run_forge(state: dict) -> dict:
    story_card = state.get("story_card", {})
    if not story_card:
        try:
            with open(state.get("story_card_path", "story-card.yaml")) as f:
                story_card = yaml.safe_load(f)
        except Exception as e:
            return {**state, "errors": state.get("errors", []) + [f"FORGE: Cannot read story card: {e}"]}

    ticket_id = story_card["ticket_id"]
    slug = _ticket_slug(ticket_id)
    branch_name = story_card.get("branch_name", f"feature/{slug}")
    errors = []
    ac_results = []

    # Create git branch
    try:
        repo = _create_branch(REPO_ROOT, branch_name)
    except Exception as e:
        errors.append(f"FORGE: Branch creation failed: {e}")
        repo = None

    # Ensure generated package directories exist
    gen_dir = os.path.join(REPO_ROOT, "generated", slug)
    test_dir = os.path.join(REPO_ROOT, "tests", "generated")
    os.makedirs(gen_dir, exist_ok=True)
    os.makedirs(test_dir, exist_ok=True)
    _touch(os.path.join(REPO_ROOT, "generated", "__init__.py"))
    _touch(os.path.join(gen_dir, "__init__.py"))
    _touch(os.path.join(test_dir, "__init__.py"))
    _ensure_conftest(test_dir)

    # TDD loop per acceptance criterion
    for i, ac in enumerate(story_card.get("acceptance_criteria", [])):
        result = _tdd_loop(ac, story_card, slug, i)
        ac_results.append(result)

    # Refactor the generated app
    _refactor(slug)

    # Commit and push
    forge_result = {}
    if repo:
        try:
            forge_result = _commit_and_push(repo, branch_name, ticket_id, ac_results)
        except Exception as e:
            errors.append(f"FORGE: Commit/push failed: {e}")
            forge_result = {"error": str(e)}

    # Jira comment
    passed = sum(1 for r in ac_results if r["passed"])
    total = len(ac_results)
    try:
        post_comment(
            ticket_id,
            f"PACE FORGE: {total} ACs processed ({passed} passed). "
            f"Branch: {branch_name}. "
            f"Files built in generated/{slug}/.",
        )
    except Exception as e:
        errors.append(f"FORGE: Could not post comment: {e}")

    return {
        **state,
        "branch_name": branch_name,
        "forge_result": forge_result,
        "ac_results": ac_results,
        "errors": state.get("errors", []) + errors,
    }


# ── TDD loop ──────────────────────────────────────────────────────────────────

def _tdd_loop(ac: dict, story_card: dict, slug: str, index: int) -> dict:
    ac_id = ac.get("id", f"ac{index+1}")
    test_file = os.path.join(REPO_ROOT, "tests", "generated", f"test_{slug}_{ac_id}.py")
    impl_file = os.path.join(REPO_ROOT, "generated", slug, "app.py")

    # Step 1 — write test, giving the LLM a view of what's already in app.py
    current_code = _read_file(impl_file)
    test_code = _generate_test(ac, story_card, slug, current_code)
    _write_file(test_file, test_code)

    passed = False
    last_error = ""
    for attempt in range(1, MAX_TDD_ATTEMPTS + 1):
        current_code = _read_file(impl_file)
        error_section = (
            f"Previous test failure (attempt {attempt-1}):\n{last_error}\nFix the code above.\n"
            if last_error else ""
        )
        impl_code = _generate_impl(ac, story_card, slug, current_code, error_section)
        _write_file(impl_file, impl_code)

        result = _run_pytest(test_file)
        if result["passed"]:
            passed = True
            break
        last_error = result["stdout"][-2000:]  # keep last 2 KB of output

    return {
        "ac_id": ac_id,
        "description": ac.get("description", ""),
        "passed": passed,
        "attempts": attempt,
        "test_file": test_file,
    }


# ── LLM calls ─────────────────────────────────────────────────────────────────

def _generate_test(ac: dict, story_card: dict, slug: str, current_code: str = "") -> str:
    prompt = TEST_PROMPT.format(
        title=story_card["title"],
        ac_id=ac["id"],
        ac_description=ac["description"],
        test_hint=ac.get("test_hint", ""),
        slug=slug,
        current_code=current_code or "(empty — app not yet written)",
    )
    return _llm(prompt)


def _generate_impl(ac: dict, story_card: dict, slug: str, current_code: str, error_section: str) -> str:
    prompt = IMPL_PROMPT.format(
        title=story_card["title"],
        ac_id=ac["id"],
        ac_description=ac["description"],
        implementation_hint=ac.get("implementation_hint", ""),
        slug=slug,
        error_section=error_section,
        current_code=current_code or "",
    )
    return _llm(prompt)


def _refactor(slug: str) -> None:
    impl_file = os.path.join(REPO_ROOT, "generated", slug, "app.py")
    current_code = _read_file(impl_file)
    if not current_code.strip():
        return
    prompt = REFACTOR_PROMPT.format(current_code=current_code)
    refactored = _llm(prompt)
    if refactored.strip():
        _write_file(impl_file, refactored)


def _llm(prompt: str) -> str:
    raw = llm_client.chat(prompt, system="You are an expert Python engineer. Output only valid Python code, no markdown fences, no explanations.").strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```$", "", raw, flags=re.MULTILINE)
    return raw.strip()


# ── Git operations ────────────────────────────────────────────────────────────

def _create_branch(repo_root: str, branch_name: str) -> git.Repo:
    repo = git.Repo(repo_root)
    # If branch already exists, just check it out
    if branch_name in [b.name for b in repo.branches]:
        repo.git.checkout(branch_name)
    else:
        repo.git.checkout("-b", branch_name)
    return repo


def _commit_and_push(repo: git.Repo, branch_name: str, ticket_id: str, ac_results: list) -> dict:
    repo.git.add(".")
    passed = sum(1 for r in ac_results if r["passed"])
    msg = f"PACE FORGE: {ticket_id} — TDD implementation ({passed}/{len(ac_results)} ACs passed)"
    repo.index.commit(msg)
    origin = repo.remote("origin")
    push_info = origin.push(refspec=f"{branch_name}:{branch_name}", set_upstream=True)
    return {
        "branch": branch_name,
        "commit_message": msg,
        "push_status": str(push_info[0].summary) if push_info else "pushed",
    }


# ── Filesystem helpers ────────────────────────────────────────────────────────

def _ticket_slug(ticket_id: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", ticket_id.lower()).strip("_")


def _read_file(path: str) -> str:
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return ""


def _write_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def _touch(path: str) -> None:
    if not os.path.exists(path):
        open(path, "w").close()


def _ensure_conftest(test_dir: str) -> None:
    conftest = os.path.join(test_dir, "conftest.py")
    if not os.path.exists(conftest):
        _write_file(conftest, f'import sys, os\nsys.path.insert(0, r"{REPO_ROOT}")\n')


def _run_pytest(test_file: str) -> dict:
    python = os.path.join(REPO_ROOT, "venv", "Scripts", "python.exe")
    if not os.path.exists(python):
        python = "python"
    result = subprocess.run(
        [python, "-m", "pytest", test_file, "-v", "--tb=short"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return {
        "passed": result.returncode == 0,
        "stdout": result.stdout + result.stderr,
        "returncode": result.returncode,
    }
