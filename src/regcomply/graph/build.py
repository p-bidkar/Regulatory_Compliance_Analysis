import time
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, StateGraph

from regcomply.agents import change_detection, policy_rag, recommendations
from regcomply.graph.state import PipelineState

_compiled = None


def _with_timing(name: str, fn: Callable[[PipelineState], dict[str, Any]]):
    def wrapper(state: PipelineState) -> dict[str, Any]:
        started = time.perf_counter()
        out = dict(fn(state))
        elapsed = round(time.perf_counter() - started, 3)
        timings = dict(state.get("timings") or {})
        timings.update(out.get("timings") or {})
        timings[name] = elapsed
        out["timings"] = timings
        return out

    return wrapper


def build_graph():
    global _compiled
    if _compiled is not None:
        return _compiled
    g = StateGraph(PipelineState)
    g.add_node("change_detection", _with_timing("change_detection", change_detection.run))
    g.add_node("policy_rag", _with_timing("policy_rag", policy_rag.run))
    g.add_node("recommendations", _with_timing("recommendations", recommendations.run))
    g.set_entry_point("change_detection")
    g.add_edge("change_detection", "policy_rag")
    g.add_edge("policy_rag", "recommendations")
    g.add_edge("recommendations", END)
    _compiled = g.compile()
    return _compiled


def run_pipeline(state: PipelineState) -> PipelineState:
    app = build_graph()
    out = app.invoke(state)
    return out  # type: ignore[return-value]
