"""
schema.py
Standard schema definitions for Initiative Intelligence.
All column mapping targets, category taxonomy, status normalization,
and strategy context structure defined here.
Nothing in this file calls Claude.
"""

# ── Required and optional CSV columns ──────────────────────────────────────
REQUIRED_COLUMNS = ["title", "status"]

OPTIONAL_COLUMNS = [
    "description",
    "owner",
    "priority",
    "labels",
    "due_date",
    "last_updated",
]

ALL_SCHEMA_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

# Human-readable labels for the column mapping UI
COLUMN_LABELS = {
    "title": "Initiative Title *",
    "status": "Status *",
    "description": "Description",
    "owner": "Owner / Assignee",
    "priority": "Priority",
    "labels": "Labels / Tags",
    "due_date": "Due Date",
    "last_updated": "Last Updated",
}

# ── Status normalization ────────────────────────────────────────────────────
STANDARD_STATUSES = [
    "Active",
    "Blocked",
    "Complete",
    "Backlog",
    "In Review",
    "Cancelled",
]

# Common status strings from Jira/Linear/Asana → standard status
# Used as fuzzy defaults; user confirms via UI
STATUS_DEFAULTS = {
    # Active variants
    "in progress": "Active",
    "in-progress": "Active",
    "in-flight": "Active",
    "in flight": "Active",
    "doing": "Active",
    "wip": "Active",
    "started": "Active",
    "active": "Active",
    "open": "Active",
    "almost done": "In Review",
    "staged": "In Review",
    "staging": "In Review",
    # Blocked variants
    "blocked": "Blocked",
    "on hold": "Blocked",
    "waiting": "Blocked",
    "paused": "Blocked",
    "impediment": "Blocked",
    # Complete variants
    "done": "Complete",
    "complete": "Complete",
    "completed": "Complete",
    "closed": "Complete",
    "resolved": "Complete",
    "shipped": "Complete",
    "released": "Complete",
    # Backlog variants
    "backlog": "Backlog",
    "todo": "Backlog",
    "to do": "Backlog",
    "to-do": "Backlog",
    "planned": "Backlog",
    "new": "Backlog",
    "open": "Backlog",
    # In Review variants
    "in review": "In Review",
    "review": "In Review",
    "pr open": "In Review",
    "testing": "In Review",
    "qa": "In Review",
    # Cancelled variants
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
    "won't do": "Cancelled",
    "wontdo": "Cancelled",
    "rejected": "Cancelled",
    "dropped": "Cancelled",
    "waiting on": "Blocked",
    "waiting": "Blocked",
}

# Statuses that count as "active work" for analysis purposes
ACTIVE_STATUSES = {"Active", "Blocked", "In Review"}

# ── Initiative category taxonomy ────────────────────────────────────────────
INITIATIVE_CATEGORIES = [
    "Product / Feature Development",
    "Infrastructure / Platform",
    "Reliability / Quality",
    "Compliance / Security",
    "Customer Success / Onboarding",
    "GTM / Sales Enablement",
    "Hiring / Team Building",
    "Internal Operations / Tooling",
    "Research / Discovery",
    "Unclear / Insufficient Information",
]

# Keyword signals per category (title + description matching)
CATEGORY_KEYWORDS = {
    "Product / Feature Development": [
        "feature", "product", "launch", "ship", "build", "implement",
        "new", "v2", "redesign", "revamp", "add", "create", "develop",
        "mvp", "beta", "release", "roadmap", "ui", "ux", "flow",
        "dashboard", "page", "screen", "component", "api", "endpoint",
        "integration", "workflow",
    ],
    "Infrastructure / Platform": [
        "infrastructure", "platform", "architecture", "database", "db",
        "backend", "server", "cloud", "aws", "gcp", "azure", "kubernetes",
        "k8s", "docker", "deploy", "deployment", "pipeline", "ci/cd",
        "devops", "scaling", "scale", "performance", "latency", "uptime",
        "migration", "upgrade", "refactor", "rewrite", "framework",
        "microservice", "monolith", "service",
    ],
    "Reliability / Quality": [
        "bug", "fix", "reliability", "quality", "testing", "test",
        "qa", "regression", "stability", "incident", "postmortem",
        "alert", "monitoring", "observability", "logging", "error",
        "crash", "outage", "slo", "sla", "uptime", "coverage",
        "flaky", "debt", "technical debt",
    ],
    "Compliance / Security": [
        "compliance", "security", "soc2", "soc 2", "hipaa", "gdpr",
        "audit", "access control", "rbac", "permission", "auth",
        "authentication", "authorization", "encryption", "pen test",
        "penetration", "vulnerability", "cve", "iso", "certif",
        "privacy", "data protection", "infosec", "firewall",
        "logging", "audit log", "access log",
    ],
    "Customer Success / Onboarding": [
        "onboarding", "customer success", "cs", "retention", "churn",
        "nps", "csat", "support", "ticket", "helpdesk", "documentation",
        "docs", "training", "user guide", "tutorial", "activation",
        "adoption", "engagement", "health score", "qbr", "renewal",
        "expansion", "upsell", "cross-sell",
    ],
    "GTM / Sales Enablement": [
        "gtm", "go-to-market", "sales", "marketing", "demand gen",
        "lead", "pipeline", "prospect", "outbound", "inbound",
        "campaign", "content", "seo", "paid", "ads", "brand",
        "positioning", "messaging", "enablement", "playbook",
        "crm", "hubspot", "salesforce", "demo", "trial", "pricing",
        "packaging", "partnership", "channel",
    ],
    "Hiring / Team Building": [
        "hire", "hiring", "recruit", "recruiting", "headcount",
        "team", "org", "culture", "onboard", "interview",
        "job", "role", "position", "candidate", "offer",
        "compensation", "salary", "performance review", "okr",
        "manager", "ic", "leveling",
    ],
    "Internal Operations / Tooling": [
        "internal", "ops", "operations", "tooling", "tool",
        "process", "workflow", "automation", "efficiency",
        "reporting", "analytics", "data", "metrics", "kpi",
        "finance", "legal", "vendor", "procurement", "contract",
        "admin", "it", "helpdesk", "slack", "notion", "jira",
    ],
    "Research / Discovery": [
        "research", "discovery", "explore", "spike", "poc",
        "proof of concept", "prototype", "experiment", "test",
        "hypothesis", "user research", "interview", "survey",
        "analysis", "investigate", "evaluate", "assess",
        "feasibility", "rfc", "design doc",
    ],
}

# ── Strategy context structure ──────────────────────────────────────────────
BINDING_CONSTRAINTS = [
    "Runway / Capital",
    "Talent / Hiring capacity",
    "Product readiness",
    "Customer validation",
    "Distribution / GTM",
    "Regulatory / Compliance",
    "Other",
]

PORTFOLIO_SCOPES = [
    "Entire company",
    "Product & Engineering only",
    "GTM / Sales only",
    "Operations only",
    "Other / Partial",
]

STRATEGIC_HORIZONS = [
    "This quarter (< 3 months)",
    "6 months",
    "12 months",
    "2+ years",
]

# ── Confidence thresholds ───────────────────────────────────────────────────
# Classification confidence based on % of initiatives with usable descriptions
CLASSIFICATION_CONFIDENCE_THRESHOLDS = {
    "High": 0.70,    # >= 70% have descriptions
    "Medium": 0.40,  # 40–69%
    # Below 40% → Low
}
