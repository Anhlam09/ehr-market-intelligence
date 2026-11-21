"""
Step 4 — Validate required information before loading.

Runs rule-based checks over the processed CSVs and returns a structured report.
Checks are split into:
  * errors   -> block the load (data integrity violations)
  * warnings -> allow the load but surface on the dashboard (quality signals)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from common import PROCESSED, get_logger

log = get_logger("validate")


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def _load(table: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED / f"{table}.csv")


def validate() -> ValidationReport:
    r = ValidationReport()
    t = {name: _load(name) for name in (
        "sources", "vendors", "market_segments", "product_features",
        "vendor_segments", "vendor_features", "market_metrics",
    )}

    # --- vendors ---
    v = t["vendors"]
    if v["vendor_name"].isna().any():
        r.errors.append("vendors: vendor_name contains nulls")
    if v["vendor_id"].duplicated().any():
        r.errors.append("vendors: vendor_id is not unique")
    if v["vendor_name"].str.strip().str.lower().duplicated().any():
        r.errors.append("vendors: duplicate vendor names after standardization")
    bad_year = v["founded_year"].dropna()
    if ((bad_year < 1900) | (bad_year > 2100)).any():
        r.errors.append("vendors: founded_year out of range")

    # --- unique PKs on reference tables ---
    for name, pk in [("sources", "source_id"), ("market_segments", "segment_id"),
                     ("product_features", "feature_id"), ("market_metrics", "metric_id")]:
        if t[name][pk].duplicated().any():
            r.errors.append(f"{name}: {pk} is not unique")

    # --- foreign key integrity ---
    vendor_ids = set(v["vendor_id"])
    segment_ids = set(t["market_segments"]["segment_id"])
    feature_ids = set(t["product_features"]["feature_id"])
    source_ids = set(t["sources"]["source_id"])

    def _fk(table, col, valid, label):
        bad = set(t[table][col].dropna()) - valid
        if bad:
            r.errors.append(f"{table}.{col} has invalid {label}: {sorted(bad)}")

    _fk("vendor_segments", "vendor_id", vendor_ids, "vendor_id")
    _fk("vendor_segments", "segment_id", segment_ids, "segment_id")
    _fk("vendor_features", "vendor_id", vendor_ids, "vendor_id")
    _fk("vendor_features", "feature_id", feature_ids, "feature_id")
    _fk("market_metrics", "vendor_id", vendor_ids, "vendor_id")
    _fk("market_metrics", "segment_id", segment_ids, "segment_id")
    for tbl in ("vendor_segments", "vendor_features", "market_metrics"):
        _fk(tbl, "source_id", source_ids, "source_id")

    # --- market share range (percent metrics must be 0..100) ---
    mm = t["market_metrics"]
    pct = mm[mm["metric_unit"] == "percent"]["metric_value"].dropna()
    if ((pct < 0) | (pct > 100)).any():
        r.errors.append("market_metrics: percent value outside 0..100")

    # --- measurement year reasonable ---
    yr = mm["measurement_year"].dropna()
    if ((yr < 1990) | (yr > 2100)).any():
        r.errors.append("market_metrics: measurement_year out of range")

    # --- enumerations ---
    if not set(t["vendor_segments"]["market_role"].dropna()).issubset({"primary", "secondary"}):
        r.errors.append("vendor_segments: invalid market_role value")
    if not set(t["vendor_features"]["availability_status"].dropna()).issubset({"confirmed", "absent", "unknown"}):
        r.errors.append("vendor_features: invalid availability_status value")

    # --- duplicate metric observations ---
    dup_keys = ["vendor_id", "segment_id", "metric_name", "measurement_year"]
    if mm.duplicated(subset=dup_keys).any():
        r.errors.append("market_metrics: duplicate observations for vendor/segment/metric/year")

    # --- warnings (quality, non-blocking) ---
    no_source = t["vendor_features"]["source_id"].isna().sum()
    if no_source:
        r.warnings.append(f"vendor_features: {no_source} rows missing source_id")
    unknown = (t["vendor_features"]["availability_status"] == "unknown").sum()
    r.warnings.append(f"vendor_features: {unknown} feature statuses are 'unknown' (no evidence found)")
    missing_metric_val = mm["metric_value"].isna().sum()
    if missing_metric_val:
        r.warnings.append(f"market_metrics: {missing_metric_val} metrics have no reported value")

    r.stats = {
        "vendors": len(v),
        "segments": len(t["market_segments"]),
        "features": len(t["product_features"]),
        "vendor_feature_rows": len(t["vendor_features"]),
        "metrics": len(mm),
        "sources": len(t["sources"]),
    }

    for e in r.errors:
        log.error("VALIDATION ERROR: %s", e)
    for w in r.warnings:
        log.warning("validation warning: %s", w)
    log.info("validation %s (%d errors, %d warnings)",
             "PASSED" if r.ok else "FAILED", len(r.errors), len(r.warnings))
    return r


if __name__ == "__main__":
    rep = validate()
    raise SystemExit(0 if rep.ok else 1)
