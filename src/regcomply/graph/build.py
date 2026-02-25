from langgraph.graph import END, StateGraph

from regcomply.agents import change_detection, policy_rag, recommendations
from regcomply.graph.state import PipelineState

_compiled = None


def build_graph():
    global _compiled
    if _compiled is not None:
        return _compiled
    g = StateGraph(PipelineState)
    g.add_node("change_detection", change_detection.run)
    g.add_node("policy_rag", policy_rag.run)
    g.add_node("recommendations", recommendations.run)
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
