"""
preprocessing.py
Pass 1: Portfolio Classification — deterministic only, no Claude.

Responsibilities:
- Validate and normalize the uploaded CSV
- Map user columns to standard schema
- Normalize status values
- Classify each initiative into a category using keyword matching
- Compute portfolio-level derived metrics
"""

import re
import pandas as pd
from typing import Optional
from schema import (
    REQUIRED_COLUMNS,
    ACTIVE_STATUSES,
    STATUS_DEFAULTS,
    CATEGORY_KEYWORDS,
    CLASSIFICATION_CONFIDENCE_THRESHOLDS,
)

# ── Column name fuzzy matching ──────────────────────────────────────────────

def suggest_column_mapping(df_columns: list[str]) -> dict[str, Optional[str]]:
    """
    Given a list of CSV column names, suggest mappings to standard schema fields.
    Returns {schema_field: csv_column_or_None}.
    Used to pre-populate the column mapping UI — user confirms before run.
    """
    schema_hints = {
        "title": ["title", "name", "initiative", "task", "issue", "summary", "subject", "item"],
        "status": ["status", "state", "stage", "phase", "current_status", "current status",
                   "list name", "list", "column", "status (status)", "status_(status)"],
        "description": ["description", "desc", "details", "body", "notes",
                        "initiative_desc", "task_desc", "issue_desc", "detail",
                        "notes (long text)", "description (long text)"],
        "owner": ["owner", "assignee", "assigned", "responsible", "lead", "reporter",
                  "whos_doing", "who_is", "person", "member", "teammate",
                  "people", "person (people)", "assigned to"],
        "priority": ["priority", "p0", "p1", "urgency", "severity", "importance",
                     "priority (dropdown)"],
        "labels": ["labels", "tags", "label", "tag", "category", "type", "component",
                   "tags (tags)"],
        "due_date": ["due", "due_date", "deadline", "target", "end_date", "eta",
                     "due date (date)", "date (date)"],
        "last_updated": ["updated", "last_updated", "modified", "last_modified", "updated_at",
                         "last modified date"],
    }

    normalized = {col: col.lower().strip().replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "")
                  for col in df_columns}

    mapping = {}
    for schema_field, hints in schema_hints.items():
        match = None
        best_score = 0
        for col, norm in normalized.items():
            # Score: 3 = exact match, 2 = hint is in norm, 1 = norm is in hint (weak)
            score = 0
            for hint in hints:
                hint_norm = hint.replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "")
                if norm == hint_norm:
                    score = max(score, 3)
                elif hint_norm in norm:
                    score = max(score, 2)
                elif norm in hint_norm and len(norm) > 3:
                    score = max(score, 1)
            if score > best_score:
                best_score = score
                match = col
        mapping[schema_field] = match

    return mapping


# ── CSV validation ──────────────────────────────────────────────────────────

def validate_csv(df: pd.DataFrame, column_mapping: dict[str, str]) -> dict:
    """
    Validate the dataframe against required schema fields.
    Returns {valid: bool, errors: list, warnings: list}.
    """
    errors = []
    warnings = []

    # Check required columns are mapped
    for req in REQUIRED_COLUMNS:
        if not column_mapping.get(req):
            errors.append(f"Required field '{req}' is not mapped to any column.")

    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}

    # Rename to standard schema
    rename_map = {v: k for k, v in column_mapping.items() if v}
    df_std = df.rename(columns=rename_map)

    # Row count checks
    if len(df_std) < 5:
        errors.append(f"Upload contains only {len(df_std)} rows. Minimum 5 required.")
    if len(df_std) > 300:
        warnings.append(
            f"Upload contains {len(df_std)} rows. Analysis will run but may be slower. "
            "Consider filtering to active initiatives only for faster, more focused results."
        )

    # Null checks on required fields
    title_col = column_mapping.get("title")
    if title_col and title_col in df.columns:
        null_titles = int(df[title_col].isna().sum())
        if null_titles > 0:
            warnings.append(f"{null_titles} initiatives have no title and will be excluded.")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


# ── Status normalization ────────────────────────────────────────────────────

def normalize_status(status_value: str, status_map: dict[str, str]) -> str:
    """
    Map a raw status value to a standard status using the user-confirmed map.
    Falls back to fuzzy default if not in user map.
    """
    if pd.isna(status_value):
        return "Backlog"
    normalized = str(status_value).lower().strip()
    if normalized in status_map:
        return status_map[normalized]
    # Fuzzy fallback
    return STATUS_DEFAULTS.get(normalized, "Backlog")


# ── Initiative classification ───────────────────────────────────────────────

def classify_initiative(title: str, description: str = "", labels: str = "") -> tuple[str, bool]:
    """
    Classify an initiative into a category using keyword matching.
    Returns (category, had_sufficient_context).
    had_sufficient_context = True if description or labels were non-empty.
    """
    text = " ".join([
        str(title or ""),
        str(description or ""),
        str(labels or ""),
    ]).lower()

    # Score each category
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        if category == "Unclear / Insufficient Information":
            continue
        score = sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', text))
        if score > 0:
            scores[category] = score

    had_context = bool(str(description or "").strip() or str(labels or "").strip())

    if not scores:
        return "Unclear / Insufficient Information", had_context

    return max(scores, key=scores.get), had_context


