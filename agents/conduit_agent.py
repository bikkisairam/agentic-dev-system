"""
CONDUIT Agent — checks CI/CD configuration without calling the LLM.
Validates GitHub Actions workflow files: existence, action pinning,
lock files, and dangerous continue-on-error usage.
Returns SHIP, HOLD, or ADVISORY.
"""
import os
import re
import glob

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SEMVER_RE = re.compile(r"^v?\d+\.\d+\.\d+")
MUTABLE_RE = re.compile(r"^(v\d+|latest|main|master|HEAD)$")


def run_conduit(state: dict) -> dict:
    workflow_files = glob.glob(os.path.join(REPO_ROOT, ".github", "workflows", "*.yml"))
    workflow_files += glob.glob(os.path.join(REPO_ROOT, ".github", "workflows", "*.yaml"))

    checks = [
        _check_ci_exists(workflow_files),
        _check_action_pinning(workflow_files),
        _check_lock_files(),
        _check_continue_on_error(workflow_files),
    ]

    decision = _aggregate_decision(checks)
    summary_parts = [c["detail"] for c in checks if c["status"] != "PASS"]
    summary = "; ".join(summary_parts) if summary_parts else "All CI/CD checks passed."

    conduit_result = {
        "decision": decision,
        "checks": checks,
        "summary": summary,
    }
    return {**state, "conduit_result": conduit_result}


# ── Individual checks ─────────────────────────────────────────────────────────

def _check_ci_exists(workflow_files: list) -> dict:
    if workflow_files:
        return {"name": "CI file exists", "status": "PASS",
                "detail": f"Found {len(workflow_files)} workflow file(s)."}
    return {"name": "CI file exists", "status": "WARN",
            "detail": "No .github/workflows/*.yml files found. Consider adding CI."}


def _check_action_pinning(workflow_files: list) -> dict:
    if not workflow_files:
        return {"name": "Action pinning", "status": "PASS", "detail": "No workflows to check."}

    unpinned = []
    for wf in workflow_files:
        with open(wf) as f:
            content = f.read()
        for match in re.finditer(r"uses:\s*([^\s]+)", content):
            ref_str = match.group(1)
            if "@" not in ref_str:
                continue
            _, ref = ref_str.rsplit("@", 1)
            if MUTABLE_RE.match(ref):
                unpinned.append(ref_str)

    if not unpinned:
        return {"name": "Action pinning", "status": "PASS",
                "detail": "All action references are pinned."}
    return {"name": "Action pinning", "status": "FAIL",
            "detail": f"Unpinned action refs (use SHA): {', '.join(unpinned[:5])}"}


def _check_lock_files() -> dict:
    has_python = os.path.exists(os.path.join(REPO_ROOT, "requirements.txt"))
    has_node = (
        os.path.exists(os.path.join(REPO_ROOT, "package-lock.json"))
        or os.path.exists(os.path.join(REPO_ROOT, "yarn.lock"))
        or os.path.exists(os.path.join(REPO_ROOT, "ui", "package-lock.json"))
    )
    missing = []
    if not has_python:
        missing.append("requirements.txt")
    if os.path.exists(os.path.join(REPO_ROOT, "package.json")) and not has_node:
        missing.append("package-lock.json / yarn.lock")

    if not missing:
        return {"name": "Lock files", "status": "PASS", "detail": "Dependency lock files present."}
    return {"name": "Lock files", "status": "WARN",
            "detail": f"Missing lock files: {', '.join(missing)}"}


def _check_continue_on_error(workflow_files: list) -> dict:
    if not workflow_files:
        return {"name": "Continue-on-error", "status": "PASS", "detail": "No workflows to check."}

    risky_steps = []
    for wf in workflow_files:
        with open(wf) as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            if "continue-on-error: true" in line:
                risky_steps.append(f"{os.path.basename(wf)}:{i}")

    if not risky_steps:
        return {"name": "Continue-on-error", "status": "PASS",
                "detail": "No risky continue-on-error found."}
    return {"name": "Continue-on-error", "status": "FAIL",
            "detail": f"continue-on-error: true at: {', '.join(risky_steps[:5])}"}


# ── Decision aggregation ──────────────────────────────────────────────────────

def _aggregate_decision(checks: list) -> str:
    statuses = {c["status"] for c in checks}
    if "FAIL" in statuses:
        return "HOLD"
    if "WARN" in statuses:
        return "ADVISORY"
    return "SHIP"
