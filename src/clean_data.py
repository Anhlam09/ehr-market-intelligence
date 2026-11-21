"""
Step 3 — Clean and standardize.

Reads the newest raw snapshot and produces cleaned, typed CSVs in
data/processed/. Responsibilities:

  * de-duplicate records (by primary key)
  * standardize vendor names and normalize market-segment / role / status values
  * coerce numeric and date fields to consistent types
  * convert blank strings to proper nulls
  * flag conflicting metric observations (same vendor/segment/metric/year)

The raw snapshot is never modified.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

from common import PROCESSED, RAW, TABLES_IN_ORDER, get_logger

log = get_logger("clean")

# Canonical spellings for vendor names (normalize common variants).
VENDOR_NAME_CANON = {
    "epic": "Epic Systems",
    "epic systems": "Epic Systems",
    "cerner": "Oracle Health",
    "oracle cerner": "Oracle Health",
    "oracle health": "Oracle Health",
    "meditech": "MEDITECH",
    "athenahealth": "athenahealth",
    "athena health": "athenahealth",
    "august": "August Health",
    "august health": "August Health",
    "pointclickcare": "PointClickCare",
    "point click care": "PointClickCare",
    "matrixcare": "MatrixCare",
    "ecp": "ECP",
    "alis": "ALIS",
    "yardi": "Yardi",
}

INT_COLS = {
    "vendors": ["vendor_id", "founded_year"],
    "sources": ["source_id"],
    "market_segments": ["segment_id"],
    "product_features": ["feature_id"],
    "vendor_segments": ["vendor_id", "segment_id", "source_id"],
    "vendor_features": ["vendor_id", "feature_id", "source_id"],
    "market_metrics": ["metric_id", "vendor_id", "segment_id", "measurement_year", "source_id"],
}
NUM_COLS = {"market_metrics": ["metric_value"]}
DATE_COLS = {
    "sources": ["publication_date", "retrieval_date"],
    "vendor_features": ["verified_date"],
}
PRIMARY_KEYS = {
    "sources": ["source_id"],
    "vendors": ["vendor_id"],
    "market_segments": ["segment_id"],
    "product_features": ["feature_id"],
    "vendor_segments": ["vendor_id", "segment_id"],
    "vendor_features": ["vendor_id", "feature_id"],
    "market_metrics": ["metric_id"],
}


def _latest_snapshot() -> Path:
    pointer = json.loads((RAW / "latest.json").read_text())
    return RAW / pointer["latest"]


def _normalize_vendor_name(name: str) -> str:
    key = (name or "").strip().lower()
    return VENDOR_NAME_CANON.get(key, (name or "").strip())


def clean() -> dict[str, pd.DataFrame]:
    snap = json.loads(_latest_snapshot().read_text())
    cleaned: dict[str, pd.DataFrame] = {}

    for table in TABLES_IN_ORDER:
        df = pd.DataFrame(snap["tables"][table])

        # blanks -> NA
        df = df.replace(r"^\s*$", pd.NA, regex=True)

        # standardize vendor names
        if "vendor_name" in df.columns:
            df["vendor_name"] = df["vendor_name"].map(_normalize_vendor_name)

        # normalize categorical text
        if "market_role" in df.columns:
            df["market_role"] = df["market_role"].str.strip().str.lower()
        if "availability_status" in df.columns:
            df["availability_status"] = df["availability_status"].str.strip().str.lower()
        if "segment_name" in df.columns:
            df["segment_name"] = df["segment_name"].str.strip()

        # type coercion
        for col in INT_COLS.get(table, []):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        for col in NUM_COLS.get(table, []):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        for col in DATE_COLS.get(table, []):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

        # de-duplicate on primary key
        pk = PRIMARY_KEYS[table]
        before = len(df)
        df = df.drop_duplicates(subset=pk, keep="first").reset_index(drop=True)
        removed = before - len(df)
        if removed:
            log.warning("%s: removed %d duplicate rows", table, removed)

        # flag conflicting metric observations
        if table == "market_metrics":
            dup_keys = ["vendor_id", "segment_id", "metric_name", "measurement_year"]
            conflicts = df[df.duplicated(subset=dup_keys, keep=False)]
            if not conflicts.empty:
                log.warning("market_metrics: %d conflicting observations flagged", len(conflicts))

        cleaned[table] = df
        log.info("cleaned %-18s %d rows", table, len(df))

    _write_processed(cleaned)
    return cleaned


def _write_processed(cleaned: dict[str, pd.DataFrame]) -> None:
    for table, df in cleaned.items():
        out = PROCESSED / f"{table}.csv"
        df.to_csv(out, index=False, quoting=csv.QUOTE_MINIMAL)
    log.info("wrote %d processed CSVs to %s", len(cleaned), PROCESSED)


if __name__ == "__main__":
    clean()
