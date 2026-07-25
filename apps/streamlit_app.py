from pathlib import Path

import streamlit as st

from regcomply import __version__
from regcomply.graph import run_pipeline
from regcomply.graph.state import PipelineState

REG_DIR = Path(__file__).parent.parent / "data" / "raw" / "regulations"

st.set_page_config(page_title="regcomply", layout="wide")
st.title("regcomply")
st.caption(
    f"v{__version__} | Multi-agent regulatory compliance analysis | "
    "Drafts for human review only — not legal advice"
)

with st.sidebar:
    st.header("Configuration")
    baseline_file = st.selectbox(
        "Baseline regulation",
        sorted(REG_DIR.glob("*_baseline.txt")),
        format_func=lambda p: p.name,
    )
    updated_file = st.selectbox(
        "Updated regulation",
        sorted(REG_DIR.glob("*_updated.txt")),
        format_func=lambda p: p.name,
    )
    run_btn = st.button("Run analysis", type="primary", use_container_width=True)

if run_btn:
    if not baseline_file or not updated_file:
        st.error("Select both a baseline and updated regulation file.")
        st.stop()

    baseline_text = Path(baseline_file).read_text(encoding="utf-8")
    updated_text = Path(updated_file).read_text(encoding="utf-8")

    regulation_id = Path(baseline_file).stem.replace("_baseline", "")

    init: PipelineState = {
        "regulation_id": regulation_id,
        "baseline_text": baseline_text,
        "updated_text": updated_text,
    }

    with st.spinner("Running pipeline (change detection -> policy RAG -> recommendations)..."):
        result = run_pipeline(init)

    change_items = result.get("change_items", [])
    retrieved_chunks = result.get("retrieved_chunks", [])
    recommendations = result.get("draft_recommendations", [])
    citations = result.get("citations", [])

    st.subheader(f"Results for: {regulation_id}")

    tab1, tab2, tab3, tab4 = st.tabs([
        f"Changes detected ({len(change_items)})",
        f"Policy chunks retrieved ({len(retrieved_chunks)})",
        f"Recommendations ({len(recommendations)})",
        "Citations & raw output",
    ])

    with tab1:
        if not change_items:
            st.info("No substantive changes detected.")
        for item in change_items:
            impact = item.get("compliance_impact", "")
            color = {"high": "red", "medium": "orange", "low": "green"}.get(impact, "gray")
            st.markdown(
                f"**{item.get('section', 'N/A')}** &nbsp;"
                f":{color}[{impact.upper()}] &nbsp; `{item.get('change_type', '')}`"
            )
            st.write(item.get("summary", ""))
            with st.expander("Details"):
                col1, col2 = st.columns(2)
                with col1:
                    st.caption("Baseline text")
                    st.text(item.get("baseline_text", "(new)"))
                with col2:
                    st.caption("Updated text")
                    st.text(item.get("updated_text", "(deleted)"))
            st.divider()

    with tab2:
        if not retrieved_chunks:
            st.info("No policy chunks retrieved. Run scripts/build_index.py first.")
        for chunk in retrieved_chunks:
            st.markdown(
                f"**{chunk.get('source_doc_id', '')}** | "
                f"`{chunk.get('section_path', '')}` | "
                f"score: `{chunk.get('score', '')}`"
            )
            st.text(chunk.get("text", "")[:400] + "...")
            st.divider()

    with tab3:
        if not recommendations:
            st.info("No recommendations generated.")
        for rec in recommendations:
            priority = rec.get("priority", "")
            color = {"critical": "red", "high": "red", "medium": "orange", "low": "green"}.get(
                priority, "gray"
            )
            st.markdown(
                f"**{rec.get('recommendation_id', '')}** &nbsp;"
                f":{color}[{priority.upper()}] &nbsp; "
                f"Policy: `{rec.get('policy_doc', '')}`"
            )
            st.markdown(f"*Regulatory change:* {rec.get('regulatory_change_ref', '')}")
            st.markdown(f"**Rationale:** {rec.get('rationale', '')}")
            with st.expander("Current vs recommended policy language"):
                col1, col2 = st.columns(2)
                with col1:
                    st.caption("Current policy text")
                    st.text(rec.get("current_policy_text", ""))
                with col2:
                    st.caption("Recommended update")
                    st.write(rec.get("recommended_update", ""))
            st.divider()

    with tab4:
        st.subheader("Citation verification")
        if citations:
            for cit in citations:
                verified = cit.get("verified", False)
                status = "verified" if verified else "unverified"
                color = "green" if verified else "red"
                st.markdown(
                    f":{color}[{status.upper()}] "
                    f"{cit.get('recommendation_id', '')} -> "
                    f"`{cit.get('chunk_id', '')}` "
                    f"({cit.get('source_doc_id', '')})"
                )
        timings = result.get("timings") or {}
        if timings:
            st.subheader("Stage timings (seconds)")
            st.json(timings)
        st.subheader("Raw pipeline output")
        st.json(result)
