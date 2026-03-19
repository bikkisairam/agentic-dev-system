import os
import requests
from requests.auth import HTTPBasicAuth

JIRA_URL = os.environ.get("JIRA_URL", "https://YOUR_COMPANY.atlassian.net")
JIRA_USERNAME = os.environ.get("JIRA_USERNAME", "your@email.com")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "your-api-token-here")


def get_user_story(ticket_id: str = "JIRA-101"):
    """Fetch a real Jira ticket by ID."""
    url = f"{JIRA_URL}/rest/api/3/issue/{ticket_id}"
    auth = HTTPBasicAuth(JIRA_USERNAME, JIRA_API_TOKEN)
    headers = {"Accept": "application/json"}

    response = requests.get(url, headers=headers, auth=auth)
    response.raise_for_status()

    data = response.json()
    fields = data["fields"]

    # Extract acceptance criteria from description (Atlassian Document Format)
    description_text = _extract_text(fields.get("description"))
    acceptance_criteria = _extract_acceptance_criteria(description_text)

    return {
        "id": data["key"],
        "title": fields.get("summary", ""),
        "description": description_text,
        "acceptance_criteria": acceptance_criteria,
        "status": fields.get("status", {}).get("name", ""),
        "assignee": (fields.get("assignee") or {}).get("displayName", "Unassigned"),
    }


def _extract_text(adf_doc) -> str:
    """Recursively extract plain text from Atlassian Document Format (ADF)."""
    if not adf_doc:
        return ""
    if isinstance(adf_doc, str):
        return adf_doc
    text_parts = []
    if adf_doc.get("type") == "text":
        text_parts.append(adf_doc.get("text", ""))
    for child in adf_doc.get("content", []):
        text_parts.append(_extract_text(child))
    return " ".join(p for p in text_parts if p).strip()


def _extract_acceptance_criteria(description: str) -> list[str]:
    """Parse acceptance criteria lines from description text."""
    criteria = []
    in_ac_section = False
    for line in description.splitlines():
        line = line.strip()
        lower = line.lower()
        if "acceptance criteria" in lower or "acceptance criterion" in lower:
            in_ac_section = True
            continue
        if in_ac_section and line.startswith(("-", "*", "•")):
            criteria.append(line.lstrip("-*• ").strip())
        elif in_ac_section and line and not line.startswith(("-", "*", "•")):
            # Stop at next section heading (non-bullet, non-empty)
            if len(line) < 60 and not line.endswith("."):
                break
    return criteria if criteria else [description] if description else []


def format_story_for_agent(story):
    criteria = "\n".join(f"- {c}" for c in story.get("acceptance_criteria", []))
    return f"""User Story: {story['title']}
Description: {story['description']}
Acceptance Criteria:
{criteria}"""
