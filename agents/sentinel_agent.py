"""
SENTINEL Agent — uses the LLM to scan generated code for security vulnerabilities:
hardcoded secrets, SQL injection, and missing authentication.
Returns SHIP, HOLD, or ADVISORY with a findings list.
"""
import os
import re
import json
import llm_client
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SENTINEL_PROMPT = """\
You are a security code reviewer. Analyze the following Python code for security vulnerabilities.
Check specifically for:

1. HARDCODED_SECRETS: API keys, passwords, tokens, or secrets hardcoded as string literals
   (values that should come from os.environ but are instead literal strings like "mysecret123")
2. SQL_INJECTION: Raw string formatting or concatenation used to build SQL queries
   (e.g., f"SELECT * FROM users WHERE id={{user_id}}" instead of parameterised queries)
3. MISSING_AUTH: FastAPI endpoints that handle sensitive data but have no authentication
   (no Depends(), no Bearer token check, no API key header, no OAuth)

Code to review:
```python
{code}
```

Respond with ONLY valid JSON in this exact format (no prose, no markdown):
{{
  "decision": "SHIP",
  "findings": [],
  "summary": "No security issues found."
}}

Or with findings:
{{
  "decision": "HOLD",
  "findings": [
    {{
      "type": "HARDCODED_SECRETS",
      "severity": "HIGH",
      "line": 12,
      "detail": "Password 'admin123' is hardcoded on line 12."
    }}
  ],
  "summary": "One HIGH severity issue found."
}}

Decision rules:
- "HOLD"     if any finding has severity "HIGH"
- "ADVISORY" if findings exist but none are HIGH
- "SHIP"     if findings list is empty
"""


def run_sentinel(state: dict) -> dict:
    story_card = state.get("story_card", {})
    ticket_id = story_card.get("ticket_id", state.get("ticket_id", ""))
    slug = _ticket_slug(ticket_id)

    code = _load_generated_code(slug)
    if not code.strip():
        sentinel_result = {
            "decision": "ADVISORY",
            "findings": [{"type": "MISSING_AUTH", "severity": "MEDIUM", "line": None,
                          "detail": "No generated code found to scan."}],
            "summary": "No generated code was available for security review.",
        }
    else:
        sentinel_result = _scan_code(code)

    return {**state, "sentinel_result": sentinel_result}


def _scan_code(code: str) -> dict:
    prompt = SENTINEL_PROMPT.format(code=code[:8000])  # cap at 8 KB
    try:
        raw = llm_client.chat(prompt, system="You are a security code reviewer. Output only valid JSON.").strip()
        # Strip markdown fences
        raw = re.sub(r"^```[a-z]*\n?", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"```$", "", raw, flags=re.MULTILINE)
        # Extract first JSON object
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
            if "decision" in result and "findings" in result:
                return result
    except Exception:
        pass
    # Fallback — cannot scan, flag for manual review
    return {
        "decision": "ADVISORY",
        "findings": [],
        "summary": "LLM security scan failed. Manual review required.",
    }


def _load_generated_code(slug: str) -> str:
    path = os.path.join(REPO_ROOT, "generated", slug, "app.py")
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return ""


def _ticket_slug(ticket_id: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", ticket_id.lower()).strip("_")
