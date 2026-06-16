"""
claude_reasoning.py
Judgment layer — Claude Sonnet via structured tool use.

Claude receives structured pass1 + pass2 metrics, never raw CSV.
Six tools map to six output sections.
Prompt calibrated to strategic horizon and confidence levels.
"""

import json
import anthropic

TOOLS = [
    {
        "name": "write_portfolio_snapshot",
        "description": (
            "Write a brief plain-language summary of what the portfolio contains. "
            "Cover: total initiatives, active count, category shape, notable concentrations, "
            "owner load if available. 2-4 sentences. No recommendations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "narrative": {"type": "string"},
            },
            "required": ["narrative"],
        },
    },
    {
        "name": "identify_strategic_alignment",
        "description": (
            "Identify where the portfolio visibly supports the stated strategic bet. "
            "Include non-obvious prerequisite work — infrastructure or compliance "
            "that enables the bet even if not directly labeled as such. "
            "Be specific: name initiative categories or patterns."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "observation": {"type": "string"},
                            "evidence": {"type": "string"},
                            "is_prerequisite_work": {"type": "boolean"},
                        },
                        "required": ["observation", "evidence", "is_prerequisite_work"],
                    },
                },
            },
            "required": ["findings"],
        },
    },
    {
        "name": "identify_drift_findings",
        "description": (
            "Identify specific discrepancies between stated strategic intent and observed execution. "
            "Each finding must be quantified using the metrics provided. "
            "Calibrate urgency to the strategic horizon: "
            "short horizon (this quarter) → urgent, present-tense framing; "
            "long horizon (12+ months) → interrogative framing ('is this prerequisite work or avoidance?'). "
            "Name the gap. Do not soften it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "finding": {"type": "string"},
                            "evidence": {"type": "string"},
                            "severity": {"type": "string", "enum": ["High", "Medium", "Low"]},
                        },
                        "required": ["finding", "evidence", "severity"],
                    },
                },
            },
            "required": ["findings"],
        },
    },
    {
        "name": "surface_hidden_contradictions",
        "description": (
            "Surface patterns in the portfolio that contradict the strategic context "
            "in non-obvious ways. This is the absence detection pass: "
            "reason about what the stated strategy implies should exist in the portfolio "
            "but does not appear. Name specifically what is missing and why it matters. "
            "Also surface cases where the portfolio contains work that "
            "contradicts multiple stated priorities simultaneously."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "contradictions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "observation": {"type": "string"},
                            "implication": {"type": "string"},
                        },
                        "required": ["observation", "implication"],
                    },
                },
            },
            "required": ["contradictions"],
        },
    },
    {
        "name": "generate_leadership_questions",
        "description": (
            "Generate 3-5 questions the drift findings suggest leadership should discuss. "
            "These are not recommendations or actions. They are questions that force "
            "the strategic conversation the data implies is needed. "
            "Each question should be specific to the findings, not generic."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "rationale": {"type": "string"},
                        },
                        "required": ["question", "rationale"],
                    },
                },
            },
            "required": ["questions"],
        },
    },
    {
        "name": "flag_confidence_caveats",
        "description": (
            "Flag any cases where confidence limitations affect specific findings. "
            "Link classification or coverage caveats to the findings they qualify. "
            "Only call this if there are meaningful caveats to surface — "
            "do not generate generic disclaimers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "caveats": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "caveat": {"type": "string"},
                            "affected_findings": {"type": "string"},
                        },
                        "required": ["caveat", "affected_findings"],
                    },
                },
            },
            "required": ["caveats"],
        },
    },
]


