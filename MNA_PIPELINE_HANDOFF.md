# M&A Pipeline Handoff

## Branch / repo state

Work so far was developed on the branch:

- `daniel-bloomberg-pipeline`

This branch has already been pushed to the remote repository.

The branch currently contains the Bloomberg-based M&A ingestion and analytics pipeline up to:

- multi-deal database build
- analogue selection
- analogue comparison
- event-windowed comparison outputs

Before merging to `main`, make sure the branch is fully pushed and up to date.

---

## What has been built so far

### 1. Bloomberg connectivity and ingestion

A working Bloomberg Desktop API (`blpapi`) pipeline now exists.

It can:

- resolve the correct deal using Bloomberg M&A bulk data
- identify the `Action Id`
- query the `Action` object for deal-level terms
- load target and acquirer market data where needed
- store all of it in SQLite

### 2. Deal-term extraction

For each deal, the pipeline can now retrieve and store:

- Bloomberg deal id / action id
- announcement date
- expected completion date where available
- payment type
- cash terms per target share
- stock terms / exchange ratio
- nature of bid
- percent sought
- status
- raw Bloomberg payload JSON for traceability

### 3. Database build

A bulk-loading pipeline now reads:

- `data/pending_deals.csv`
- `data/completed_deals.csv`

and populates the SQLite database.

Current high-level database state from the latest successful run:

- `mna_events`: 144
- `Completed`: 135
- `Pending`: 9
- `prices`: 159983
- `volumes`: 159983

Payment type breakdown at that point:

- `Cash`: 62
- `Cash and Stock`: 38
- `Stock`: 33
- `Cash or Stock`: 8
- `Undisclosed`: 3

### 4. Spread-readiness check

For stock / mixed deals, spread computation needs acquirer-side data.

A readiness check showed:

- stock-or-mixed total: 71
- ready for spread: 68
- not ready: 3

This means the database is broadly good enough for spread-based analytics.

### 5. Single-deal analytics

For a given deal, the pipeline can compute:

#### Target analysis
- baseline price
- announcement-day jump
- return path from baseline
- pre-announcement average volume
- volume ratio path

#### Spread analysis
- implied deal value path
- absolute spread path
- percentage spread path

#### Event view
- compact summary combining deal metadata, target metrics, and spread metrics

### 6. Analogue selection

A first analogue engine has been built.

For a selected pending deal, it:

- filters to completed deals
- requires exact payment-type compatibility
- screens candidates through a data-quality layer
- prioritises same-sector analogues first
- uses out-of-sector analogues only as fallback
- ranks candidates using:
  - deal size similarity
  - percent sought similarity
  - nature of bid similarity

For the Norfolk / Union Pacific pending deal (`event_id = 2`), the output currently distinguishes:

- same-sector analogues
- fallback structural analogues

### 7. Analogue comparison

A comparison engine has been built on top of analogue selection.

For a selected pending deal, it computes:

- pending target return path
- pending spread path
- analogue aggregated target return path
- analogue aggregated spread path
- analogue aggregated volume ratio path
- headline comparisons such as:
  - pending announcement jump vs analogue median / mean
  - pending day-5 return vs analogue median / mean
  - pending announcement-day spread vs analogue median / mean
  - pending latest-window spread vs analogue median / mean

The comparison was later corrected to operate on a fixed event window:

- event day `-5` to `+60`

This removed meaningless long-history tails from the aggregated paths.

---

## Current interpretation of the analytics

The pipeline currently produces a meaningful result for Norfolk / Union Pacific:

- Norfolk’s target reaction is weaker than the analogue set on announcement
- Norfolk underperforms analogue median / mean by day 5
- Norfolk trades at a much wider spread than the analogue set, both on announcement and at the comparison horizon

This means the analytics layer is already producing a usable project narrative.

---

## Important design decisions already made

### A. Target-first bulk loading
Bulk loading resolves the target first, then uses:

- `MERGERS_AND_ACQUISITIONS`
- selected bulk row
- `Action Id`

to identify the correct deal.

This is the core architecture and should be preserved.

### B. Acquirer handling
For `Cash` deals, acquirer resolution is not required for spread computation.

For `Stock` and `Cash and Stock` deals, acquirer-side data matters. The loader attempts to resolve and store it, but the pipeline does not fail the whole deal if the acquirer is messy. This is why spread-readiness was checked separately.

### C. Data-quality screening
A data-quality layer was introduced before analogue selection.

It is especially important for:

