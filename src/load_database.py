"""
Step 4/6 — Load records into PostgreSQL.

Creates the schema (idempotent) and upserts the processed CSVs. Upserts make the
pipeline safe to re-run: existing rows are updated in place, new rows inserted,
and no duplicates are created. NULL-safe type handling converts pandas NA to
SQL NULL.
"""
from __future__ import annotations

import math

import pandas as pd

from common import PROCESSED, SQL, TABLES_IN_ORDER, connect, get_logger

log = get_logger("load")

# Conflict target (primary key) per table for ON CONFLICT upserts.
CONFLICT_KEYS = {
    "sources": ["source_id"],
    "vendors": ["vendor_id"],
    "market_segments": ["segment_id"],
    "product_features": ["feature_id"],
    "vendor_segments": ["vendor_id", "segment_id"],
    "vendor_features": ["vendor_id", "feature_id"],
    "market_metrics": ["metric_id"],
}


def create_schema(conn) -> None:
    ddl = (SQL / "create_tables.sql").read_text()
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()
    log.info("schema ensured")


def _clean_value(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if v is pd.NA:
        return None
    return v


def _upsert(conn, table: str, df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    cols = list(df.columns)
    keys = CONFLICT_KEYS[table]
    updates = [c for c in cols if c not in keys]
    collist = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    conflict = ", ".join(keys)
    if updates:
        set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in updates)
        on_conflict = f"DO UPDATE SET {set_clause}"
    else:
        on_conflict = "DO NOTHING"

    sql = (
        f"INSERT INTO {table} ({collist}) VALUES ({placeholders}) "
        f"ON CONFLICT ({conflict}) {on_conflict}"
    )
    rows = [tuple(_clean_value(v) for v in rec) for rec in df.itertuples(index=False, name=None)]
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    return len(rows)


def load() -> int:
    total = 0
    with connect() as conn:
        create_schema(conn)
        for table in TABLES_IN_ORDER:
            df = pd.read_csv(PROCESSED / f"{table}.csv")
            df = df.astype(object).where(pd.notna(df), None)
            n = _upsert(conn, table, df)
            total += n
            log.info("upserted %-18s %d rows", table, n)
        conn.commit()
    log.info("load complete: %d rows upserted", total)
    return total


if __name__ == "__main__":
    load()