def build_system_prompt(strategy_context: dict, confidence_summary: dict) -> str:
    horizon = strategy_context.get("strategic_horizon", "This quarter (< 3 months)")
    is_short_horizon = "quarter" in horizon.lower() or "3 month" in horizon.lower()

    horizon_instruction = (
        "The strategic horizon is SHORT (this quarter). "
        "Frame drift findings as urgent and present-tense. "
        "Misalignment now has direct consequences this quarter."
        if is_short_horizon else
        "The strategic horizon is LONGER than one quarter. "
        "Frame drift findings as interrogative where appropriate: "
        "'Is this prerequisite work or drift?' rather than assuming misalignment. "
        "Some apparent drift may be correct sequencing."
    )

    classification_level = confidence_summary["classification"]["level"]
    coverage_level = confidence_summary["coverage"]["level"]

    confidence_instruction = ""
    if classification_level == "Low":
        confidence_instruction += (
            "\nClassification confidence is LOW. "
            "Many initiatives lacked descriptions. "
            "Acknowledge uncertainty in findings where classification was likely unreliable. "
            "Do not produce false precision."
        )
    if coverage_level in ("Partial", "Limited"):
        scope = confidence_summary["coverage"]["scope"]
        confidence_instruction += (
            f"\nPortfolio coverage is {coverage_level} ({scope} only). "
            "Explicitly note when a finding may be affected by incomplete portfolio visibility. "
            "Do not conclude that absent work doesn't exist — it may simply not be in the upload."
        )

    return f"""You are an organizational diagnostician reviewing an initiative portfolio against stated strategic intent.

Your job is to surface what the data reveals — not to recommend, prescribe, or tell leadership what to do.

CORE PRINCIPLES:
- Observation over recommendation. Name the gap. Do not tell them how to close it.
- Quantification over characterization. Use the numbers provided. "4 of 14 active initiatives (28.6%)" is trustworthy. "Some initiatives" is not.
- Absence detection is a first-class task. Reason about what the stated strategy implies should be visible but is not. This is often the most important finding.
- Uncomfortable specificity. The goal is for the reader to think "damn, that's actually right." Vague findings fail this test.
- Reason only from available evidence. Do not infer intent from titles alone when descriptions are absent. Say what the data shows, not what you imagine.

REQUIRED DRIFT CHECKS — you must evaluate all three, every run:

1. DEPRIORITIZED AREA DRIFT: If "Related to deprioritized area" bucket has ANY non-zero count, this is a required drift finding. Do not ignore it. Name the count, the percentage, and what it means that active work is flowing into an area leadership explicitly decided to stop. This is the clearest drift signal in the system.

2. ABSENCE DETECTION: Look at "Expected categories not present in active portfolio" in the data. If anything is listed there, surface it as a hidden contradiction. A strategy implies certain work must exist. If that work is absent, name it explicitly: "The stated strategy implies X should be visible in the portfolio. It is not."

3. BLOCKED BET INITIATIVES: If any initiatives supporting the strategic bet are blocked, this is an urgent finding. Name the specific initiative, name it as blocked, and surface the implication: work that directly supports the strategic bet is not moving.

HORIZON CALIBRATION:
{horizon_instruction}

CONFIDENCE:
{confidence_instruction}

When you call tools, use the metrics provided in the user message. Do not invent numbers. If a metric is not provided, work with what is available and note the limitation."""


