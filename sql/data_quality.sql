-- ===========================================================================
-- Data-quality & pipeline-monitoring queries (Analysis 3: data engineering)
-- ===========================================================================

-- D1. Rows missing source references (traceability gaps).
SELECT 'vendor_segments' AS table_name, COUNT(*) AS rows_missing_source
FROM   vendor_segments WHERE source_id IS NULL
UNION ALL
SELECT 'vendor_features', COUNT(*) FROM vendor_features WHERE source_id IS NULL
UNION ALL
SELECT 'market_metrics',  COUNT(*) FROM market_metrics  WHERE source_id IS NULL;


-- D2. Source freshness: age of each source's retrieval date, oldest first.
SELECT source_name,
       source_type,
       retrieval_date,
       publication_date,
       (CURRENT_DATE - retrieval_date) AS days_since_retrieval
FROM   sources
ORDER  BY retrieval_date ASC NULLS FIRST;


-- D3. Evidence coverage per vendor (share of features with a known status).
SELECT v.vendor_name,
       COUNT(*)                                                       AS total_features,
       COUNT(*) FILTER (WHERE vf.availability_status <> 'unknown')    AS features_with_evidence,
       ROUND(100.0 * COUNT(*) FILTER (WHERE vf.availability_status <> 'unknown')
             / NULLIF(COUNT(*), 0), 1)                               AS evidence_coverage_pct
FROM   vendors v
JOIN   vendor_features vf USING (vendor_id)
GROUP  BY v.vendor_name
ORDER  BY evidence_coverage_pct ASC;


-- D4. Metrics with no reported value (known gaps we are honest about).
SELECT v.vendor_name, m.metric_name, m.measurement_year
FROM   market_metrics m
JOIN   vendors v USING (vendor_id)
WHERE  m.metric_value IS NULL;


-- D5. Latest pipeline run summary.
SELECT run_id,
       pipeline_name,
       start_time,
       end_time,
       status,
       records_processed,
       records_rejected,
       error_message
FROM   pipeline_runs
ORDER  BY start_time DESC
LIMIT  10;


-- D6. Duplicate-observation guard check (should always return 0 rows).
SELECT vendor_id, segment_id, metric_name, measurement_year, COUNT(*) AS n
FROM   market_metrics
GROUP  BY vendor_id, segment_id, metric_name, measurement_year
HAVING COUNT(*) > 1;
