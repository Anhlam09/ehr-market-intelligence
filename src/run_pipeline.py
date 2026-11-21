"""
ETL orchestrator: collect -> clean -> validate -> load, with run tracking.

Records one row in pipeline_runs per execution (start/end time, status, counts,
error message). Re-runnable: upserts guarantee reruns do not duplicate data.

    python src/run_pipeline.py
"""
from __future__ import annotations

import sys

import collect_data
import clean_data
import validate_data
import load_database
from common import connect, get_logger, utcnow

log = get_logger("pipeline")
PIPELINE_NAME = "ehr_etl"


def _start_run(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pipeline_runs (pipeline_name, start_time, status) "
            "VALUES (%s, %s, 'running') RETURNING run_id",
            (PIPELINE_NAME, utcnow()),
        )
        run_id = cur.fetchone()[0]
    conn.commit()
    return run_id


def _finish_run(conn, run_id, status, processed=0, rejected=0, error=None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE pipeline_runs SET end_time=%s, status=%s, records_processed=%s, "
            "records_rejected=%s, error_message=%s WHERE run_id=%s",
            (utcnow(), status, processed, rejected, error, run_id),
        )
    conn.commit()


def _ensure_schema() -> None:
    with connect() as conn:
        load_database.create_schema(conn)


def main() -> int:
    _ensure_schema()
    with connect() as conn:
        run_id = _start_run(conn)
        log.info("pipeline run #%d started", run_id)
        try:
            collect_data.collect()
            clean_data.clean()
            report = validate_data.validate()
            if not report.ok:
                _finish_run(conn, run_id, "failed", rejected=len(report.errors),
                            error="; ".join(report.errors))
                log.error("pipeline run #%d FAILED validation", run_id)
                return 1
            processed = load_database.load()
            _finish_run(conn, run_id, "success", processed=processed,
                        rejected=len(report.warnings))
            log.info("pipeline run #%d SUCCESS (%d rows)", run_id, processed)
            return 0
        except Exception as exc:  # noqa: BLE001
            _finish_run(conn, run_id, "failed", error=str(exc))
            log.exception("pipeline run #%d crashed", run_id)
            return 1


if __name__ == "__main__":
    sys.exit(main())