# ── Pass 1: Full portfolio classification ──────────────────────────────────

def run_pass1(df: pd.DataFrame, column_mapping: dict[str, str],
              status_map: dict[str, str]) -> dict:
    """
    Main Pass 1 function.
    Takes the raw dataframe + user-confirmed column mapping and status map.
    Returns structured portfolio metrics — no Claude, no raw data forwarded.
    """
    # Normalize to standard schema
    rename_map = {v: k for k, v in column_mapping.items() if v}
    df = df.rename(columns=rename_map).copy()

    # Drop fully blank rows early
    df = df.dropna(how="all").reset_index(drop=True)

    # Cast title to string to handle numeric IDs or mixed types, then drop empty
    if "title" in df.columns:
        df["title"] = df["title"].astype(str).str.strip()
        df = df[df["title"].notna() & (df["title"] != "") & (df["title"] != "nan")].reset_index(drop=True)

    # Normalize status
    df["status_normalized"] = df["status"].apply(
        lambda s: normalize_status(s, status_map)
    ) if "status" in df.columns else "Backlog"

    # Classify each initiative
    classifications = []
    had_context_flags = []
    for _, row in df.iterrows():
        cat, had_ctx = classify_initiative(
            title=row.get("title", ""),
            description=row.get("description", ""),
            labels=row.get("labels", ""),
        )
        classifications.append(cat)
        had_context_flags.append(had_ctx)

    df["category"] = classifications
    df["had_context"] = had_context_flags

    # ── Derived metrics ────────────────────────────────────────────────────

    total = len(df)
    active_df = df[df["status_normalized"].isin(ACTIVE_STATUSES)]
    active_count = len(active_df)
    blocked_count = len(df[df["status_normalized"] == "Blocked"])
    complete_count = len(df[df["status_normalized"] == "Complete"])
    backlog_count = len(df[df["status_normalized"] == "Backlog"])

    # Category distribution (all initiatives)
    category_counts = df["category"].value_counts().to_dict()
    category_pct = {k: round(v / total * 100, 1) for k, v in category_counts.items()}

    # Category distribution (active only)
    if active_count > 0:
        active_category_counts = active_df["category"].value_counts().to_dict()
        active_category_pct = {k: round(v / active_count * 100, 1)
                                for k, v in active_category_counts.items()}
    else:
        active_category_counts = {}
        active_category_pct = {}

    # Owner load (if owner column present)
    owner_distribution = {}
    if "owner" in df.columns:
        owner_counts = df[df["owner"].notna()]["owner"].value_counts()
        owner_distribution = owner_counts.head(10).to_dict()

    # Staleness (if last_updated present)
    stale_count = 0
    if "last_updated" in df.columns:
        try:
            df["last_updated_parsed"] = pd.to_datetime(df["last_updated"], errors="coerce")
            cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
            stale_count = int(
                (active_df["last_updated_parsed"].dropna() < cutoff).sum()
                if "last_updated_parsed" in active_df.columns else 0
            )
        except Exception:
            stale_count = 0

    # Classification confidence
    pct_with_context = sum(had_context_flags) / total if total > 0 else 0
    unclear_count = category_counts.get("Unclear / Insufficient Information", 0)

    if pct_with_context >= CLASSIFICATION_CONFIDENCE_THRESHOLDS["High"]:
        classification_confidence = "High"
    elif pct_with_context >= CLASSIFICATION_CONFIDENCE_THRESHOLDS["Medium"]:
        classification_confidence = "Medium"
    else:
        classification_confidence = "Low"

    # Build per-initiative records for Pass 2
    initiatives = []
    for _, row in df.iterrows():
        initiatives.append({
            "title": str(row.get("title", "")),
            "status": str(row.get("status_normalized", "")),
            "category": str(row.get("category", "")),
            "description": str(row.get("description", ""))[:300] if pd.notna(row.get("description")) else "",
            "owner": str(row.get("owner", "")) if pd.notna(row.get("owner", "")) else "",
            "labels": str(row.get("labels", "")) if pd.notna(row.get("labels", "")) else "",
            "had_context": bool(row.get("had_context", False)),
        })

    return {
        "total_count": total,
        "active_count": active_count,
        "blocked_count": blocked_count,
        "complete_count": complete_count,
        "backlog_count": backlog_count,
        "category_counts": category_counts,
        "category_pct": category_pct,
        "active_category_counts": active_category_counts,
        "active_category_pct": active_category_pct,
        "owner_distribution": owner_distribution,
        "stale_count": stale_count,
        "unclear_count": unclear_count,
        "pct_with_context": round(pct_with_context * 100, 1),
        "classification_confidence": classification_confidence,
        "initiatives": initiatives,
    }
