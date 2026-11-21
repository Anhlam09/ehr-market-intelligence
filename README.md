# EHR Market Intelligence & Competitive Analysis Platform

An end-to-end data engineering and analytics platform that collects, cleans,
validates, stores, and analyzes information about Electronic Health Record (EHR)
vendors across healthcare markets — with a focused competitive analysis of
**August Health** and its senior-living competitors.

The data engineering (ETL pipeline, PostgreSQL schema, validation, data-quality
monitoring) is the foundation; the EHR competitive analysis is the application.

## Dashboard preview

**Competitive Intelligence** — side-by-side feature comparison, segment overlap, and the transparent similarity score:

![Competitive Intelligence page](docs/images/02_competitive_intelligence.png)

**EHR Market Overview** — vendor coverage, hospital market share, and senior-living footprint (kept separate by design):

![Market Overview page](docs/images/01_market_overview.png)

**Data Engineering Monitor** — pipeline runs, source freshness, evidence coverage, and traceability gaps:

![Data Engineering Monitor page](docs/images/03_data_engineering_monitor.png)

---

## What this demonstrates

- **Python ETL** — modular collect → clean → validate → load pipeline with logging and run tracking
- **PostgreSQL** — normalized schema, primary/foreign keys, constraints, indexes, idempotent **upserts**
- **Data cleaning & validation** — pandas standardization + rule-based blocking/non-blocking checks
- **SQL analytics** — market concentration, feature coverage, competitor overlap, data-quality monitoring
- **Transparent modeling** — a weighted, evidence-based competitor overlap score (no black-box ML)
- **Dashboard** — a 3-page Streamlit + Plotly app
- **Testing & CI** — pytest data-quality suite + GitHub Actions
- **Honest data practices** — every fact is source-tagged; unknowns are kept as *unknown*, never invented

---

## Architecture

```
seed CSVs ──► collect_data ──► data/raw/*.json ──► clean_data ──► data/processed/*.csv
                (snapshot)        (immutable)       (pandas)         (typed, deduped)
                                                                           │
                                                                           ▼
   Streamlit dashboard ◄── PostgreSQL ◄── load_database ◄── validate_data
      (3 pages)            (8 tables)        (upsert)      (blocking + warnings)
                                                 ▲
                                          run_pipeline (orchestrator + pipeline_runs tracking)
```

---

## Database schema (8 tables)

| Table | Purpose |
|---|---|
| `vendors` | Company profile (name, website, HQ, founded year, description) |
| `market_segments` | Healthcare segments (acute care, ambulatory, assisted living, memory care, skilled nursing, long-term care) |
| `product_features` | Standardized capabilities (charting, billing, meds, scheduling, reporting, compliance, pharmacy, API, export, FHIR) |
| `vendor_segments` | M:N vendor ↔ segment with `market_role` (primary/secondary) + source |
| `vendor_features` | M:N vendor ↔ feature with `availability_status` (confirmed/absent/unknown) + source + verified date |
| `market_metrics` | Market share / footprint observations, unit- and year-tagged, with a uniqueness guard |
| `sources` | Source references (URL, publication date, retrieval date, type) |
| `pipeline_runs` | Execution log (status, counts, errors) for monitoring |

Full DDL with constraints and indexes: [`sql/create_tables.sql`](sql/create_tables.sql).

---

## Setup

Requires Python 3.11+ and PostgreSQL 13+.

```bash
# 1. create the database
createdb ehr_market

# 2. python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. configure connection
cp .env.example .env        # edit PGUSER / PGPASSWORD etc. as needed
```

## Run the pipeline

```bash
python src/run_pipeline.py        # collect → clean → validate → load (idempotent)
python src/analyze_competitors.py # competitor overlap scoring (prints ranking)
pytest -q                         # data-quality tests
streamlit run dashboard/app.py    # open the dashboard
```

Re-running `run_pipeline.py` is safe — upserts and the uniqueness constraints
guarantee no duplicated rows.

---

## The competitor overlap model

A **transparent, weighted, evidence-based** score (0–100) between a focus vendor
(default August Health) and every other vendor. Each dimension is a Jaccard
similarity between the two vendors' relevant sets:

| Dimension | Weight | Based on |
|---|---|---|
| Customer segment similarity | 40% | shared `vendor_segments` |
| Product feature similarity | 35% | jointly **confirmed** features |
| Workflow similarity | 15% | confirmed charting / meds / scheduling |
| Integration / use-case similarity | 10% | confirmed pharmacy / API / export / FHIR |

**Classification:** High ≥ 70 · Moderate 40–69 · Low < 40 · *Insufficient evidence*
when either vendor's evidence coverage is below threshold.

Key principle: `unknown` means *no public evidence found*, and is treated as
**missing — not as absence**. The weights are stated assumptions meant to be tested.

Example result (August Health vs others): senior-living vendors (ECP, ALIS, Yardi,
PointClickCare, MatrixCare) rank as the closest competitors; Epic and Oracle Health
rank **low overlap** — a different market, reached by evidence rather than assumption.

---

## Dashboard pages

1. **EHR Market Overview** — vendor counts, segment filters, coverage, hospital
   market-share chart, senior-living footprint (kept separate by design).
2. **Competitive Intelligence** — pick any two vendors for a side-by-side feature
   comparison, segment overlap, similarity score, and source-linked evidence.
3. **Data Engineering Monitor** — latest pipeline run, run history, source
   freshness, evidence coverage, traceability gaps, and known value gaps.

---

## Methodology & limitations (read before citing figures)

- **Do not compare hospital market share with senior-living counts.** They use
  different populations and measurement methods; the dashboard keeps them apart.
- **Market-share and footprint values are stored "as reported"** and tagged by
  `source_type`. Vendor self-reported counts are labeled as such. Re-verify
  against the cited source before using any figure externally.
- **Missing data is never treated as a zero or a "no".** It is `unknown` /
  `NULL` and surfaced on the monitor page.
- The seed dataset is a curated, source-backed MVP snapshot (see `data/seed/`).
  Phase 5 (automation, live collection, AI-assisted extraction) is future work;
  the collection pattern is scaffolded in `src/collect_data.py`.

---

## Project layout

```
ehr-market-intelligence/
├── data/{raw,processed,seed}/   # raw snapshots, cleaned CSVs, curated seed
├── src/                         # common, collect, clean, validate, load, run_pipeline, analyze_competitors
├── sql/                         # create_tables, market_analysis, competitor_analysis, data_quality
├── dashboard/app.py             # 3-page Streamlit app
├── tests/test_data_quality.py   # pytest invariants + idempotency
├── .github/workflows/ci.yml     # pipeline + tests on PostgreSQL service
├── requirements.txt · .env.example · .gitignore
```
