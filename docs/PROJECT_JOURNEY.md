# Project Journey — how I built this and why

My own notes on the decisions I made building the EHR Market Intelligence platform,
the reasoning behind each one, and the things I want to be able to explain. Written
in plain language so I can re-read it before talking about the project.

---

## The one-sentence story

> I built an end-to-end data platform that collects, cleans, validates, stores
> (PostgreSQL), analyzes (SQL), and visualizes (Streamlit) information about EHR
> vendors — and I treated **data engineering and data integrity as the hard part**,
> not the charts.

---

## Decisions I made, and why

### 1. Database: local PostgreSQL (not Docker, not SQLite)
**Why:** PostgreSQL was already installed on my machine, so it was the fastest path
to a real relational database. Docker would add reproducibility but also friction
every time I run it; SQLite would be more portable but wouldn't show off real
PostgreSQL features (constraints, upserts, window functions).
**What I'd say in an interview:** "I picked the tool that let me demonstrate real
PostgreSQL skills with the least setup overhead, and I kept the connection config
in `.env` so it's still portable."

### 2. Data source: a curated, source-backed seed dataset (not live scraping)
**Why:** Live scraping 10 vendor sites would be fragile, uneven, and some sites
block it. A hand-curated dataset where **every fact is tied to a source URL and a
date** is more honest and more reliable for an MVP. I still scaffolded the live-
collection pattern (`requests` + `BeautifulSoup`) to show I know how.
**What I'd say:** "I separated the *collection pattern* from the *data*. The pipeline
is real; the data is curated and fully sourced, which is the honest thing to do when
live scraping isn't dependable."

### 3. Scope: full MVP end-to-end
**Why:** A portfolio piece needs to actually *work* front to back — schema, ETL,
validation, SQL, scoring model, dashboard, tests. Half a system doesn't prove much.

### 4. I considered training a model on Modal — then decided against it
**Why this matters:** I had a Modal account and wondered if the project needed GPU
model training. I reasoned through it: the competitive "overlap score" is a
**transparent weighted formula**, not a trained model. The brief even said "don't
start with ML." So adding Modal would mean cost and complexity for zero benefit.
**What I'd say:** "I can tell when *not* to reach for heavy tooling. The scoring is
deliberate arithmetic I can explain and defend — a black-box model would be worse
here, not better."

### 5. I kept the whole thing as my own work
No external assistant branding anywhere. The repo reads as mine.

---

## Design principles I committed to (and can defend)

- **`unknown` is not the same as `absent`.** If I found no public evidence that a
  vendor has a feature, I recorded it as `unknown`, *not* as "they don't have it."
  Treating missing data as a "no" would fabricate conclusions.
- **Never compare hospital market share to senior-living counts.** They use
  different populations and measurement methods. The dashboard keeps them on
  separate panels on purpose.
- **Don't invent numbers.** When I couldn't verify a figure, I left it NULL.
- **Idempotency.** The pipeline uses upserts + unique constraints so re-running it
  never duplicates data. I proved this by running it multiple times and checking
  row counts stayed stable.
- **Traceability.** Every metric and feature points back to a row in `sources`
  with a URL and dates.

---

## The moment I'm most proud of (the MatrixCare call)

My first draft said MatrixCare served **15,000 facilities**. When I went to verify
it, their site only said *"thousands of... organizations"* — no specific number.
So I **changed the value to NULL** rather than keep a number I couldn't back up.

Meanwhile I *was* able to verify PointClickCare's "27,000+ LTPAC facilities" — not
from an aggregator (those blocked me with HTTP 403), but from **PointClickCare's own
CEO blog**. And I confirmed athenahealth's 160,000 clinicians, and corrected Oracle
(21.8% → 23.4%) and MEDITECH (13.9% → 16.0%) to the real KLAS 2023 figures.

**Why this is the best talking point:** It shows judgment. A data engineer's value
isn't just moving data — it's knowing which numbers to trust, downgrading the ones
you can't verify, and being transparent about the gaps.

---

## The order I worked in (and why order mattered)

1. **Build the backbone** — schema, seed, ETL, validation, load.
2. **Verify the data against real sources** — *before* anything downstream.
3. **Regenerate** everything from the corrected source of truth.
4. **Screenshot** the dashboard — only *after* the data was final.
5. **Publish** to GitHub last, so the first public commit was already clean.

**Key habit:** I edited the **seed generator** (the source of truth), never the
generated CSVs by hand, then regenerated. Fix data at the source; let everything
downstream rebuild.

---

## What I'd do next (honest roadmap)

- Add a "data sources & confidence" table so each figure shows its confidence level.
- Verify the remaining feature statuses that are still `unknown`.
- Phase 5: schedule periodic collection, detect changed vendor info, track history,
  and (optionally) use an LLM *API* to help extract facts from vendor PDFs — still
  no model training needed.

---

## 30-second pitch (for when someone asks "tell me about this project")

"It's an EHR market-intelligence platform. A Python ETL pipeline collects and
cleans vendor data, validates it, and loads it into a normalized PostgreSQL
database with constraints and idempotent upserts. SQL queries analyze market
concentration and a transparent, weighted competitor-overlap model, and a
three-page Streamlit dashboard visualizes it with full source traceability. The
interesting result: August Health's real competitors are senior-living vendors,
not Epic — and I reached that from evidence, not assumption. The part I care most
about is data integrity: unverifiable numbers are stored as NULL, and 'unknown'
is never treated as 'absent.'"