- filtering out obviously bad instrument-style names
- preventing dirty rows from contaminating analogue ranking

### D. Tiered analogue logic
The analogue selector is intentionally tiered:

- Tier 1: same-sector analogues
- Tier 2: fallback structural analogues

This should remain visible in the UI, because it is analytically honest and useful.

---

## Main files that matter now

### Core Bloomberg / ingestion
- `ma_index_tracker/bloomberg_client.py`
- `ma_index_tracker/bulk_loader.py`
- `load_many_events.py`
- `create_db.py`

### Database / schema
- `ma_index_tracker/db/schema.py`
- `ma_index_tracker/db/database.py`

### Analytics
- `ma_index_tracker/analysis.py`
- `ma_index_tracker/spread_analysis.py`
- `ma_index_tracker/event_view.py`

### Analogue / comparison logic
- `ma_index_tracker/data_quality.py`
- `ma_index_tracker/analogues.py`
- `ma_index_tracker/comparison.py`

### Runner scripts
- `run_analysis.py`
- `run_spread_analysis.py`
- `run_event_view.py`
- `run_analogue_selection.py`
- `run_analogue_comparison.py`

### Temporary / diagnostic scripts
These were useful during development and can either be kept temporarily, moved into a `scripts/` folder, or deleted later:
- `quality_check_completed.py`
- `check_spread_ready.py`
- `check_bulk_db.py`
- similar one-off inspection scripts

---

## What is still missing

### 1. UI / presentation layer
This is the next major block.

Recommended architecture:

- Python backend API, likely FastAPI
- React / Next.js frontend dashboard

Recommended first API endpoints:

- `GET /pending-deals`
- `GET /deal/{event_id}`
- `GET /deal/{event_id}/analogues`
- `GET /deal/{event_id}/comparison`

Recommended first UI layout:

- left sidebar: pending deals
- main panel: selected deal metadata
- top analogue list
- headline comparison cards
- charts / tables for:
  - target return path
  - spread path
  - volume ratio path

### 2. Holders block
This has not yet been built.

Anyone working on holders should align with the existing DB patterns and avoid changing the existing event / company keys casually.

### 3. News / web scraping block
This has not yet been built.

Anyone working on news integration should make sure they connect their work to the existing `event_id` / company structure rather than creating inconsistent parallel identifiers.

---

## Guidance for teammates

### If continuing analytics / UI
Do **not** rewrite the ingestion logic unless something is clearly broken.

The current ingestion and analytics pipeline is already functional and should be treated as the canonical base.

### If working on holders
Likely add new tables / modules, but preserve:

- `companies`
- `mna_events`
- the existing event ids
- the Bloomberg deal id linkage

### If working on news integration
Use the existing deal metadata to anchor articles / summaries:
- target company
- acquirer company
- announcement date
- event id

Avoid introducing a separate incompatible notion of a deal key.

---

## Recommended next steps after merge to main

1. Freeze the analytics state now by merging this branch into `main`.
2. Let teammates branch off from updated `main`.
3. Continue next with the API / UI layer.
4. Keep holders and news as separate workstreams built on top of the same DB foundation.

---

## Git merge guidance for this branch

### On your machine

Make sure all your work on the feature branch is committed and pushed:

```bash
git checkout daniel-bloomberg-pipeline
git status
git push
```

Then switch to main and update it:

```bash
git checkout main
git pull origin main
```

Then merge your branch into local main:

```bash
git merge daniel-bloomberg-pipeline
```

If there are no conflicts, push main:

```bash
git push origin main
```

### If there are conflicts
Git will tell you which files conflict.

Then:
1. open each conflicted file
2. resolve the conflict manually
3. save the file
4. run:

```bash
git add <file>
```

for each resolved file, then:

```bash
git commit
git push origin main
```

---

## Notes about GitHub visibility

If you cannot find the repository under your own GitHub profile, that usually means the repository is **not owned by your personal account**.

Common reasons:

- it belongs to another person’s account
- it belongs to an organisation
- you are a collaborator, but not the owner

That is why it may not appear under your own repositories list in the way you expect.

In practice, the easiest way to access it is:
- open the repo URL directly
- or look at `git remote -v` locally to see the exact remote URL

Example:

```bash
git remote -v
```

This shows the GitHub remote linked to your clone.

---

## Safe checkpoint

Before merging to main, it is sensible to keep this branch as a permanent milestone branch:

- `daniel-bloomberg-pipeline`

That way, even after merge, you still retain the full branch history for reference.
