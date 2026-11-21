-- ===========================================================================
-- EHR Market Intelligence — relational schema (PostgreSQL)
-- Normalized design with primary/foreign keys, indexes, and data-quality
-- constraints. Safe to run repeatedly (idempotent).
-- ===========================================================================

-- --- sources ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sources (
    source_id        INTEGER PRIMARY KEY,
    source_name      TEXT NOT NULL,
    source_url       TEXT,
    publication_date DATE,
    retrieval_date   DATE,
    source_type      TEXT NOT NULL,
    CONSTRAINT chk_source_type CHECK (
        source_type IN ('vendor_website','industry_research',
                        'government_dataset','api_documentation','other')
    )
);

-- --- vendors ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vendors (
    vendor_id    INTEGER PRIMARY KEY,
    vendor_name  TEXT NOT NULL,
    website      TEXT,
    headquarters TEXT,
    founded_year INTEGER,
    description  TEXT,
    CONSTRAINT uq_vendor_name UNIQUE (vendor_name),
    CONSTRAINT chk_founded_year CHECK (
        founded_year IS NULL OR founded_year BETWEEN 1900 AND 2100
    )
);

-- --- market_segments -------------------------------------------------------
CREATE TABLE IF NOT EXISTS market_segments (
    segment_id   INTEGER PRIMARY KEY,
    segment_name TEXT NOT NULL,
    description  TEXT,
    CONSTRAINT uq_segment_name UNIQUE (segment_name)
);

-- --- product_features ------------------------------------------------------
CREATE TABLE IF NOT EXISTS product_features (
    feature_id       INTEGER PRIMARY KEY,
    feature_name     TEXT NOT NULL,
    feature_category TEXT,
    CONSTRAINT uq_feature_name UNIQUE (feature_name)
);

-- --- vendor_segments (M:N vendors <-> segments) ----------------------------
CREATE TABLE IF NOT EXISTS vendor_segments (
    vendor_id   INTEGER NOT NULL REFERENCES vendors(vendor_id),
    segment_id  INTEGER NOT NULL REFERENCES market_segments(segment_id),
    market_role TEXT NOT NULL,
    source_id   INTEGER REFERENCES sources(source_id),
    PRIMARY KEY (vendor_id, segment_id),
    CONSTRAINT chk_market_role CHECK (market_role IN ('primary','secondary'))
);

-- --- vendor_features (M:N vendors <-> features) ----------------------------
CREATE TABLE IF NOT EXISTS vendor_features (
    vendor_id           INTEGER NOT NULL REFERENCES vendors(vendor_id),
    feature_id          INTEGER NOT NULL REFERENCES product_features(feature_id),
    availability_status TEXT NOT NULL,
    source_id           INTEGER REFERENCES sources(source_id),
    verified_date       DATE,
    PRIMARY KEY (vendor_id, feature_id),
    CONSTRAINT chk_availability CHECK (
        availability_status IN ('confirmed','absent','unknown')
    )
);

-- --- market_metrics --------------------------------------------------------
CREATE TABLE IF NOT EXISTS market_metrics (
    metric_id        INTEGER PRIMARY KEY,
    vendor_id        INTEGER NOT NULL REFERENCES vendors(vendor_id),
    segment_id       INTEGER REFERENCES market_segments(segment_id),
    metric_name      TEXT NOT NULL,
    metric_value     NUMERIC,
    metric_unit      TEXT,
    measurement_year INTEGER,
    source_id        INTEGER REFERENCES sources(source_id),
    -- prevent duplicate observations of the same metric for a vendor/segment/year
    CONSTRAINT uq_metric_observation UNIQUE (vendor_id, segment_id, metric_name, measurement_year),
    CONSTRAINT chk_measurement_year CHECK (
        measurement_year IS NULL OR measurement_year BETWEEN 1990 AND 2100
    ),
    -- market-share percentages must be 0..100 (other units are unconstrained)
    CONSTRAINT chk_share_range CHECK (
        metric_unit <> 'percent'
        OR metric_value IS NULL
        OR (metric_value >= 0 AND metric_value <= 100)
    )
);

-- --- pipeline_runs ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id            SERIAL PRIMARY KEY,
    pipeline_name     TEXT NOT NULL,
    start_time        TIMESTAMPTZ NOT NULL,
    end_time          TIMESTAMPTZ,
    status            TEXT NOT NULL,
    records_processed INTEGER DEFAULT 0,
    records_rejected  INTEGER DEFAULT 0,
    error_message     TEXT,
    CONSTRAINT chk_run_status CHECK (status IN ('running','success','failed'))
);

-- --- indexes ---------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_vendor_segments_segment ON vendor_segments(segment_id);
CREATE INDEX IF NOT EXISTS idx_vendor_features_feature ON vendor_features(feature_id);
CREATE INDEX IF NOT EXISTS idx_vendor_features_status  ON vendor_features(availability_status);
CREATE INDEX IF NOT EXISTS idx_market_metrics_vendor   ON market_metrics(vendor_id);
CREATE INDEX IF NOT EXISTS idx_market_metrics_segment  ON market_metrics(segment_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_name_time ON pipeline_runs(pipeline_name, start_time DESC);
