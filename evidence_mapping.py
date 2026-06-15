"""
evidence_mapping.py
Pass 2: Strategic Evidence Mapping — deterministic only, no Claude.

Takes Pass 1 output + strategy context.
Maps each initiative into one of four strategic buckets.
Computes allocation percentages.
These numbers are what Claude reasons over in the judgment layer.
"""

import re
from schema import ACTIVE_STATUSES


def extract_strategy_keywords(strategy_context: dict) -> dict:
    """
    Parse strategy fields to extract keyword signals for evidence mapping.
    Returns structured keyword sets per strategic dimension.
    """
    def tokenize(text: str) -> list[str]:
        if not text:
            return []
        # Extract meaningful tokens, min 3 chars, exclude stopwords
        stopwords = {
            "the", "and", "for", "our", "are", "we", "to", "a", "an",
            "in", "of", "is", "it", "by", "as", "on", "at", "be",
            "this", "that", "with", "have", "will", "from", "or", "but",
            "not", "all", "can", "more", "most", "also", "so", "if",
            "its", "into", "than", "then", "they", "them", "their",
        }
        tokens = re.findall(r'\b[a-z]{3,}\b', text.lower())
        return [t for t in tokens if t not in stopwords]

    bet_text = " ".join([
        strategy_context.get("strategic_bet", ""),
        strategy_context.get("success_evidence", ""),
    ])
    tradeoff_text = strategy_context.get("deliberate_tradeoff_label", "")
    constraint_text = strategy_context.get("binding_constraint", "")

    # Additional domain expansion based on common strategic themes
    domain_expansions = {
        "enterprise": ["enterprise", "b2b", "corporate", "compliance", "security",
                       "soc2", "hipaa", "audit", "procurement", "sales", "deal"],
        "smb": ["smb", "small business", "self-serve", "self serve", "freemium",
                "trial", "signup", "onboarding", "low-touch"],
        "retention": ["retention", "churn", "renewal", "expansion", "nps", "csat",
                      "health score", "customer success", "adoption"],
        "growth": ["growth", "acquisition", "new user", "signup", "lead", "pipeline",
                   "conversion", "activation"],
        "platform": ["platform", "infrastructure", "api", "integration", "developer",
                     "sdk", "marketplace"],
        "ai": ["ai", "ml", "machine learning", "llm", "model", "intelligence",
               "automation", "prediction"],
    }

    bet_keywords = set(tokenize(bet_text))
    # Expand bet keywords with domain terms if any domain word appears
    for domain, expansions in domain_expansions.items():
        if domain in bet_keywords or any(e in bet_text.lower() for e in expansions):
            bet_keywords.update(expansions)

    tradeoff_keywords = set(tokenize(tradeoff_text))
    constraint_keywords = set(tokenize(constraint_text))

    return {
        "bet_keywords": bet_keywords,
        "tradeoff_keywords": tradeoff_keywords,
        "constraint_keywords": constraint_keywords,
    }


def score_initiative_alignment(initiative: dict, keyword_sets: dict) -> str:
    """
    Assign each initiative to a strategic evidence bucket.

    Buckets (in priority order):
    1. Supports strategic bet
    2. Related to deprioritized area (drift signal)
    3. Supports binding constraint
    4. No clear strategic connection
    """
    text = " ".join([
        initiative.get("title", ""),
        initiative.get("description", ""),
        initiative.get("labels", ""),
        initiative.get("category", ""),
    ]).lower()

    def match_score(keywords: set) -> int:
        return sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', text))

    bet_score = match_score(keyword_sets["bet_keywords"])
    tradeoff_score = match_score(keyword_sets["tradeoff_keywords"])
    constraint_score = match_score(keyword_sets["constraint_keywords"])

    # Tradeoff check runs independently — an initiative can support the bet
    # AND be related to the deprioritized area (interesting contradiction signal)
    is_tradeoff_related = tradeoff_score >= 1

    if bet_score >= 2:
        bucket = "Supports strategic bet"
    elif bet_score == 1 and constraint_score >= 1:
        bucket = "Supports strategic bet"  # bet + constraint alignment = bet
    elif constraint_score >= 2:
        bucket = "Supports binding constraint"
    elif bet_score == 1:
        bucket = "Supports strategic bet"
    elif constraint_score == 1:
        bucket = "Supports binding constraint"
    else:
        bucket = "No clear strategic connection"

    # Override or flag if also tradeoff-related
    if is_tradeoff_related:
        if bucket == "Supports strategic bet":
            # Contradictory signal: doing the thing they said they'd stop
            bucket = "Related to deprioritized area"
        else:
            bucket = "Related to deprioritized area"

    return bucket


