"""
components/strategy_form.py
Strategy input form — five fields across two sections.
Returns strategy_context dict on submission.
"""

import streamlit as st
from schema import BINDING_CONSTRAINTS, PORTFOLIO_SCOPES, STRATEGIC_HORIZONS


def render_strategy_form() -> dict | None:
    """
    Renders the strategy input form.
    Returns strategy_context dict if submitted and valid, else None.
    """
    st.subheader("Strategy Context")
    st.caption(
        "Answer five questions. This takes about 90 seconds. "
        "The quality of these inputs directly determines the quality of the drift analysis."
    )

    with st.form("strategy_form"):
        st.markdown("**Strategy**")

        strategic_bet = st.text_area(
            "What is the most important strategic bet your company is making this quarter?",
            placeholder="e.g. Move upmarket into enterprise healthcare — win our first 3 enterprise customers before Series B.",
            height=80,
            help="Name a directional move, not a revenue target.",
        )

        success_evidence = st.text_area(
            "What evidence would tell you this bet is working?",
            placeholder="e.g. Enterprise prospects entering procurement. Healthcare pilots signed. Compliance conversations initiated by customers.",
            height=80,
            help="Name observable signals — customer behavior, sales conversations, usage patterns — not revenue targets.",
        )

        col1, col2 = st.columns([2, 1])
        with col1:
            deliberate_tradeoff_label = st.text_input(
                "What did you actively decide not to focus on this quarter?",
                placeholder="e.g. SMB self-serve, International expansion",
                help="Name something real — something your team actually debated and decided to deprioritize.",
            )
        with col2:
            deliberate_tradeoff_rationale = st.text_input(
                "Why? (optional)",
                placeholder="e.g. Not enough margin",
            )

        binding_constraint = st.selectbox(
            "What is the single biggest constraint on the company right now?",
            options=["— select —"] + BINDING_CONSTRAINTS,
            help="The thing that, if removed, would change everything else.",
        )

        st.markdown("---")
        st.markdown("**Context**")
        st.caption("These two fields determine how findings are interpreted.")

        col3, col4 = st.columns(2)
        with col3:
            portfolio_scope = st.selectbox(
                "What work is represented in this data?",
                options=PORTFOLIO_SCOPES,
            )
        with col4:
            strategic_horizon = st.selectbox(
                "Over what horizon is this strategy intended to create value?",
                options=STRATEGIC_HORIZONS,
            )

        submitted = st.form_submit_button("Save Strategy Context", type="primary")

    if submitted:
        errors = []
        if not strategic_bet.strip():
            errors.append("Strategic Bet is required.")
        if not success_evidence.strip():
            errors.append("Success Evidence is required.")
        if binding_constraint == "— select —":
            errors.append("Binding Constraint is required.")

        if errors:
            for e in errors:
                st.error(e)
            return None

        return {
            "strategic_bet": strategic_bet.strip(),
            "success_evidence": success_evidence.strip(),
            "deliberate_tradeoff_label": deliberate_tradeoff_label.strip(),
            "deliberate_tradeoff_rationale": deliberate_tradeoff_rationale.strip(),
            "binding_constraint": binding_constraint,
            "portfolio_scope": portfolio_scope,
            "strategic_horizon": strategic_horizon,
        }

    return None


def render_strategy_quality_feedback(strategy_context: dict):
    """
    Inline quality feedback after strategy submission.
    Does not block the run — informs and proceeds.
    """
    warnings = []
    signals = []

    bet = strategy_context.get("strategic_bet", "")
    tradeoff = strategy_context.get("deliberate_tradeoff_label", "")

    # Check for vague bet signals
    vague_terms = ["grow", "improve", "better", "increase", "scale", "build"]
    jargon_terms = ["synergy", "paradigm", "excellence", "optimize", "leverage",
                    "cross-functional", "unlock", "alignment", "transformation",
                    "best-in-class", "world-class", "innovative", "disruptive"]

    if any(t in bet.lower() for t in jargon_terms):
        warnings.append(
            "Your strategic bet contains language that is too general for drift analysis — "
            "words like 'synergy', 'excellence', or 'paradigm' don't give the tool concrete "
            "hooks to map initiatives against. Consider: what specific move are you making, "
            "against which customer, in which market, by when?"
        )
    elif any(t in bet.lower() for t in vague_terms) and len(bet.split()) < 12:
        warnings.append(
            "Your strategic bet is directional but may not name a specific move. "
            "Consider: what would have to be true by end of quarter for this bet to be correct?"
        )
    else:
        signals.append("Strategic bet is specific — drift analysis will be more precise.")

    if not tradeoff:
        warnings.append(
            "No deliberate tradeoff provided. This is the highest-signal field. "
            "If your team hasn't actively decided what not to do, the drift findings will be less actionable."
        )
    else:
        signals.append(f"Deliberate tradeoff named: '{tradeoff}' — enables direct drift checking.")

    if signals:
        for s in signals:
            st.success(f"✓ {s}")
    if warnings:
        for w in warnings:
            st.warning(f"⚠ {w}")
