"""
Unified LLM client for all PACE agents.

Switch provider by setting LLM_PROVIDER in .env:
  LLM_PROVIDER=claude   → Anthropic Claude (default, recommended)
  LLM_PROVIDER=groq     → Groq (free, very fast)
  LLM_PROVIDER=openai   → OpenAI GPT-4o-mini
  LLM_PROVIDER=ollama   → Local Ollama (original)

Required env vars per provider:
  claude : ANTHROPIC_API_KEY
  groq   : GROQ_API_KEY
  openai : OPENAI_API_KEY
  ollama : (none — must be running locally)
"""
import os

PROVIDER = os.environ.get("LLM_PROVIDER", "claude").lower()


def chat(prompt: str, system: str = "You are an expert software engineer.") -> str:
    """Send a prompt and return the text response."""
    if PROVIDER == "claude":
        return _claude(prompt, system)
    elif PROVIDER == "groq":
        return _groq(prompt, system)
    elif PROVIDER == "openai":
        return _openai(prompt, system)
    elif PROVIDER == "ollama":
        return _ollama(prompt)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {PROVIDER!r}")


# ── Providers ─────────────────────────────────────────────────────────────────

def _claude(prompt: str, system: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model=os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def _groq(prompt: str, system: str) -> str:
    import requests
    headers = {
        "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
        "Content-Type": "application/json",
    }
    body = {
        "model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens": 4096,
        "temperature": 0.2,
    }
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                      headers=headers, json=body, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _openai(prompt: str, system: str) -> str:
    import requests
    headers = {
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        "Content-Type": "application/json",
    }
    body = {
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens": 4096,
        "temperature": 0.2,
    }
    r = requests.post("https://api.openai.com/v1/chat/completions",
                      headers=headers, json=body, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _ollama(prompt: str) -> str:
    import ollama
    model = os.environ.get("OLLAMA_MODEL", "codellama")
    resp = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
    return resp["message"]["content"]
