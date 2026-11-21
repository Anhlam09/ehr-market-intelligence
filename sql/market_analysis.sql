-- ===========================================================================
-- Market analysis queries (Analysis 1: full EHR market)
-- Each query is self-contained and documented.
-- ===========================================================================

-- Q1. Count of vendors by market segment (primary vs secondary role).
--     Shows how crowded each healthcare segment is.
SELECT s.segment_name,
       COUNT(*)                                             AS vendors_total,
       COUNT(*) FILTER (WHERE vs.market_role = 'primary')   AS primary_vendors,
       COUNT(*) FILTER (WHERE vs.market_role = 'secondary') AS secondary_vendors
FROM   market_segments s
JOIN   vendor_segments vs USING (segment_id)
GROUP  BY s.segment_name
ORDER  BY vendors_total DESC;


-- Q2. Acute-care hospital EHR market share, ranked, with cumulative concentration.
--     IMPORTANT: hospital share only; do NOT compare to senior-living counts.
SELECT v.vendor_name,
       m.metric_value                                            AS market_share_pct,
       m.measurement_year,
       src.source_name,
       SUM(m.metric_value) OVER (ORDER BY m.metric_value DESC)   AS cumulative_pct
FROM   market_metrics m
JOIN   vendors v          USING (vendor_id)
JOIN   sources src        USING (source_id)
WHERE  m.metric_name = 'acute_care_ehr_market_share'
  AND  m.metric_unit = 'percent'
ORDER  BY m.metric_value DESC;


-- Q3. Market concentration (HHI-style sum of squared shares) for a segment.
--     Reported shares only; remaining market is "all other / unmeasured".
SELECT m.measurement_year,
       ROUND(SUM(m.metric_value), 1)                   AS covered_share_pct,
       ROUND(100 - SUM(m.metric_value), 1)             AS unmeasured_share_pct,
       ROUND(SUM(POWER(m.metric_value, 2)) / 100.0, 1) AS top_vendor_hhi_contribution
FROM   market_metrics m
WHERE  m.metric_name = 'acute_care_ehr_market_share'
GROUP  BY m.measurement_year;


-- Q4. Vendor market-coverage matrix: how many segments each vendor serves.
SELECT v.vendor_name,
       COUNT(vs.segment_id)                                       AS segments_served,
       STRING_AGG(ms.segment_name, ', ' ORDER BY ms.segment_name) AS segments
FROM   vendors v
LEFT   JOIN vendor_segments vs USING (vendor_id)
LEFT   JOIN market_segments ms USING (segment_id)
GROUP  BY v.vendor_name
ORDER  BY segments_served DESC, v.vendor_name;


-- Q5. Product coverage: confirmed feature count per vendor (evidence-based).
--     'unknown' statuses are excluded (absence of evidence != evidence of absence).
SELECT v.vendor_name,
       COUNT(*) FILTER (WHERE vf.availability_status = 'confirmed') AS confirmed_features,
       COUNT(*) FILTER (WHERE vf.availability_status = 'unknown')   AS unknown_features,
       ROUND(100.0 * COUNT(*) FILTER (WHERE vf.availability_status = 'confirmed')
             / NULLIF(COUNT(*), 0), 1)                             AS confirmed_pct
FROM   vendors v
JOIN   vendor_features vf USING (vendor_id)
GROUP  BY v.vendor_name
ORDER  BY confirmed_features DESC;


-- Q6. Feature prevalence across the market (which capabilities are common vs rare).
SELECT pf.feature_name,
       pf.feature_category,
       COUNT(*) FILTER (WHERE vf.availability_status = 'confirmed') AS vendors_with_feature
FROM   product_features pf
JOIN   vendor_features vf USING (feature_id)
GROUP  BY pf.feature_name, pf.feature_category
ORDER  BY vendors_with_feature DESC, pf.feature_name;
