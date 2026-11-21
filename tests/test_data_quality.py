"""
Data-quality tests (pytest). Run after a pipeline execution:

    pytest -q

These assert the invariants from the project spec directly against PostgreSQL,
plus a rerun-idempotency check.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from common import connect  # noqa: E402
import run_pipeline  # noqa: E402


def _scalar(sql):
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchone()[0]


def test_vendor_names_not_null():
    assert _scalar("SELECT COUNT(*) FROM vendors WHERE vendor_name IS NULL") == 0


def test_vendor_ids_unique():
    assert _scalar("SELECT COUNT(*) FROM (SELECT vendor_id FROM vendors GROUP BY vendor_id HAVING COUNT(*)>1) t") == 0


def test_foreign_keys_valid():
    # vendor_segments and vendor_features must reference existing vendors/segments/features
    assert _scalar("""
        SELECT COUNT(*) FROM vendor_segments vs
        LEFT JOIN vendors v USING (vendor_id) WHERE v.vendor_id IS NULL
    """) == 0
    assert _scalar("""
        SELECT COUNT(*) FROM vendor_features vf
        LEFT JOIN product_features pf USING (feature_id) WHERE pf.feature_id IS NULL
    """) == 0


def test_market_share_in_range():
    assert _scalar("""
        SELECT COUNT(*) FROM market_metrics
        WHERE metric_unit = 'percent'
          AND metric_value IS NOT NULL
          AND (metric_value < 0 OR metric_value > 100)
    """) == 0


def test_measurement_years_reasonable():
    assert _scalar("""
        SELECT COUNT(*) FROM market_metrics
        WHERE measurement_year IS NOT NULL
          AND (measurement_year < 1990 OR measurement_year > 2100)
    """) == 0


def test_no_duplicate_metric_observations():
    assert _scalar("""
        SELECT COUNT(*) FROM (
            SELECT vendor_id, segment_id, metric_name, measurement_year
            FROM market_metrics
            GROUP BY vendor_id, segment_id, metric_name, measurement_year
            HAVING COUNT(*) > 1
        ) t
    """) == 0


def test_availability_status_enum():
    assert _scalar("""
        SELECT COUNT(*) FROM vendor_features
        WHERE availability_status NOT IN ('confirmed','absent','unknown')
    """) == 0


def test_rerun_is_idempotent():
    before = _scalar("SELECT COUNT(*) FROM vendor_features")
    rc = run_pipeline.main()
    assert rc == 0
    after = _scalar("SELECT COUNT(*) FROM vendor_features")
    assert before == after, "pipeline rerun changed row count (not idempotent)"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
