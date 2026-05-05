# M&A Dashboard Project – Final Handoff / Run Guide

## 1. What the project now does

This project builds a Bloomberg-driven M&A analytics dashboard.

The current version covers the full pipeline from data ingestion to UI:

- ingest pending and completed M&A deals
- store them in SQLite
- load deal terms, price data, volume data, and spread inputs
- compute target analysis
- compute spread analysis
- select top analogue deals
- compare a pending deal against analogue history
- ingest external public sources/news for pending deals
- display everything in a UI with:
  - pending deal selector
  - deal metadata
  - sources/news
  - interpretation/commentary
  - analogue table
  - comparison charts

## 2. What is in scope right now

### Core data / analytics
The database and analytics currently support:

- pending and completed deals
- target / acquirer company storage
- prices
- volumes
- spread analysis
- analogue selection
- analogue comparison
- event sources/news
- ownership tables (schema present; broader holder workflow may still depend on teammate work)

### UI
The frontend now supports:

- selecting a pending deal
- showing deal summary fields
- showing sources/news links
- showing interpretation bullets
- showing analogue comparison metrics
- showing charts for:
  - target return
  - spread
  - volume ratio

### Error handling
If a deal is not comparison-ready, the UI shows a clean warning rather than crashing.

## 3. Important limitation

The project stores structured summary fields for each deal, but it does not currently store a Bloomberg-style free-text prose summary paragraph for each deal.

What is available instead are structured summary fields such as:

- payment type
- nature of bid
- percent sought
- dates
- cash / stock terms
- announced value
- status

This is enough for the dashboard and should be sufficient for the project outcome, but it is worth knowing explicitly.

## 4. Main project structure

```text
MA-analysis/
├─ data/
│  ├─ pending_deals.csv
│  └─ completed_deals.csv
├─ ma_index_tracker/
│  ├─ bloomberg_client.py
│  ├─ bulk_loader.py
│  ├─ analysis.py
│  ├─ spread_analysis.py
│  ├─ analogues.py
│  ├─ comparison.py
│  ├─ data_quality.py
│  ├─ event_view.py
│  ├─ source_ingestion.py
│  └─ db/
│     ├─ schema.py
│     └─ database.py
├─ ui/
│  ├─ backend/
│  │  ├─ app/
│  │  │  ├─ main.py
│  │  │  ├─ db.py
│  │  │  ├─ schemas.py
│  │  │  └─ __init__.py
│  │  └─ requirements.txt
│  └─ frontend/
│     ├─ app/
│     ├─ components/
│     ├─ lib/
│     ├─ package.json
│     └─ ...
├─ ma_index_tracker.sqlite
└─ run_*.py helper scripts
```

## 5. Main logic modules

### Ingestion / Bloomberg
- `ma_index_tracker/bloomberg_client.py`
- `ma_index_tracker/bulk_loader.py`

### Database
- `ma_index_tracker/db/schema.py`
- `ma_index_tracker/db/database.py`

### Analytics
- `ma_index_tracker/analysis.py`
- `ma_index_tracker/spread_analysis.py`
- `ma_index_tracker/analogues.py`
- `ma_index_tracker/comparison.py`
- `ma_index_tracker/event_view.py`

### Sources / news
- `ma_index_tracker/source_ingestion.py`
- `run_source_ingestion.py`

### UI backend
- `ui/backend/app/main.py`

### UI frontend
- `ui/frontend/app/page.tsx`
- `ui/frontend/components/*`
- `ui/frontend/lib/api.ts`

## 6. Backend API endpoints

Current backend endpoints include:

- `GET /health`
- `GET /pending-deals`
- `GET /deal/{event_id}/summary`
- `GET /deal/{event_id}/sources`
- `GET /deal/{event_id}/analogues`
- `GET /deal/{event_id}/comparison`

## 7. How to run the project

### A. Backend

Open a terminal in:

```text
ui/backend
```

Run:

```bash
python -m uvicorn app.main:app --reload
```

Backend should run at:

```text
http://127.0.0.1:8000
```

Quick health check:

```text
http://127.0.0.1:8000/health
```

### B. Frontend

Open a second terminal in:

```text
ui/frontend
```

Run:

If the frontend has trouble starting cleanly because of stale Next build output, remove the build cache first:

```bash
rm -rf .next
```

Then run:

```bash
npm run dev
```

Frontend should run at:

```text
http://localhost:3000
```

### C. Important note
Both backend and frontend need to be running at the same time.

## 8. How to run source/news ingestion

To ingest sources for one event only:

```bash
python run_source_ingestion.py --event-id 2
```

To ingest sources for all pending events:

```bash
python run_source_ingestion.py
```

Notes:
- some events may return 0 sources
- some may fail temporarily due to rate limiting (HTTP 429)
- these can be retried later individually

## 9. How the UI currently behaves

For a selected deal, the UI shows:

1. pending deal list in the sidebar
2. deal summary card
3. sources/news section
4. interpretation/commentary section
5. headline metrics
6. analogue table
7. charts:
   - target return path
   - spread path
   - volume ratio path

If comparison data is unavailable for a deal, the UI shows a warning message instead of failing.

## 10. How analogue deals are chosen

The analogue selection logic is designed to compare a pending deal against historically completed deals that are structurally similar.

### Candidate pool
The selector starts from completed deals only.

It then filters candidates using:
- compatible payment type
- data-quality checks
- required fields being present for comparison

This prevents dirty or unusable rows from entering the analogue set.

### Payment-type matching
The first major constraint is payment type compatibility.

For example:
- cash deals are compared against cash deals
- stock deals against stock deals
- cash-and-stock deals against cash-and-stock deals

This is important because deal structure strongly affects spread behaviour and market reaction.

### Tiered selection
The selector is intentionally tiered:

#### Tier 1: same-sector analogues
Completed deals with:
- the same payment type
- the same target sector

These are treated as the strongest analogues.

#### Tier 2: fallback analogues
Completed deals with:
- the same payment type
- a different target sector

These are only used after same-sector analogues, so the tool remains honest when strong same-sector history is limited.

### Ranking inside each tier
Within each tier, candidates are ranked using similarity features such as:
- deal size similarity
- percent sought similarity
- nature of bid similarity

So the final top analogue set is based on both:
- structural similarity
- ranking quality within the relevant tier

### Why this matters
This means the dashboard does not simply return “the ten biggest similar-looking deals.”

Instead, it prefers:
1. same-sector, same-structure historical deals
2. then fallback structural analogues when the same-sector pool is too small

This makes the analogue comparison more interpretable and more defensible in the final dashboard.

## 11. Commentary / interpretation logic

The interpretation section is currently based on the analytics output and compares:

- pending announcement jump vs analogue median
- pending day-5 return vs analogue median
- pending latest spread vs analogue median
- same-sector analogue count vs fallback analogue count

This means the commentary is deterministic and grounded in the actual analytics already computed.

## 12. Database / schema update note

At one stage, the local DB file did not yet include the `event_sources` table even though the schema code had been merged.

The fix was to run schema initialization again against the existing SQLite DB so missing tables would be created without wiping existing data.

If this ever happens again for future schema additions, the same pattern should work provided the schema only adds missing tables or compatible changes.


