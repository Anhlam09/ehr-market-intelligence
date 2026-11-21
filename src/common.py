"""Shared helpers: paths, environment config, database connection, logging."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from dotenv import load_dotenv

# --- paths -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SEED = DATA / "seed"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
LOGS = ROOT / "logs"
SQL = ROOT / "sql"

for _d in (RAW, PROCESSED, LOGS):
    _d.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

# Tables in dependency (load) order.
TABLES_IN_ORDER = [
    "sources",
    "vendors",
    "market_segments",
    "product_features",
    "vendor_segments",
    "vendor_features",
    "market_metrics",
]


def db_dsn() -> str:
    """Build a libpq connection string from environment variables."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    return (
        f"host={os.getenv('PGHOST', 'localhost')} "
        f"port={os.getenv('PGPORT', '5432')} "
        f"dbname={os.getenv('PGDATABASE', 'ehr_market')} "
        f"user={os.getenv('PGUSER', os.getenv('USER', 'postgres'))} "
        f"password={os.getenv('PGPASSWORD', '')}"
    ).strip()


def connect() -> psycopg.Connection:
    """Open a PostgreSQL connection."""
    return psycopg.connect(db_dsn())


def get_logger(name: str) -> logging.Logger:
    """Logger that writes to both stdout and logs/pipeline.log."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")

    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    fileh = logging.FileHandler(LOGS / "pipeline.log")
    fileh.setFormatter(fmt)
    logger.addHandler(fileh)
    return logger


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def run_stamp() -> str:
    """Filesystem-safe UTC timestamp for snapshot filenames."""
    return utcnow().strftime("%Y%m%dT%H%M%SZ")
