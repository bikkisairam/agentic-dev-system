from jira.jira_reader import get_user_story
from agents.builder_agent import build_code
from agents.devops_agent import commit_code


def run_pace():
    """
    PACE Orchestration
    """

    result = {}

    # PLAN
    story = get_user_story()
    result["plan"] = "Jira story fetched"

    # ACT
    build_code(story)
    result["act"] = "Code generated"

    # CHECK
    result["check"] = "Skipped for now"  # we can add tests later

    # EVALUATE
    commit_code()
    result["evaluate"] = "Code committed"

    return result