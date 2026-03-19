"""
PRIME Agent — validates a Jira ticket, generates story-card.yaml,
transitions the ticket to In Progress, and adds the pace-in-progress label.
"""
import re
import yaml
import ollama
from jira.jira_client import get_ticket, post_comment, transition_ticket, add_label

STORY_CARD_PATH = "story-card.yaml"
LLM_MODEL = "codellama"

PRIME_PROMPT = """\
You are a software project manager. Convert the following Jira ticket into a structured YAML story card.
Output ONLY valid YAML — no markdown fences, no prose, no explanations.

Ticket ID: {ticket_id}
Title: {title}
Description: {description}
Priority: {priority}
Story Points: {story_points}
Acceptance Criteria:
{ac_list}

Generate YAML with this exact schema:
ticket_id: <value>
title: <value>
description: <one-line summary>
priority: <value>
story_points: <integer>
branch_name: feature/{branch_slug}
language: python
framework: fastapi
acceptance_criteria:
  - id: ac1
    description: <AC text>
    implementation_hint: <one sentence hint for implementation>
    test_hint: <one sentence hint for testing>

Rules:
- branch_name must be lowercase with hyphens only, max 60 chars
- Each AC must have all four fields (id, description, implementation_hint, test_hint)
- Output ONLY the YAML block, nothing else
"""


def run_prime(state: dict) -> dict:
    ticket_id = state["ticket_id"]
    errors = []

    try:
        ticket = get_ticket(ticket_id)
    except Exception as e:
        return {**state, "errors": state.get("errors", []) + [f"PRIME: Failed to fetch ticket: {e}"]}

    valid, reason = _validate_ticket(ticket)
    if not valid:
        msg = f"PACE PRIME: Ticket lacks sufficient info to build — {reason}"
        try:
            post_comment(ticket_id, msg)
        except Exception:
            pass
        return {**state, "errors": state.get("errors", []) + [f"PRIME: {reason}"]}

    story_card = _generate_story_card(ticket)
    _write_story_card(story_card, STORY_CARD_PATH)

    # Jira updates (best-effort — don't abort pipeline on failure)
    try:
        post_comment(ticket_id, f"PACE PRIME: Story Card ready. Branch: {story_card['branch_name']}. FORGE next.")
    except Exception as e:
        errors.append(f"PRIME: Could not post comment: {e}")

    try:
        transition_ticket(ticket_id, "In Progress")
    except Exception as e:
        errors.append(f"PRIME: Could not transition ticket: {e}")

    try:
        add_label(ticket_id, "pace-in-progress")
    except Exception as e:
        errors.append(f"PRIME: Could not add label: {e}")

    return {
        **state,
        "story_card": story_card,
        "story_card_path": STORY_CARD_PATH,
        "branch_name": story_card["branch_name"],
        "errors": state.get("errors", []) + errors,
    }


# ── Validation ────────────────────────────────────────────────────────────────

def _validate_ticket(ticket: dict) -> tuple[bool, str]:
    if not ticket.get("title", "").strip():
        return False, "Title is empty"
    if len(ticket.get("description", "")) < 10:
        return False, "Description is too short"
    # AC can be empty — PRIME's LLM will extract them from the description
    return True, ""


# ── Story card generation ─────────────────────────────────────────────────────

def _generate_story_card(ticket: dict) -> dict:
    ac_list = "\n".join(
        f"  {i+1}. {ac}" for i, ac in enumerate(ticket["acceptance_criteria"])
    )
    branch_slug = _make_branch_slug(ticket["id"], ticket["title"])
    prompt = PRIME_PROMPT.format(
        ticket_id=ticket["id"],
        title=ticket["title"],
        description=ticket["description"],
        priority=ticket.get("priority", "Medium"),
        story_points=ticket.get("story_points", 0),
        ac_list=ac_list,
        branch_slug=branch_slug,
    )
    try:
        resp = ollama.chat(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp["message"]["content"].strip()
        # Strip markdown fences if present
        raw = re.sub(r"^```[a-z]*\n?", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"```$", "", raw, flags=re.MULTILINE)
        card = yaml.safe_load(raw.strip())
        if isinstance(card, dict) and "acceptance_criteria" in card:
            return card
    except Exception:
        pass
    return _build_story_card_fallback(ticket, branch_slug)


def _build_story_card_fallback(ticket: dict, branch_slug: str) -> dict:
    # Use extracted ACs if available, otherwise derive one from the title
    acs = ticket.get("acceptance_criteria") or [ticket["title"]]
    return {
        "ticket_id": ticket["id"],
        "title": ticket["title"],
        "description": ticket["description"][:300],
        "priority": ticket.get("priority", "Medium"),
        "story_points": ticket.get("story_points", 0),
        "branch_name": f"feature/{branch_slug}",
        "language": "python",
        "framework": "fastapi",
        "acceptance_criteria": [
            {
                "id": f"ac{i+1}",
                "description": ac,
                "implementation_hint": f"Implement: {ac}",
                "test_hint": f"Test that: {ac}",
            }
            for i, ac in enumerate(acs)
        ],
    }


def _make_branch_slug(ticket_id: str, title: str) -> str:
    id_part = ticket_id.lower().replace(" ", "-")
    title_slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    return f"{id_part}-{title_slug}"


def _write_story_card(card: dict, path: str) -> None:
    with open(path, "w") as f:
        yaml.dump(card, f, default_flow_style=False, allow_unicode=True)
