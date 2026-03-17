import ollama
from jira.jira_reader import format_story_for_agent


def generate_tests(story):
    """
    Test Agent:
    Generates pytest test cases for the generated FastAPI application.
    """
    formatted = format_story_for_agent(story)

    prompt = f"""
Write pytest tests for a FastAPI application based on this user story:

{formatted}

Requirements:
- Import requests
- Test the /weather endpoint at http://127.0.0.1:8000/weather using GET
- Assert status_code == 200
- Assert content-type header starts with "application/json"
- Assert response JSON contains keys: temperature, humidity, weather

Output ONLY valid Python code with NO markdown, NO explanations.
"""

    response = ollama.chat(
        model="codellama",
        messages=[{"role": "user", "content": prompt}]
    )

    raw_code = response["message"]["content"]
    code = raw_code.replace("```python", "").replace("```", "").strip()

    with open("tests/test_generated_code.py", "w") as f:
        f.write(code)

    return code