def run_pass2(pass1_output: dict, strategy_context: dict) -> dict:
    """
    Main Pass 2 function.
    Takes Pass 1 structured output + strategy context dict.
    Returns evidence mapping results with allocation metrics.
    """
    initiatives = pass1_output["initiatives"]
    keyword_sets = extract_strategy_keywords(strategy_context)

    # Map each initiative
    bucket_assignments = []
    for initiative in initiatives:
        bucket = score_initiative_alignment(initiative, keyword_sets)
        bucket_assignments.append({
            **initiative,
            "evidence_bucket": bucket,
        })

    # Active initiatives only for allocation metrics
    active_initiatives = [
        i for i in bucket_assignments
        if i["status"] in ACTIVE_STATUSES
    ]
    active_count = len(active_initiatives)

    # Bucket counts and percentages (active only — this is the signal)
    bucket_counts = {
        "Supports strategic bet": 0,
        "Supports binding constraint": 0,
        "Related to deprioritized area": 0,
        "No clear strategic connection": 0,
    }
    for i in active_initiatives:
        bucket = i["evidence_bucket"]
        if bucket in bucket_counts:
            bucket_counts[bucket] += 1

    bucket_pct = {}
    for bucket, count in bucket_counts.items():
        bucket_pct[bucket] = round(count / active_count * 100, 1) if active_count > 0 else 0.0

    # Blocked initiatives that support the bet — priority intervention signal
    blocked_bet_initiatives = [
        i for i in bucket_assignments
        if i["status"] == "Blocked" and i["evidence_bucket"] == "Supports strategic bet"
    ]

    # Absence signal: categories expected given strategy but not present
    present_categories = set(i["category"] for i in active_initiatives)
    expected_but_absent = _detect_absent_categories(strategy_context, present_categories)

    return {
        "initiatives": bucket_assignments,
        "active_count": active_count,
        "bucket_counts": bucket_counts,
        "bucket_pct": bucket_pct,
        "blocked_bet_count": len(blocked_bet_initiatives),
        "blocked_bet_initiatives": [i["title"] for i in blocked_bet_initiatives],
        "expected_but_absent": expected_but_absent,
        "keyword_sets": {k: list(v) for k, v in keyword_sets.items()},
    }


def _detect_absent_categories(strategy_context: dict, present_categories: set) -> list[str]:
    """
    Given the strategic bet, identify categories that would be expected
    but are absent from the active portfolio.
    This feeds Claude's absence detection reasoning.
    """
    bet = strategy_context.get("strategic_bet", "").lower()
    evidence = strategy_context.get("success_evidence", "").lower()
    constraint = strategy_context.get("binding_constraint", "").lower()
    combined = bet + " " + evidence + " " + constraint

    absent = []

    # Enterprise signals → expect compliance/security
    if any(kw in combined for kw in ["enterprise", "b2b", "corporate", "upmarket"]):
        if "Compliance / Security" not in present_categories:
            absent.append("Compliance / Security (typical prerequisite for enterprise sales)")

    # Revenue/growth signals → expect GTM
    if any(kw in combined for kw in ["revenue", "growth", "acquisition", "sales", "customer"]):
        if "GTM / Sales Enablement" not in present_categories:
            absent.append("GTM / Sales Enablement (expected given revenue/growth focus)")

    # Retention/churn signals → expect customer success
    if any(kw in combined for kw in ["retention", "churn", "renewal", "expand"]):
        if "Customer Success / Onboarding" not in present_categories:
            absent.append("Customer Success / Onboarding (expected given retention focus)")

    # Validation constraint → expect research/discovery
    if "customer validation" in constraint or "validation" in constraint:
        if "Research / Discovery" not in present_categories:
            absent.append("Research / Discovery (expected given customer validation as binding constraint)")

    # Talent constraint → expect hiring
    if "talent" in constraint or "hiring" in constraint:
        if "Hiring / Team Building" not in present_categories:
            absent.append("Hiring / Team Building (expected given talent as binding constraint)")

    return absent
