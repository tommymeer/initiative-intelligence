"""
components/output_display.py
Renders the analysis output sections in Streamlit.
"""

import streamlit as st


SEVERITY_COLORS = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
CONFIDENCE_COLORS = {"High": "🟢", "Medium": "🟡", "Low": "🔴",
                     "Complete": "🟢", "Partial": "🟡", "Limited": "🔴"}


def render_confidence_header(confidence_summary: dict):
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        level = confidence_summary["classification"]["level"]
        icon = CONFIDENCE_COLORS.get(level, "⚪")
        st.metric("Classification Confidence", f"{icon} {level}")
        st.caption(confidence_summary["classification"]["explanation"])
    with col2:
        level = confidence_summary["coverage"]["level"]
        icon = CONFIDENCE_COLORS.get(level, "⚪")
        st.metric("Portfolio Coverage", f"{icon} {level}")
        st.caption(confidence_summary["coverage"]["explanation"])

    note = confidence_summary.get("combined_note", "")
    if note:
        st.info(note)
    st.markdown("---")


def render_allocation_bar(pass2_output: dict):
    st.markdown("**Active Initiative Allocation**")
    bucket_pct = pass2_output.get("bucket_pct", {})
    bucket_counts = pass2_output.get("bucket_counts", {})
    active_count = pass2_output.get("active_count", 0)

    cols = st.columns(4)
    bucket_icons = {
        "Supports strategic bet": "🎯",
        "Supports binding constraint": "🔗",
        "Related to deprioritized area": "⚠️",
        "No clear strategic connection": "❓",
    }
    for i, (bucket, pct) in enumerate(bucket_pct.items()):
        count = bucket_counts.get(bucket, 0)
        icon = bucket_icons.get(bucket, "")
        cols[i].metric(
            f"{icon} {bucket.split('(')[0].strip()}",
            f"{count} ({pct}%)",
            help=f"{count} of {active_count} active initiatives"
        )
    st.markdown("---")


def render_portfolio_snapshot(reasoning_output: dict):
    snapshot = reasoning_output.get("portfolio_snapshot")
    if not snapshot:
        return
    st.subheader("Portfolio Snapshot")
    st.write(snapshot.get("narrative", ""))


def render_strategic_alignment(reasoning_output: dict):
    alignment = reasoning_output.get("strategic_alignment")
    if not alignment or not alignment.get("findings"):
        return
    st.subheader("Strategic Alignment")
    for f in alignment["findings"]:
        prereq = f.get("is_prerequisite_work", False)
        label = "Prerequisite work" if prereq else "Direct alignment"
        with st.expander(f"✓ {f['observation'][:80]}...", expanded=True):
            st.write(f['observation'])
            st.caption(f"Evidence: {f['evidence']}")
            st.caption(f"Type: {label}")


def render_drift_findings(reasoning_output: dict):
    drift = reasoning_output.get("drift_findings")
    if not drift or not drift.get("findings"):
        st.subheader("Drift Findings")
        st.success("No significant drift detected.")
        return
    st.subheader("Drift Findings")
    for f in drift["findings"]:
        severity = f.get("severity", "Medium")
        icon = SEVERITY_COLORS.get(severity, "⚪")
        with st.expander(f"{icon} [{severity}] {f['finding'][:80]}...", expanded=True):
            st.write(f["finding"])
            st.caption(f"Evidence: {f['evidence']}")


def render_hidden_contradictions(reasoning_output: dict):
    contradictions = reasoning_output.get("hidden_contradictions")
    if not contradictions or not contradictions.get("contradictions"):
        return
    st.subheader("Hidden Contradictions")
    for c in contradictions["contradictions"]:
        with st.expander(f"◈ {c['observation'][:80]}...", expanded=True):
            st.write(c["observation"])
            st.caption(f"Implication: {c['implication']}")


def render_leadership_questions(reasoning_output: dict):
    questions = reasoning_output.get("leadership_questions")
    if not questions or not questions.get("questions"):
        return
    st.subheader("Questions Leadership Should Ask")
    for i, q in enumerate(questions["questions"], 1):
        st.markdown(f"**{i}. {q['question']}**")
        st.caption(q["rationale"])
        st.markdown("")


def render_confidence_caveats(reasoning_output: dict):
    caveats = reasoning_output.get("confidence_caveats")
    if not caveats or not caveats.get("caveats"):
        return
    st.subheader("Confidence Caveats")
    for c in caveats["caveats"]:
        st.warning(f"**{c['caveat']}**\n\nAffects: {c['affected_findings']}")


def render_full_output(reasoning_output: dict, confidence_summary: dict,
                       pass1_output: dict, pass2_output: dict):
    render_confidence_header(confidence_summary)
    render_allocation_bar(pass2_output)
    render_portfolio_snapshot(reasoning_output)
    render_strategic_alignment(reasoning_output)
    render_drift_findings(reasoning_output)
    render_hidden_contradictions(reasoning_output)
    render_leadership_questions(reasoning_output)
    render_confidence_caveats(reasoning_output)
