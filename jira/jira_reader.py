def get_user_story():
    return {
        "id": "JIRA-101",
        "title": "Weather API",
        "description": "Create a FastAPI endpoint /weather that returns dummy weather data",
        "acceptance_criteria": [
            "Endpoint /weather exists",
            "Returns JSON response with temperature, humidity, and weather fields",
            "Status code 200"
        ]
    }


def format_story_for_agent(story):
    criteria = "\n".join(f"- {c}" for c in story.get("acceptance_criteria", []))
    return f"""User Story: {story['title']}
Description: {story['description']}
Acceptance Criteria:
{criteria}"""
