"""
confidence.py
Confidence scoring — deterministic, no Claude.

Two independent dimensions:
1. Classification Confidence — quality of initiative metadata
2. Portfolio Coverage Confidence — completeness of the uploaded data
"""


def compute_classification_confidence(pass1_output: dict) -> dict:
    pct = pass1_output.get("pct_with_context", 0)
    unclear_count = pass1_output.get("unclear_count", 0)
    total = pass1_output.get("total_count", 1)
    unclear_pct = round(unclear_count / total * 100, 1) if total > 0 else 0

    level = pass1_output.get("classification_confidence", "Low")

    if level == "High":
        explanation = (
            f"{pct}% of initiatives had descriptions or labels sufficient for reliable "
            "classification. Findings should be treated as reliable."
        )
    elif level == "Medium":
        explanation = (
            f"{pct}% of initiatives had descriptions or labels. "
            f"{unclear_pct}% could not be confidently classified. "
            "Findings are directionally reliable; one or two categories may be misclassified."
        )
    else:
        explanation = (
            f"Only {pct}% of initiatives had descriptions or labels. "
            f"{unclear_pct}% could not be classified from title alone. "
            "Treat findings as hypotheses, not conclusions. "
            "Consider adding initiative descriptions and re-running."
        )

    return {
        "level": level,
        "pct_with_context": pct,
        "unclear_pct": unclear_pct,
        "explanation": explanation,
    }


def compute_coverage_confidence(portfolio_scope: str) -> dict:
    scope_lower = portfolio_scope.lower()

    if "entire company" in scope_lower:
        level = "Complete"
        explanation = (
            "Uploaded data represents the entire company's active work. "
            "Alignment findings reflect the full organizational portfolio."
        )
        caveat = None
    elif "other" in scope_lower or "partial" in scope_lower:
        level = "Limited"
        explanation = (
            f"Uploaded data represents a partial view of organizational work ({portfolio_scope}). "
            "Significant initiative activity may not be visible. "
            "Alignment findings should be treated as directional only."
        )
        caveat = (
            f"Portfolio Coverage: Limited. Uploaded data represents {portfolio_scope}. "
            "Alignment findings may significantly understate or misrepresent "
            "total organizational activity."
        )
    else:
        level = "Partial"
        explanation = (
            f"Uploaded data represents {portfolio_scope} only. "
            "Work happening in other functions is not visible. "
            "Alignment findings reflect this function's activity only."
        )
        caveat = (
            f"Portfolio Coverage: Partial. Uploaded data represents {portfolio_scope} only. "
            "Work in other functions is not included. "
            "Findings may understate or overstate strategic alignment "
            "depending on where the strategic bet is being executed."
        )

    return {
        "level": level,
        "scope": portfolio_scope,
        "explanation": explanation,
        "caveat": caveat,
    }


def build_confidence_summary(
    classification_confidence: dict,
    coverage_confidence: dict,
) -> dict:
    return {
        "classification": classification_confidence,
        "coverage": coverage_confidence,
        "combined_note": _combined_note(
            classification_confidence["level"],
            coverage_confidence["level"]
        ),
    }


def _combined_note(classification_level: str, coverage_level: str) -> str:
    if classification_level == "High" and coverage_level == "Complete":
        return "Confidence is high. Findings are based on complete, well-described portfolio data."
    elif classification_level == "Low" or coverage_level == "Limited":
        return (
            "Confidence limitations are significant. "
            "Treat findings as directional hypotheses rather than reliable conclusions. "
            "See confidence details above each section."
        )
    else:
        return (
            "Confidence is moderate. "
            "Key findings are directionally reliable but should be validated "
            "against the team's knowledge of actual work distribution."
        )
