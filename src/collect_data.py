"""
Step 1 — Collect data.

Reads the curated, source-backed seed dataset and writes immutable, timestamped
raw snapshots to data/raw/ (the "original responses"). Each snapshot records the
retrieval timestamp so downstream steps and the dashboard can report freshness.

The seed CSVs are the collected source of truth for the MVP. A thin, optional
website-fetch helper (requests + BeautifulSoup) is included to show the live
collection pattern; it is NOT called by the pipeline and should only be used
where a site's terms permit.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from common import RAW, SEED, TABLES_IN_ORDER, get_logger, run_stamp, utcnow

log = get_logger("collect")


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def collect() -> Path:
    """Snapshot every seed table into a single timestamped raw JSON file."""
    stamp = run_stamp()
    snapshot = {
        "retrieved_at": utcnow().isoformat(),
        "snapshot_id": stamp,
        "origin": "curated_seed_dataset",
        "tables": {},
    }
    total = 0
    for table in TABLES_IN_ORDER:
        rows = _read_csv(SEED / f"{table}.csv")
        snapshot["tables"][table] = rows
        total += len(rows)
        log.info("collected %-18s %d rows", table, len(rows))

    out = RAW / f"snapshot_{stamp}.json"
    out.write_text(json.dumps(snapshot, indent=2))
    # keep a stable pointer to the newest snapshot
    (RAW / "latest.json").write_text(json.dumps({"latest": out.name}, indent=2))
    log.info("wrote raw snapshot %s (%d total rows)", out.name, total)
    return out


# --- optional live-fetch helper (demonstration only) -----------------------
def fetch_page_title(url: str, timeout: int = 15) -> str | None:
    """Fetch a page and return its <title>. Use only where permitted."""
    import requests
    from bs4 import BeautifulSoup

    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "ehr-market-intel/1.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    return soup.title.string.strip() if soup.title and soup.title.string else None


if __name__ == "__main__":
    collect()
