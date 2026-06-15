"""
app.py
Initiative Intelligence — Strategy Drift Detection
thomasmeerschwam.com

A continuous audit of whether execution still reflects intent.
"""

import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

from preprocessing import validate_csv, run_pass1
from evidence_mapping import run_pass2
from confidence import compute_classification_confidence, compute_coverage_confidence, build_confidence_summary
from claude_reasoning import run_reasoning
from export import build_export
from components.strategy_form import render_strategy_form, render_strategy_quality_feedback
from components.column_mapping import render_column_mapping, render_status_mapping
from components.output_display import render_full_output

load_dotenv()

st.set_page_config(
    page_title="Initiative Intelligence",
    page_icon="◈",
    layout="wide",
)

# ── Header ──────────────────────────────────────────────────────────────────

st.title("◈ Initiative Intelligence")
st.markdown(
    "**Strategy Drift Detection** — a continuous audit of whether execution still reflects intent."
)
st.markdown(
    "_Every company has a strategy document and a project management system. "
    "Almost none of them have anything that compares the two._"
)
st.markdown("---")

# ── Session state ────────────────────────────────────────────────────────────

for key in ["df", "column_mapping", "status_map", "strategy_context",
            "pass1_output", "pass2_output", "confidence_summary",
            "reasoning_output", "validation_result"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ── Step 1: Upload ───────────────────────────────────────────────────────────

st.header("1 · Upload Initiative Data")
st.caption(
    "Export from Jira (Board → Export Issues), Linear (Settings → Export), "
    "Asana (Export CSV), Notion (Export as CSV), or use any spreadsheet. "
    "Required columns: initiative title, status."
)

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        st.session_state.df = df
        st.success(f"Loaded {len(df)} rows, {len(df.columns)} columns.")
        with st.expander("Preview (first 5 rows)"):
            st.dataframe(df.head())
    except Exception as e:
        st.error(f"Could not read file: {e}")

# ── Step 2: Column mapping ───────────────────────────────────────────────────

if st.session_state.df is not None:
    st.markdown("---")
    st.header("2 · Map Columns")

    column_mapping = render_column_mapping(st.session_state.df)

    if column_mapping and column_mapping.get("title") and column_mapping.get("status"):
        # Validate
        validation = validate_csv(st.session_state.df, column_mapping)
        st.session_state.validation_result = validation

        if not validation["valid"]:
            for e in validation["errors"]:
                st.error(e)
        else:
            for w in validation.get("warnings", []):
                st.warning(w)

            # Status normalization
            status_col = column_mapping["status"]
            st.session_state.status_map = render_status_mapping(
                st.session_state.df, status_col
            )
            st.session_state.column_mapping = column_mapping

            if st.button("Confirm Mapping & Continue", key="confirm_mapping"):
                st.session_state.mapping_confirmed = True

# ── Step 3: Strategy context ─────────────────────────────────────────────────

if st.session_state.get("mapping_confirmed") and st.session_state.column_mapping:
    st.markdown("---")
    st.header("3 · Strategy Context")

    strategy_context = render_strategy_form()

    if strategy_context:
        st.session_state.strategy_context = strategy_context
        render_strategy_quality_feedback(strategy_context)

# ── Step 4: Run analysis ─────────────────────────────────────────────────────

ready = (
    st.session_state.df is not None
    and st.session_state.column_mapping is not None
    and st.session_state.status_map is not None
    and st.session_state.strategy_context is not None
)

if ready:
    st.markdown("---")
    st.header("4 · Run Analysis")

    if st.button("◈ Run Drift Analysis", type="primary", use_container_width=True):
        with st.spinner("Running deterministic preprocessing..."):
            pass1 = run_pass1(
                st.session_state.df,
                st.session_state.column_mapping,
                st.session_state.status_map,
            )
            st.session_state.pass1_output = pass1

        with st.spinner("Running strategic evidence mapping..."):
            pass2 = run_pass2(pass1, st.session_state.strategy_context)
            st.session_state.pass2_output = pass2

        with st.spinner("Computing confidence scores..."):
            class_conf = compute_classification_confidence(pass1)
            cov_conf = compute_coverage_confidence(
                st.session_state.strategy_context.get("portfolio_scope", "Entire company")
            )
            conf_summary = build_confidence_summary(class_conf, cov_conf)
            st.session_state.confidence_summary = conf_summary

        with st.spinner("Generating drift analysis..."):
            reasoning = run_reasoning(
                pass1,
                pass2,
                st.session_state.strategy_context,
                conf_summary,
            )
            st.session_state.reasoning_output = reasoning

        st.success("Analysis complete.")

# ── Step 5: Output ───────────────────────────────────────────────────────────

if st.session_state.reasoning_output:
    st.markdown("---")
    st.header("5 · Drift Analysis")

    render_full_output(
        st.session_state.reasoning_output,
        st.session_state.confidence_summary,
        st.session_state.pass1_output,
        st.session_state.pass2_output,
    )

    # Export
    st.markdown("---")
    export_text = build_export(
        st.session_state.strategy_context,
        st.session_state.confidence_summary,
        st.session_state.reasoning_output,
        st.session_state.pass1_output,
        st.session_state.pass2_output,
    )
    st.download_button(
        label="Download Analysis (.txt)",
        data=export_text,
        file_name="initiative_intelligence_analysis.txt",
        mime="text/plain",
        use_container_width=True,
    )

# ── Footer ───────────────────────────────────────────────────────────────────

st.markdown("---")
st.caption(
    "Initiative Intelligence · [thomasmeerschwam.com](https://thomasmeerschwam.com) · "
    "Part of the Ground Truth Decisioning System"
)
