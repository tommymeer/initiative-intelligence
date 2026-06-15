"""
export.py
Generates the .txt export artifact.
"""

from datetime import datetime


def build_export(
    strategy_context: dict,
    confidence_summary: dict,
    reasoning_output: dict,
    pass1_output: dict,
    pass2_output: dict,
) -> str:
    lines = []

    lines.append("INITIATIVE INTELLIGENCE — STRATEGY DRIFT ANALYSIS")
    lines.append(f"Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}")
    lines.append("=" * 60)

    lines.append("\nSTRATEGY CONTEXT")
    lines.append(f"Strategic Bet: {strategy_context.get('strategic_bet', '—')}")
    lines.append(f"Success Evidence: {strategy_context.get('success_evidence', '—')}")
    lines.append(f"Deliberate Tradeoff: {strategy_context.get('deliberate_tradeoff_label', '—')}")
    lines.append(f"Binding Constraint: {strategy_context.get('binding_constraint', '—')}")
    lines.append(f"Portfolio Scope: {strategy_context.get('portfolio_scope', '—')}")
    lines.append(f"Strategic Horizon: {strategy_context.get('strategic_horizon', '—')}")

    lines.append("\n" + "=" * 60)
    lines.append("CONFIDENCE")
    lines.append(f"Classification: {confidence_summary['classification']['level']}")
    lines.append(confidence_summary['classification']['explanation'])
    lines.append(f"Coverage: {confidence_summary['coverage']['level']}")
    lines.append(confidence_summary['coverage']['explanation'])

    lines.append("\n" + "=" * 60)
    lines.append("PORTFOLIO SNAPSHOT")
    snapshot = reasoning_output.get("portfolio_snapshot")
    if snapshot:
        lines.append(snapshot.get("narrative", ""))

    lines.append("\n" + "=" * 60)
    lines.append("STRATEGIC ALIGNMENT")
    alignment = reasoning_output.get("strategic_alignment")
    if alignment and alignment.get("findings"):
        for f in alignment["findings"]:
            prefix = "[PREREQUISITE] " if f.get("is_prerequisite_work") else ""
            lines.append(f"• {prefix}{f['observation']}")
            lines.append(f"  Evidence: {f['evidence']}")
    else:
        lines.append("No clear alignment signals identified.")

    lines.append("\n" + "=" * 60)
    lines.append("DRIFT FINDINGS")
    drift = reasoning_output.get("drift_findings")
    if drift and drift.get("findings"):
        for f in drift["findings"]:
            lines.append(f"[{f['severity']}] {f['finding']}")
            lines.append(f"  Evidence: {f['evidence']}")
    else:
        lines.append("No significant drift detected.")

    lines.append("\n" + "=" * 60)
    lines.append("HIDDEN CONTRADICTIONS")
    contradictions = reasoning_output.get("hidden_contradictions")
    if contradictions and contradictions.get("contradictions"):
        for c in contradictions["contradictions"]:
            lines.append(f"• {c['observation']}")
            lines.append(f"  Implication: {c['implication']}")
    else:
        lines.append("No hidden contradictions identified.")

    lines.append("\n" + "=" * 60)
    lines.append("QUESTIONS LEADERSHIP SHOULD ASK")
    questions = reasoning_output.get("leadership_questions")
    if questions and questions.get("questions"):
        for i, q in enumerate(questions["questions"], 1):
            lines.append(f"{i}. {q['question']}")
            lines.append(f"   Why this matters: {q['rationale']}")
    else:
        lines.append("No questions generated.")

    caveats = reasoning_output.get("confidence_caveats")
    if caveats and caveats.get("caveats"):
        lines.append("\n" + "=" * 60)
        lines.append("CONFIDENCE CAVEATS")
        for c in caveats["caveats"]:
            lines.append(f"• {c['caveat']}")
            lines.append(f"  Affects: {c['affected_findings']}")

    lines.append("\n" + "=" * 60)
    lines.append("PORTFOLIO ALLOCATION SUMMARY (Active Initiatives)")
    lines.append(f"Total active: {pass2_output['active_count']}")
    for bucket, pct in pass2_output['bucket_pct'].items():
        count = pass2_output['bucket_counts'].get(bucket, 0)
        lines.append(f"  {bucket}: {count} ({pct}%)")

    lines.append("\n" + "=" * 60)
    lines.append("Initiative Intelligence · thomasmeerschwam.com")

    return "\n".join(lines)
