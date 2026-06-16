# Initiative Intelligence — Strategy Drift Detection

**A continuous audit of whether execution still reflects intent.**

Part of the [Ground Truth Decisioning System](https://thomasmeerschwam.com) by Thomas Meerschwam.

> *Every company has a strategy document and a project management system. Almost none of them have anything that compares the two.*

---

## What It Does

Initiative Intelligence takes a portfolio of active work (from Jira, Linear, Asana, Notion, or any CSV export) combined with five minutes of strategic context, and identifies where execution appears aligned, misaligned, or disconnected from stated priorities.

The tool does not prioritize work. It detects drift — the gap between what leadership says the company is focused on and what the organization is actually doing.

A strong output looks like:

> *"Leadership identified customer validation as the primary constraint. Only 11% of active initiatives appear connected to acquisition, onboarding, retention, or user research."*

> *"Enterprise expansion is the stated strategic bet. 28.6% of active work is related to SMB self-serve — the area leadership explicitly deprioritized this quarter."*

If the reaction is "damn, that's actually right" — the tool has succeeded.

---

## Architecture

```
CSV Upload + Strategy Context
        │
        ▼
Layer 1 — Deterministic Preprocessing (preprocessing.py)
  Pass 1: Portfolio Classification
    • Column mapping + status normalization
    • Initiative categorization (keyword-based, no Claude)
    • Owner load, stale initiative detection
    • Classification confidence scoring
        │
        ▼
  Pass 2: Strategic Evidence Mapping (evidence_mapping.py)
    • Keyword extraction from strategy fields
    • Initiative → evidence bucket assignment
    • Allocation percentages (active initiatives only)
    • Absence detection (expected categories not present)
    • Portfolio coverage confidence
        │
        ▼
Layer 2 — Judgment Layer (claude_reasoning.py)
  Claude Sonnet via structured tool use (6 tools)
    • Portfolio snapshot
    • Strategic alignment (incl. prerequisite work)
    • Drift findings (quantified, horizon-calibrated)
    • Hidden contradictions + absence detection
    • Leadership questions
    • Confidence caveats
        │
        ▼
Layer 3 — Output + Export (output_display.py, export.py)
  • Confidence header (classification + coverage)
  • Allocation summary
  • Six output sections
  • .txt export with strategy inputs included
```

**Design principle:** Claude never sees raw CSV data. The deterministic layer runs first, produces structured metrics, and Claude reasons over clean signal only.

---

## Setup

```bash
git clone <repo>
cd initiative_intelligence
pip install -r requirements.txt
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
streamlit run app.py
```

### `.env.example`
```
ANTHROPIC_API_KEY=your_key_here
```

---

## Input

**CSV export from any project management tool.**

| Field | Required | Notes |
|---|---|---|
| Title / Name | ✓ | Initiative name |
| Status | ✓ | Any format — normalized via UI |
| Description | Recommended | Significantly improves classification quality |
| Owner / Assignee | Optional | Enables owner load analysis |
| Priority | Optional | Surfaced in output |
| Labels / Tags | Optional | Improves classification |
| Due Date | Optional | |
| Last Updated | Optional | Enables stale initiative detection |

Minimum: 5 rows. Soft cap: 300 rows.

**Supported sources:** Jira, Linear, Asana, Notion, Trello, Monday.com, or any spreadsheet exported as CSV.

**Jira:** Use "Export CSV (current fields)" from the issue search view. The title column exports as `Summary` — select that in the column mapping UI (the fuzzy matcher may suggest `Issue Key` instead).

**Linear:** Use Settings → Administration → Import/Export → Export CSV. Column names map automatically — no manual correction needed.

**Asana:** Asana does not export a native Status column. Before exporting, add a "Status" custom field to your project and populate it. Without this, all initiatives will default to Backlog in the analysis. Export via the project dropdown → Export/sync → CSV.

**Notion:** Export the database as CSV via the ••• menu → Export → Markdown & CSV. The export downloads as a ZIP — unzip it first and upload the CSV. Column names reflect your property names, so they vary. Relation properties export as UUIDs rather than readable text — avoid mapping those columns. Use simple text, select, and date properties for best results.

**Trello:** CSV export requires Trello Premium. Free users can only export JSON, which this tool does not accept. For Premium users: Show Menu → More → Print and Export → Export as CSV. Trello uses "List Name" as its status equivalent (cards live in lists, not status fields) — manually map the `List Name` column to Status in the column mapping UI.

**Monday.com:** Export via the board menu → Export to Excel, then save as CSV. Column headers include the column type in parentheses (e.g. `Status (Status)`, `Due Date (Date)`) — the fuzzy matcher handles these correctly. Owner/Person columns export as email addresses rather than names.

---

## Confidence Scoring

Two independent dimensions surfaced in every output:

**Classification Confidence** — how reliably the tool interpreted initiative descriptions:
- High: ≥70% of initiatives had descriptions or labels
- Medium: 40–69%
- Low: <40% — treat findings as directional hypotheses

**Portfolio Coverage Confidence** — how complete the uploaded data is:
- Complete: entire company uploaded
- Partial: single function (P&E, GTM, etc.)
- Limited: partial/unknown scope

---

## Design Decisions

**Why not Linear/Jira MCP integration?**
The value of the tool is in the reasoning layer, not the ingestion layer. CSV export covers Jira, Linear, Asana, Notion, and spreadsheets with a single input type. Live MCP integration is the planned v2 extension — documented here rather than built before the core reasoning was validated.

**Why two deterministic passes before Claude?**
Category classification and evidence mapping are different operations. A compliance initiative classified as "Infrastructure" may be perfectly aligned with an enterprise bet — it's prerequisite work. Pass 1 establishes what exists. Pass 2 establishes what it means relative to strategy. Claude then interprets the structured output of both passes. This keeps Claude in its correct role: interpretation, not computation.

**Why questions, not recommendations?**
The tool surfaces what the data reveals. It does not tell leadership what to do. Questions force the strategic conversation the data implies is needed. Recommendations would short-circuit that conversation.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | Python |
| API | Anthropic Claude Sonnet (structured tool use) |
| Data | pandas |
| Hosting | Streamlit Community Cloud |

---

## Known Limitations (v1)

- No persistence — single-run analysis only
- No live integrations — CSV export only
- Classification relies on keyword matching — sparse initiative data degrades quality (surfaced in confidence score)
- Portfolio scope is user-declared — tool cannot verify completeness
- Single-threaded hosting — not for high concurrency

---

## Part of the Ground Truth Decisioning System

| Tool | Question | Signal |
|---|---|---|
| WBR Generator | What happened? | Operational reality |
| Meeting Intelligence | What was decided? | Decision reality |
| Pipeline Synthesizer | What will happen? | Commercial reality |
| **Initiative Intelligence** | **What is getting done?** | **Strategic reality** |
| Executive Attention Synthesizer | What matters now? | Leadership reality |

[thomasmeerschwam.com](https://thomasmeerschwam.com)
