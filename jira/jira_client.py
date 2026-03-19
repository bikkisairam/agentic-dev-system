import os
import requests
from requests.auth import HTTPBasicAuth

JIRA_URL = os.environ.get("JIRA_URL", "https://YOUR_COMPANY.atlassian.net")
JIRA_USERNAME = os.environ.get("JIRA_USERNAME", "your@email.com")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "your-api-token-here")


def _auth():
    return HTTPBasicAuth(JIRA_USERNAME, JIRA_API_TOKEN)


def _headers():
    return {"Accept": "application/json", "Content-Type": "application/json"}


def search_tickets(jql: str, max_results: int = 50) -> list[dict]:
    # Atlassian deprecated GET /search — use POST /search/jql instead
    url = f"{JIRA_URL}/rest/api/3/search/jql"
    body = {
        "jql": jql,
        "maxResults": max_results,
        "fields": ["summary", "description", "status", "priority",
                   "labels", "assignee", "issuetype", "customfield_10016"],
    }
    resp = requests.post(url, headers=_headers(), auth=_auth(), json=body)
    resp.raise_for_status()
    return [_normalize_issue(i) for i in resp.json().get("issues", [])]


def get_ticket(ticket_id: str) -> dict:
    url = f"{JIRA_URL}/rest/api/3/issue/{ticket_id}"
    resp = requests.get(url, headers=_headers(), auth=_auth())
    resp.raise_for_status()
    return _normalize_issue(resp.json())


def post_comment(ticket_id: str, text: str) -> dict:
    url = f"{JIRA_URL}/rest/api/3/issue/{ticket_id}/comment"
    resp = requests.post(url, headers=_headers(), auth=_auth(), json={"body": _text_to_adf(text)})
    resp.raise_for_status()
    return resp.json()


def get_transitions(ticket_id: str) -> list[dict]:
    url = f"{JIRA_URL}/rest/api/3/issue/{ticket_id}/transitions"
    resp = requests.get(url, headers=_headers(), auth=_auth())
    resp.raise_for_status()
    return resp.json().get("transitions", [])


def transition_ticket(ticket_id: str, transition_name: str) -> bool:
    transitions = get_transitions(ticket_id)
    match = next(
        (t for t in transitions if t["to"]["name"].lower() == transition_name.lower()),
        None,
    )
    if not match:
        available = [t["to"]["name"] for t in transitions]
        raise ValueError(f"Transition '{transition_name}' not found. Available: {available}")
    url = f"{JIRA_URL}/rest/api/3/issue/{ticket_id}/transitions"
    resp = requests.post(url, headers=_headers(), auth=_auth(), json={"transition": {"id": match["id"]}})
    resp.raise_for_status()
    return True


def add_label(ticket_id: str, label: str) -> bool:
    url = f"{JIRA_URL}/rest/api/3/issue/{ticket_id}"
    resp = requests.put(url, headers=_headers(), auth=_auth(),
                        json={"update": {"labels": [{"add": label}]}})
    resp.raise_for_status()
    return True


def remove_label(ticket_id: str, label: str) -> bool:
    url = f"{JIRA_URL}/rest/api/3/issue/{ticket_id}"
    resp = requests.put(url, headers=_headers(), auth=_auth(),
                        json={"update": {"labels": [{"remove": label}]}})
    resp.raise_for_status()
    return True


# ── Internal helpers ──────────────────────────────────────────────────────────

def _normalize_issue(issue: dict) -> dict:
    fields = issue.get("fields", {})
    description_raw = fields.get("description", "")
    description = (
        _extract_text(description_raw)
        if isinstance(description_raw, dict)
        else (description_raw or "")
    )
    return {
        "id": issue.get("key", ""),
        "title": fields.get("summary", ""),
        "description": description,
        "status": (fields.get("status") or {}).get("name", ""),
        "priority": (fields.get("priority") or {}).get("name", "Medium"),
        "story_points": fields.get("customfield_10016") or fields.get("story_points") or 0,
        "labels": fields.get("labels", []),
        "assignee": ((fields.get("assignee") or {}).get("displayName") or "Unassigned"),
        "acceptance_criteria": _extract_acceptance_criteria(description),
    }


def _text_to_adf(text: str) -> dict:
    paragraphs = []
    for line in text.split("\n"):
        paragraphs.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": line or " "}],
        })
    return {"version": 1, "type": "doc", "content": paragraphs}


def _extract_text(adf_doc) -> str:
    """Recursively extract text from ADF, preserving newlines for block nodes."""
    if not adf_doc:
        return ""
    if isinstance(adf_doc, str):
        return adf_doc

    node_type = adf_doc.get("type", "")

    # Leaf text node
    if node_type == "text":
        return adf_doc.get("text", "")

    # Recurse into children
    child_texts = [_extract_text(c) for c in adf_doc.get("content", [])]
    child_texts = [t for t in child_texts if t]

    # Block-level nodes get newlines between them
    block_types = {"paragraph", "heading", "listItem", "bulletList",
                   "orderedList", "blockquote", "codeBlock", "rule"}
    if node_type in block_types:
        return "\n".join(child_texts)

    return " ".join(child_texts)


def _extract_acceptance_criteria(description: str) -> list[str]:
    """
    Extract acceptance criteria from a description string.
    Handles both newline-separated bullets and inline ' - ' patterns.
    """
    criteria = []

    # Strategy 1: look for a section heading then newline-separated bullets
    in_ac = False
    for line in description.splitlines():
        stripped = line.strip()
        if "acceptance criteria" in stripped.lower() or "acceptance criterion" in stripped.lower():
            in_ac = True
            continue
        if in_ac:
            if stripped.startswith(("-", "*", "•")):
                criteria.append(stripped.lstrip("-*• ").strip())
            elif stripped and not stripped.startswith(("-", "*", "•")):
                # Stop at next section heading (short non-bullet line)
                if criteria and len(stripped) < 60 and not stripped.endswith("."):
                    break

    if criteria:
        return criteria

    # Strategy 2: inline pattern — split on ' - ' after "Acceptance Criteria:"
    import re
    match = re.search(
        r"acceptance criteri[ao]n?[:\s]+(.*?)(?:\n[A-Z]|\Z)",
        description,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        ac_block = match.group(1)
        # Split on common delimiters: newline, ' - ', numbered list
        parts = re.split(r"\n|(?<!\w) - |(?<=\w)\. (?=[A-Z])", ac_block)
        for part in parts:
            part = part.strip().lstrip("-•*0123456789.)").strip()
            if len(part) > 5:
                criteria.append(part)

    return criteria
