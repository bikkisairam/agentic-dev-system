from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from jira.jira_reader import get_user_story
from agents.builder_agent import build_code
from agents.test_agent import generate_tests
from agents.test_runner import run_tests
from agents.devops_agent import commit_code


class PACEState(TypedDict):
    story: dict
    generated_code: str
    test_code: str
    test_result: dict
    commit_result: dict
    errors: List[str]


# ── Nodes ─────────────────────────────────────────────────────────────────────

def plan_node(state: PACEState) -> PACEState:
    """PLAN: Fetch the Jira user story."""
    try:
        story = get_user_story()
        return {**state, "story": story}
    except Exception as e:
        return {**state, "errors": state["errors"] + [f"PLAN: {e}"]}


def build_node(state: PACEState) -> PACEState:
    """ACT: Generate FastAPI code from the story."""
    if state["errors"]:
        return state
    try:
        code = build_code(state["story"])
        return {**state, "generated_code": code}
    except Exception as e:
        return {**state, "errors": state["errors"] + [f"BUILD: {e}"]}


def check_node(state: PACEState) -> PACEState:
    """CHECK: Generate tests and run them."""
    if state["errors"]:
        return state
    try:
        test_code = generate_tests(state["story"])
        test_result = run_tests()
        return {**state, "test_code": test_code, "test_result": test_result}
    except Exception as e:
        return {
            **state,
            "test_result": {"passed": False, "stderr": str(e)},
            "errors": state["errors"] + [f"CHECK: {e}"]
        }


def evaluate_node(state: PACEState) -> PACEState:
    """EVALUATE: Commit if tests passed, skip otherwise."""
    if state["errors"] and not state.get("generated_code"):
        return {**state, "commit_result": {"status": "skipped", "reason": "earlier stage failed"}}
    try:
        test_passed = state.get("test_result", {}).get("passed", False)
        if test_passed:
            commit_result = commit_code()
        else:
            commit_result = {
                "status": "skipped",
                "reason": "tests did not pass",
                "test_output": state.get("test_result", {}).get("stdout", "")
            }
        return {**state, "commit_result": commit_result}
    except Exception as e:
        return {**state, "errors": state["errors"] + [f"EVALUATE: {e}"],
                "commit_result": {"status": "error", "reason": str(e)}}


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(PACEState)

    graph.add_node("plan", plan_node)
    graph.add_node("build", build_node)
    graph.add_node("check", check_node)
    graph.add_node("evaluate", evaluate_node)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "build")
    graph.add_edge("build", "check")
    graph.add_edge("check", "evaluate")
    graph.add_edge("evaluate", END)

    return graph.compile()


def run_pace():
    """Run the full PACE workflow using LangGraph."""
    graph = build_graph()

    initial_state: PACEState = {
        "story": {},
        "generated_code": "",
        "test_code": "",
        "test_result": {},
        "commit_result": {},
        "errors": []
    }

    final_state = graph.invoke(initial_state)

    return {
        "plan": f"Story fetched: {final_state['story'].get('title', 'N/A')}",
        "act": f"Code generated ({len(final_state['generated_code'])} chars)",
        "check": final_state["test_result"],
        "evaluate": final_state["commit_result"],
        "errors": final_state["errors"]
    }