def build_user_message(pass1_output: dict, pass2_output: dict,
                       strategy_context: dict, confidence_summary: dict) -> str:
    """
    Build the structured message Claude receives.
    Clean metrics only — no raw CSV data.
    """
    return f"""STRATEGY CONTEXT
Strategic Bet: {strategy_context.get('strategic_bet', 'Not provided')}
Success Evidence: {strategy_context.get('success_evidence', 'Not provided')}
Deliberate Tradeoff: {strategy_context.get('deliberate_tradeoff_label', 'Not provided')}
Binding Constraint: {strategy_context.get('binding_constraint', 'Not provided')}
Portfolio Scope: {strategy_context.get('portfolio_scope', 'Not provided')}
Strategic Horizon: {strategy_context.get('strategic_horizon', 'Not provided')}

PORTFOLIO METRICS (Pass 1)
Total initiatives: {pass1_output['total_count']}
Active: {pass1_output['active_count']} | Blocked: {pass1_output['blocked_count']} | Complete: {pass1_output['complete_count']} | Backlog: {pass1_output['backlog_count']}

Category distribution (active initiatives):
{json.dumps(pass1_output['active_category_pct'], indent=2)}

Owner load (top owners):
{json.dumps(pass1_output['owner_distribution'], indent=2) if pass1_output['owner_distribution'] else 'Owner data not available'}

Initiatives with no recent activity (30+ days): {pass1_output['stale_count']}
Initiatives with insufficient context for classification: {pass1_output['unclear_count']} ({100 - pass1_output['pct_with_context']:.1f}%)

STRATEGIC EVIDENCE MAPPING (Pass 2)
Active initiative allocation by strategic bucket:
{json.dumps(pass2_output['bucket_pct'], indent=2)}

Counts:
{json.dumps(pass2_output['bucket_counts'], indent=2)}

Blocked initiatives supporting the strategic bet (priority intervention signals):
{pass2_output['blocked_bet_count']} initiatives: {', '.join(pass2_output['blocked_bet_initiatives']) or 'None'}

Expected categories not present in active portfolio:
{json.dumps(pass2_output['expected_but_absent'], indent=2) if pass2_output['expected_but_absent'] else 'None flagged'}

CONFIDENCE SUMMARY
Classification Confidence: {confidence_summary['classification']['level']}
{confidence_summary['classification']['explanation']}

Portfolio Coverage: {confidence_summary['coverage']['level']}
{confidence_summary['coverage']['explanation']}

---
PRE-COMPUTED DRIFT SIGNALS — these are facts, not suggestions. Every non-empty signal below MUST appear as a finding in the appropriate tool call. Do not omit, soften, or merge them into alignment findings.

SIGNAL 1 — DEPRIORITIZED AREA ALLOCATION:
{f'⚠ DRIFT DETECTED: {pass2_output["bucket_counts"]["Related to deprioritized area"]} of {pass2_output["active_count"]} active initiatives ({pass2_output["bucket_pct"]["Related to deprioritized area"]}%) are classified as related to "{strategy_context.get("deliberate_tradeoff_label", "the deprioritized area")}" — the area leadership explicitly decided not to focus on this quarter. This must appear as a drift finding.' if pass2_output["bucket_counts"]["Related to deprioritized area"] > 0 else "✓ No active initiatives mapped to deprioritized area."}

SIGNAL 2 — BLOCKED BET INITIATIVES:
{f'⚠ URGENT: {pass2_output["blocked_bet_count"]} initiative(s) directly supporting the strategic bet are currently BLOCKED: {", ".join(pass2_output["blocked_bet_initiatives"])}. Work that directly enables the strategic bet is not moving. This must appear as a High severity drift finding.' if pass2_output["blocked_bet_count"] > 0 else "✓ No blocked initiatives supporting the strategic bet."}

SIGNAL 3 — EXPECTED BUT ABSENT:
{chr(10).join([f"⚠ ABSENCE: {item} — this must appear as a hidden contradiction." for item in pass2_output["expected_but_absent"]]) if pass2_output["expected_but_absent"] else "✓ No expected categories absent."}

---
Now call all six tools. Use the pre-computed signals above as required inputs to drift_findings, hidden_contradictions, and leadership_questions. Do not produce empty sections for any signal marked ⚠."""


