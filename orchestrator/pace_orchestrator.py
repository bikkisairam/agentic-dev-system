"""
PACE Orchestrator — LangGraph graph: PRIME → FORGE → [GATE + SENTINEL + CONDUIT] → SCRIBE

The three quality agents run concurrently inside a single LangGraph node
via ThreadPoolExecutor, then all results are merged before SCRIBE runs.

Legacy run_pace() / stream_pace() without ticket_id kept for backward compatibility.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Annotated, Any
import operator

from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

from agents.prime_agent import run_prime
from agents.forge_agent import run_forge
from agents.gate_agent import run_gate
from agents.sentinel_agent import run_sentinel
from agents.conduit_agent import run_conduit
from agents.scribe_agent import run_scribe


# ── State ─────────────────────────────────────────────────────────────────────

class PACEState(TypedDict):
    ticket_id: str
    story_card: dict
    story_card_path: str
    branch_name: str
    forge_result: dict
    ac_results: list[dict]
    gate_result: dict
    sentinel_result: dict
    conduit_result: dict
    scribe_result: dict
    pipeline_decision: str
    errors: Annotated[list[str], operator.add]


INITIAL_STATE: PACEState = {
    "ticket_id": "",
    "story_card": {},
    "story_card_path": "",
    "branch_name": "",
    "forge_result": {},
    "ac_results": [],
    "gate_result": {},
    "sentinel_result": {},
    "conduit_result": {},
    "scribe_result": {},
    "pipeline_decision": "",
    "errors": [],
}


# ── Parallel quality node ─────────────────────────────────────────────────────

def _parallel_node(state: PACEState) -> PACEState:
    """Run GATE, SENTINEL, CONDUIT concurrently; merge results into state."""
    gate_result = {}
    sentinel_result = {}
    conduit_result = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(run_gate, state):     "gate",
            executor.submit(run_sentinel, state): "sentinel",
            executor.submit(run_conduit, state):  "conduit",
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                result_state = future.result()
                if name == "gate":
                    gate_result = result_state.get("gate_result", _error_result("gate", "no result"))
                elif name == "sentinel":
                    sentinel_result = result_state.get("sentinel_result", _error_result("sentinel", "no result"))
                elif name == "conduit":
                    conduit_result = result_state.get("conduit_result", _error_result("conduit", "no result"))
            except Exception as e:
                if name == "gate":
                    gate_result = _error_result("gate", str(e))
                elif name == "sentinel":
                    sentinel_result = _error_result("sentinel", str(e))
                elif name == "conduit":
                    conduit_result = _error_result("conduit", str(e))

    return {
        **state,
        "gate_result": gate_result,
        "sentinel_result": sentinel_result,
        "conduit_result": conduit_result,
    }


def _error_result(name: str, reason: str) -> dict:
    if name == "gate":
        return {"decision": "HOLD", "ac_verdicts": [], "total": 0,
                "passed": 0, "failed": 0, "error": reason}
    if name == "sentinel":
        return {"decision": "ADVISORY", "findings": [],
                "summary": f"Agent error: {reason}"}
    return {"decision": "ADVISORY", "checks": [],
            "summary": f"Agent error: {reason}"}


# ── Graph construction ────────────────────────────────────────────────────────

def build_pace_graph():
    graph = StateGraph(PACEState)
    graph.add_node("prime",    run_prime)
    graph.add_node("forge",    run_forge)
    graph.add_node("parallel", _parallel_node)
    graph.add_node("scribe",   run_scribe)
    graph.set_entry_point("prime")
    graph.add_edge("prime",    "forge")
    graph.add_edge("forge",    "parallel")
    graph.add_edge("parallel", "scribe")
    graph.add_edge("scribe",   END)
    return graph.compile()


# ── Public API ────────────────────────────────────────────────────────────────

def run_pace(ticket_id: str = "") -> dict:
    """Blocking execution. Returns a summary dict."""
    graph = build_pace_graph()
    final = graph.invoke({**INITIAL_STATE, "ticket_id": ticket_id})
    return _summarize(final)


def stream_pace(ticket_id: str = ""):
    """
    Generator yielding SSE event dicts as each node completes.
    The 'parallel' node emits three events: gate, sentinel, conduit.
    """
    graph = build_pace_graph()
    for chunk in graph.stream({**INITIAL_STATE, "ticket_id": ticket_id}):
        node_name = list(chunk.keys())[0]
        node_state = chunk[node_name]
        yield from _emit_events(node_name, node_state)


# ── SSE helpers ───────────────────────────────────────────────────────────────

def _emit_events(node_name: str, state: dict):
    errors = state.get("errors", [])
    if node_name == "prime":
        yield _event("prime", state.get("story_card"), errors)
    elif node_name == "forge":
        yield _event("forge", state.get("forge_result"), errors)
    elif node_name == "parallel":
        yield _event("gate",     state.get("gate_result"),     errors)
        yield _event("sentinel", state.get("sentinel_result"), errors)
        yield _event("conduit",  state.get("conduit_result"),  errors)
    elif node_name == "scribe":
        yield _event("scribe", state.get("scribe_result"), errors)


def _event(stage: str, output: Any, errors: list) -> dict:
    return {
        "stage":  stage,
        "status": "error" if errors else "success",
        "output": output or {},
        "errors": errors,
    }


def _summarize(state: dict) -> dict:
    return {
        "ticket_id":         state.get("ticket_id"),
        "pipeline_decision": state.get("scribe_result", {}).get("final_decision", "UNKNOWN"),
        "branch_name":       state.get("branch_name"),
        "gate":              state.get("gate_result", {}).get("decision"),
        "sentinel":          state.get("sentinel_result", {}).get("decision"),
        "conduit":           state.get("conduit_result", {}).get("decision"),
        "ac_results":        state.get("ac_results", []),
        "errors":            state.get("errors", []),
        "engineering_md":    state.get("scribe_result", {}).get("engineering_md_path"),
    }
