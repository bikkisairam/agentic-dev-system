import ollama

def build_code(story):

    prompt = f"""
Create a FastAPI app with endpoint /weather.

Requirements:
- Return STATIC dummy JSON data (DO NOT call any external API)
- Example: temperature, humidity, weather
- Do NOT use OpenWeather or any external service
- Do NOT require API keys
- Keep it simple

Rules:
- Do NOT include markdown
- Only return Python code
- Must be runnable
"""

    response = ollama.chat(
        model="codellama",
        messages=[{"role": "user", "content": prompt}]
    )

    raw_code = response["message"]["content"]

    # CLEAN (very important)
    code = raw_code.replace("```python", "").replace("```", "").strip()

    with open("generated_api.py", "w") as f:
        f.write(code)

    return code