def build_deterministic_questions(pass2_output: dict, strategy_context: dict) -> dict:
    """
    Generate leadership questions deterministically from confirmed signals.
    Questions are specific to the findings — not generic strategy questions.
    """
    questions = []
    tradeoff = strategy_context.get("deliberate_tradeoff_label", "the deprioritized area")
    deprioritized_count = pass2_output["bucket_counts"]["Related to deprioritized area"]
    deprioritized_pct = pass2_output["bucket_pct"]["Related to deprioritized area"]
    active_count = pass2_output["active_count"]

    if deprioritized_count > 0:
        questions.append({
            "question": (
                f"{deprioritized_count} of {active_count} active initiatives ({deprioritized_pct}%) "
                f"are related to '{tradeoff}' — the area we said we weren't focusing on. "
                f"Do we have an explicit plan to wind these down, or have we not actually made the tradeoff?"
            ),
            "rationale": (
                f"Stated tradeoffs that don't show up in the portfolio are not tradeoffs — "
                f"they're intentions. {deprioritized_pct}% allocation to a deprioritized area "
                f"suggests the decision either wasn't communicated or wasn't accepted."
            ),
        })

    if pass2_output["blocked_bet_count"] > 0:
        names = ", ".join(pass2_output["blocked_bet_initiatives"])
        questions.append({
            "question": (
                f"The {names} initiative is blocked. "
                f"This is the most direct execution vehicle for the strategic bet. "
                f"What specifically is blocking it, who owns unblocking it, and by when?"
            ),
            "rationale": (
                "A blocked initiative that directly supports the strategic bet is "
                "the highest-leverage intervention point in the portfolio. "
                "Generic status updates won't move it — a named owner and deadline will."
            ),
        })

    for absent in pass2_output.get("expected_but_absent", []):
        category = absent.split("(")[0].strip()
        questions.append({
            "question": (
                f"No active initiatives appear in {category}. "
                f"Given the stated strategy and binding constraint, "
                f"is this work happening somewhere not captured in this data, "
                f"or is it genuinely absent from the portfolio?"
            ),
            "rationale": absent,
        })

    no_connection_count = pass2_output["bucket_counts"]["No clear strategic connection"]
    no_connection_pct = pass2_output["bucket_pct"]["No clear strategic connection"]
    if no_connection_count > 0:
        initiative_word = "initiative" if no_connection_count == 1 else "initiatives"
        questions.append({
            "question": (
                f"{no_connection_count} active {initiative_word} ({no_connection_pct}%) "
                f"have no clear connection to the strategic bet, binding constraint, "
                f"or deprioritized area. What are {"this initiative" if no_connection_count == 1 else "these initiatives"} for, "
                f"and who approved {"it" if no_connection_count == 1 else "them"} this quarter?"
            ),
            "rationale": (
                "Work with no strategic connection isn't necessarily wrong — "
                "it may be obligation or maintenance work. But it should be named and owned, "
                "not invisible."
            ),
        })

    return {"questions": questions}


def build_deterministic_drift(pass2_output: dict, strategy_context: dict) -> dict:
    """
    Generate drift findings and hidden contradictions deterministically.
    These are facts — they do not depend on Claude choosing to surface them.
    Claude only interprets and expands; it does not decide whether signals exist.
    """
    drift_findings = []
    hidden_contradictions = []

    tradeoff = strategy_context.get("deliberate_tradeoff_label", "the deprioritized area")
    deprioritized_count = pass2_output["bucket_counts"]["Related to deprioritized area"]
    deprioritized_pct = pass2_output["bucket_pct"]["Related to deprioritized area"]
    active_count = pass2_output["active_count"]

    # Signal 1: Deprioritized area drift
    if deprioritized_count > 0:
        drift_findings.append({
            "finding": (
                f"{deprioritized_count} of {active_count} active initiatives ({deprioritized_pct}%) "
                f"are classified as related to '{tradeoff}' — the area leadership explicitly "
                f"decided not to focus on this quarter."
            ),
            "evidence": (
                f"Strategic evidence mapping: 'Related to deprioritized area' bucket = "
                f"{deprioritized_count} initiatives ({deprioritized_pct}% of active portfolio). "
                f"Deliberate tradeoff declared: '{tradeoff}'."
            ),
            "severity": "High" if deprioritized_pct >= 20 else "Medium",
        })

    # Signal 2: Blocked bet initiatives
    if pass2_output["blocked_bet_count"] > 0:
        names = ", ".join(pass2_output["blocked_bet_initiatives"])
        drift_findings.append({
            "finding": (
                f"{pass2_output['blocked_bet_count']} initiative(s) directly supporting "
                f"the strategic bet are currently blocked: {names}. "
                f"Work that directly enables the strategic bet is not moving."
            ),
            "evidence": (
                f"Blocked initiatives mapped to 'Supports strategic bet' bucket: {names}."
            ),
            "severity": "High",
        })

    # Signal 2b: Binding constraint has zero portfolio support
    constraint = strategy_context.get("binding_constraint", "")
    constraint_count = pass2_output["bucket_counts"]["Supports binding constraint"]
    if constraint_count == 0 and constraint and constraint not in ("Other", "— select —"):
        drift_findings.append({
            "finding": (
                f"Zero active initiatives are classified as directly supporting the binding constraint: "
                f"'{constraint}'. The declared binding constraint — the thing that stops progress "
                f"if not addressed — has no visible portfolio presence."
            ),
            "evidence": (
                f"Strategic evidence mapping: 'Supports binding constraint' bucket = 0 initiatives. "
                f"Binding constraint declared: '{constraint}'."
            ),
            "severity": "High",
        })

    # Signal 3: Expected but absent categories
    for absent_item in pass2_output.get("expected_but_absent", []):
        hidden_contradictions.append({
            "observation": (
                f"No active initiatives found in: {absent_item.split('(')[0].strip()}."
            ),
            "implication": absent_item,
        })

    # Signal 4: High no-connection percentage — strategy may be too vague to filter
    no_connection_count = pass2_output["bucket_counts"]["No clear strategic connection"]
    no_connection_pct = pass2_output["bucket_pct"]["No clear strategic connection"]
    if no_connection_pct >= 40:
        initiative_word = "initiative" if no_connection_count == 1 else "initiatives"
        drift_findings.append({
            "finding": (
                f"{no_connection_count} of {active_count} active {initiative_word} ({no_connection_pct}%) "
                f"have no clear connection to the stated strategic bet, binding constraint, "
                f"or deprioritized area. This is not a drift signal — it is a coherence signal: "
                f"the strategy as stated does not provide enough specificity to filter execution."
            ),
            "evidence": (
                f"Strategic evidence mapping: 'No clear strategic connection' = "
                f"{no_connection_count} {initiative_word} ({no_connection_pct}% of active portfolio). "
                f"When this exceeds 40%, the strategy input lacks sufficient concrete terms "
                f"to anchor the portfolio analysis."
            ),
            "severity": "High" if no_connection_pct >= 60 else "Medium",
        })

    return {
        "drift_findings": {"findings": drift_findings},
        "hidden_contradictions": {"contradictions": hidden_contradictions},
    }


