"""
SCRIBE Agent — the final stage. Writes engineering.md, posts a summary
comment on the Jira ticket, transitions it to Done, and swaps labels
from pace-in-progress → pace-shipped.
"""
import os
from datetime import datetime
from jira.jira_client import post_comment, transition_ticket, add_label, remove_label

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINEERING_MD = os.path.join(REPO_ROOT, "engineering.md")


def run_scribe(state: dict) -> dict:
    story_card = state.get("story_card", {})
    ticket_id = story_card.get("ticket_id", state.get("ticket_id", ""))
    errors = []

    final_decision = _compute_final_decision(state)
    md_content = _render_engineering_md(state, final_decision)

    # Write engineering.md
    with open(ENGINEERING_MD, "w") as f:
        f.write(md_content)

    # Post Jira comment
    comment_posted = False
    try:
        post_comment(ticket_id, _build_jira_comment_text(state, final_decision))
        comment_posted = True
    except Exception as e:
        errors.append(f"SCRIBE: Could not post comment: {e}")

    # Transition to Done only if SHIPPED
    transitioned = False
    if final_decision == "SHIPPED":
        try:
            transition_ticket(ticket_id, "Done")
            transitioned = True
        except Exception as e:
            errors.append(f"SCRIBE: Could not transition ticket: {e}")

    # Swap labels
    try:
        remove_label(ticket_id, "pace-in-progress")
        add_label(ticket_id, "pace-shipped" if final_decision == "SHIPPED" else "pace-blocked")
    except Exception as e:
        errors.append(f"SCRIBE: Could not update labels: {e}")

    scribe_result = {
        "final_decision": final_decision,
        "engineering_md_path": ENGINEERING_MD,
        "jira_comment_posted": comment_posted,
        "transitioned_to_done": transitioned,
    }
    return {
        **state,
        "scribe_result": scribe_result,
        "pipeline_decision": final_decision,
        "errors": state.get("errors", []) + errors,
    }


# ── Decision ──────────────────────────────────────────────────────────────────

def _compute_final_decision(state: dict) -> str:
    gate = state.get("gate_result", {}).get("decision", "HOLD")
    sentinel = state.get("sentinel_result", {}).get("decision", "HOLD")
    conduit = state.get("conduit_result", {}).get("decision", "HOLD")
    gate_ok = gate == "SHIP"
    sentinel_ok = sentinel in ("SHIP", "ADVISORY")
    conduit_ok = conduit in ("SHIP", "ADVISORY")
    return "SHIPPED" if (gate_ok and sentinel_ok and conduit_ok) else "BLOCKED"


# ── Engineering.md ────────────────────────────────────────────────────────────

def _render_engineering_md(state: dict, final_decision: str) -> str:
    card = state.get("story_card", {})
    gate = state.get("gate_result", {})
    sentinel = state.get("sentinel_result", {})
    conduit = state.get("conduit_result", {})
    forge = state.get("forge_result", {})
    ticket_id = card.get("ticket_id", "N/A")

    ac_rows = "\n".join(
        f"| {v['ac_id']} | {v.get('description', '')} | {'✅ PASS' if v['passed'] else '❌ FAIL'} |"
        for v in gate.get("ac_verdicts", [])
    )

    sentinel_rows = "\n".join(
        f"| {f['type']} | {f['severity']} | {f.get('line', '—')} | {f['detail']} |"
        for f in sentinel.get("findings", [])
    ) or "| — | — | — | No findings |"

    conduit_rows = "\n".join(
        f"| {c['name']} | {c['status']} | {c['detail']} |"
        for c in conduit.get("checks", [])
    ) or "| — | — | No checks run |"

    return f"""# Engineering Report: {ticket_id} — {card.get('title', '')}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Branch:** `{state.get('branch_name', card.get('branch_name', 'N/A'))}`
**Pipeline Decision:** {final_decision}

---

## Story Card

| Field | Value |
|-------|-------|
| Ticket | {ticket_id} |
| Priority | {card.get('priority', '—')} |
| Story Points | {card.get('story_points', '—')} |
| Framework | {card.get('framework', 'fastapi')} |

---

## Acceptance Criteria — GATE ({gate.get('decision', '—')})

| AC ID | Description | Result |
|-------|-------------|--------|
{ac_rows if ac_rows else '| — | — | No tests run |'}

**{gate.get('passed', 0)}/{gate.get('total', 0)} ACs passed.**

---

## Security Scan — SENTINEL ({sentinel.get('decision', '—')})

{sentinel.get('summary', '')}

| Type | Severity | Line | Detail |
|------|----------|------|--------|
{sentinel_rows}

---

## CI/CD Review — CONDUIT ({conduit.get('decision', '—')})

{conduit.get('summary', '')}

| Check | Status | Detail |
|-------|--------|--------|
{conduit_rows}

---

## Forge Summary

- **Branch:** `{forge.get('branch', '—')}`
- **Commit:** {forge.get('commit_message', '—')}
- **Push:** {forge.get('push_status', '—')}
"""


# ── Jira comment text ─────────────────────────────────────────────────────────

def _build_jira_comment_text(state: dict, final_decision: str) -> str:
    gate = state.get("gate_result", {})
    sentinel = state.get("sentinel_result", {})
    conduit = state.get("conduit_result", {})
    branch = state.get("branch_name", "—")
    passed = gate.get("passed", 0)
    total = gate.get("total", 0)

    lines = [
        f"PACE Pipeline Complete: {final_decision}",
        "",
        f"GATE: {gate.get('decision', '—')}  |  SENTINEL: {sentinel.get('decision', '—')}  |  CONDUIT: {conduit.get('decision', '—')}",
        f"Acceptance Criteria: {passed}/{total} passed",
        f"Branch: {branch}",
    ]
    if sentinel.get("findings"):
        lines.append(f"Security findings: {len(sentinel['findings'])} ({sentinel.get('summary', '')})")
    lines.append("See engineering.md on the branch for the full report.")
    return "\n".join(lines)
