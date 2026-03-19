"""
GATE Agent — runs the full pytest suite for a ticket's generated tests,
maps each AC to pass/fail, and returns a SHIP or HOLD decision.
"""
import os
import glob
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_gate(state: dict) -> dict:
    story_card = state.get("story_card", {})
    ticket_id = story_card.get("ticket_id", state.get("ticket_id", ""))
    slug = _ticket_slug(ticket_id)

    ac_verdicts = _run_suite(slug, story_card)
    # all([]) is True in Python — treat zero tests as HOLD, not SHIP
    decision = "SHIP" if ac_verdicts and all(v["passed"] for v in ac_verdicts) else "HOLD"
    passed = sum(1 for v in ac_verdicts if v["passed"])

    gate_result = {
        "decision": decision,
        "ac_verdicts": ac_verdicts,
        "total": len(ac_verdicts),
        "passed": passed,
        "failed": len(ac_verdicts) - passed,
    }
    return {**state, "gate_result": gate_result}


def _run_suite(slug: str, story_card: dict) -> list[dict]:
    test_dir = os.path.join(REPO_ROOT, "tests", "generated")
    pattern = os.path.join(test_dir, f"test_{slug}_ac*.py")
    test_files = sorted(glob.glob(pattern))

    if not test_files:
        # No test files generated — treat all ACs as failed
        return [
            {"ac_id": ac.get("id", f"ac{i+1}"), "passed": False, "output": "No test file found"}
            for i, ac in enumerate(story_card.get("acceptance_criteria", []))
        ]

    verdicts = []
    for test_file in test_files:
        ac_id = _ac_id_from_filename(test_file, slug)
        result = _run_pytest(test_file)
        verdicts.append({
            "ac_id": ac_id,
            "passed": result["passed"],
            "output": result["stdout"][-1000:],
        })
    return verdicts


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
    }


def _ticket_slug(ticket_id: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "_", ticket_id.lower()).strip("_")


def _ac_id_from_filename(path: str, slug: str) -> str:
    name = os.path.basename(path)
    # test_{slug}_{ac_id}.py
    prefix = f"test_{slug}_"
    if name.startswith(prefix):
        return name[len(prefix):].replace(".py", "")
    return name