def run_reasoning(pass1_output: dict, pass2_output: dict,
                  strategy_context: dict, confidence_summary: dict) -> dict:
    """
    Main reasoning function.
    Drift findings and hidden contradictions are generated deterministically.
    Claude handles: portfolio snapshot, strategic alignment, leadership questions, confidence caveats.
    """
    client = anthropic.Anthropic()

    # Generate guaranteed findings deterministically — not dependent on Claude
    deterministic = build_deterministic_drift(pass2_output, strategy_context)
    deterministic_questions = build_deterministic_questions(pass2_output, strategy_context)

    system_prompt = build_system_prompt(strategy_context, confidence_summary)
    user_message = build_user_message(pass1_output, pass2_output, strategy_context, confidence_summary)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=system_prompt,
        tools=TOOLS,
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": user_message}],
    )

    # Start with deterministic findings — these are guaranteed
    results = {
        "portfolio_snapshot": None,
        "strategic_alignment": None,
        "drift_findings": deterministic["drift_findings"],
        "hidden_contradictions": deterministic["hidden_contradictions"],
        "leadership_questions": deterministic_questions,
        "confidence_caveats": None,
    }

    tool_map = {
        "write_portfolio_snapshot": "portfolio_snapshot",
        "identify_strategic_alignment": "strategic_alignment",
        "flag_confidence_caveats": "confidence_caveats",
        # Claude may add to these — merge rather than replace
        "identify_drift_findings": "_claude_drift",
        "surface_hidden_contradictions": "_claude_contradictions",
        "generate_leadership_questions": "_claude_questions",
    }

    for block in response.content:
        if block.type == "tool_use" and block.name in tool_map:
            key = tool_map[block.name]
            if key == "_claude_drift":
                claude_findings = block.input.get("findings", [])
                results["drift_findings"]["findings"].extend(claude_findings)
            elif key == "_claude_contradictions":
                claude_contradictions = block.input.get("contradictions", [])
                results["hidden_contradictions"]["contradictions"].extend(claude_contradictions)
            elif key == "_claude_questions":
                # Merge Claude additions with deterministic questions
                claude_questions = block.input.get("questions", [])
                results["leadership_questions"]["questions"].extend(claude_questions)
            else:
                results[key] = block.input

    return results
