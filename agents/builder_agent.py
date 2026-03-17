import ollama
from jira.jira_reader import format_story_for_agent


def build_code(story):
    """
    Builder Agent:
    Generates a FastAPI application from a Jira user story using CodeLlama.
    """
    formatted = format_story_for_agent(story)

    prompt = f"""
Create a FastAPI application based on this user story:

{formatted}

Requirements:
- Return STATIC dummy JSON data only (DO NOT call any external API)
- Do NOT require API keys
- Keep it simple and runnable

Output ONLY valid Python code with NO markdown, NO explanations, NO prose.

Start with these imports:
from fastapi import FastAPI
import uvicorn

End with:
if __name__ == '__main__':
    uvicorn.run(app, host='localhost', port=8000)
"""

    response = ollama.chat(
        model="codellama",
        messages=[{"role": "user", "content": prompt}]
    )

    raw_code = response["message"]["content"]

    # Remove markdown code fences
    code = raw_code.replace("```python", "").replace("```", "").strip()

    # Ensure uvicorn is imported if used
    if "uvicorn.run" in code and "import uvicorn" not in code:
        code = "import uvicorn\n" + code

    # Strip trailing non-Python prose: find the last line that looks like Python
    lines = code.split("\n")
    last_valid = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if not stripped:
            continue
        # Python lines start with keywords, decorators, indentation, or identifiers
        python_starts = (
            "from ", "import ", "def ", "class ", "if ", "else", "elif ",
            "try", "except", "finally", "with ", "for ", "while ", "return",
            "    ", "\t", "@", "#", ")", "]", "}", "'", '"', "app", "uvicorn"
        )
        if any(stripped.startswith(kw) for kw in python_starts) or stripped[0].isalpha() or stripped[0] == "_":
            last_valid = i + 1
            break

    code = "\n".join(lines[:last_valid])

    with open("generated_api.py", "w") as f:
        f.write(code)

    return code
