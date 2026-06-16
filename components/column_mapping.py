"""
components/column_mapping.py
Column mapping and status normalization UI.
"""

import streamlit as st
import pandas as pd
from schema import ALL_SCHEMA_COLUMNS, COLUMN_LABELS, STANDARD_STATUSES, STATUS_DEFAULTS
from preprocessing import suggest_column_mapping


def render_column_mapping(df: pd.DataFrame) -> dict | None:
    """
    Renders column mapping UI. Returns confirmed column_mapping dict or None.
    """
    st.subheader("Map Your Columns")
    st.caption(
        "Match your CSV columns to the standard schema. "
        "Fields marked * are required. Pre-populated based on column names — confirm before proceeding. "
        "Jira: select 'Summary' for title. "
        "Asana: no Status column by default — add a Status custom field before exporting. "
        "Trello: map 'List Name' to Status. "
        "Monday.com: column headers include type in parentheses (e.g. 'Status (Status)') — these map automatically."
    )

    suggestions = suggest_column_mapping(list(df.columns))
    csv_columns = ["— not mapped —"] + list(df.columns)

    mapping = {}
    cols = st.columns(2)
    for i, field in enumerate(ALL_SCHEMA_COLUMNS):
        col = cols[i % 2]
        suggested = suggestions.get(field)
        default_idx = csv_columns.index(suggested) if suggested in csv_columns else 0
        label = COLUMN_LABELS.get(field, field)
        selected = col.selectbox(label, csv_columns, index=default_idx, key=f"map_{field}")
        mapping[field] = selected if selected != "— not mapped —" else None

    return mapping


def render_status_mapping(df: pd.DataFrame, status_col: str) -> dict:
    """
    Renders status normalization UI.
    User maps their status values to standard statuses.
    Returns {raw_status: standard_status}.
    """
    st.subheader("Normalize Status Values")
    st.caption(
        "Map your status values to standard states. "
        "Pre-populated with best-guess defaults — adjust where needed."
    )

    raw_statuses = df[status_col].dropna().unique().tolist()
    status_map = {}

    cols = st.columns(2)
    for i, raw in enumerate(raw_statuses):
        col = cols[i % 2]
        default = STATUS_DEFAULTS.get(str(raw).lower().strip(), "Backlog")
        default_idx = STANDARD_STATUSES.index(default) if default in STANDARD_STATUSES else 0
        selected = col.selectbox(
            f'"{raw}" →',
            STANDARD_STATUSES,
            index=default_idx,
            key=f"status_{raw}",
        )
        status_map[str(raw).lower().strip()] = selected

    return status_map
