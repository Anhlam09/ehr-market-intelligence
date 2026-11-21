-- ===========================================================================
-- Competitor analysis queries (Analysis 2: August Health & senior living)
-- ===========================================================================

-- C1. Shared market segments between August Health and every other vendor
--     (customer-segment overlap, the heaviest-weighted dimension).
WITH focus AS (
    SELECT segment_id FROM vendor_segments vs
    JOIN vendors v USING (vendor_id)
    WHERE v.vendor_name = 'August Health'
)
SELECT v.vendor_name,
       COUNT(*) FILTER (WHERE vs.segment_id IN (SELECT segment_id FROM focus)) AS shared_segments,
       STRING_AGG(ms.segment_name, ', ' ORDER BY ms.segment_name)
            FILTER (WHERE vs.segment_id IN (SELECT segment_id FROM focus))     AS shared_segment_names
FROM   vendors v
JOIN   vendor_segments vs USING (vendor_id)
JOIN   market_segments ms USING (segment_id)
WHERE  v.vendor_name <> 'August Health'
GROUP  BY v.vendor_name
ORDER  BY shared_segments DESC, v.vendor_name;


-- C2. Side-by-side confirmed-feature comparison for any two vendors.
--     Change the two names below to compare e.g. August Health vs Epic Systems.
SELECT pf.feature_name,
       pf.feature_category,
       MAX(CASE WHEN v.vendor_name = 'August Health' THEN vf.availability_status END) AS august_health,
       MAX(CASE WHEN v.vendor_name = 'Epic Systems'  THEN vf.availability_status END) AS epic_systems
FROM   product_features pf
LEFT   JOIN vendor_features vf USING (feature_id)
LEFT   JOIN vendors v USING (vendor_id)
WHERE  v.vendor_name IN ('August Health', 'Epic Systems')
GROUP  BY pf.feature_name, pf.feature_category
ORDER  BY pf.feature_category, pf.feature_name;


-- C3. Count of jointly-confirmed features between August Health and each vendor
--     (feature-similarity numerator; evidence-based only).
WITH focus AS (
    SELECT feature_id FROM vendor_features vf
    JOIN vendors v USING (vendor_id)
    WHERE v.vendor_name = 'August Health' AND vf.availability_status = 'confirmed'
)
SELECT v.vendor_name,
       COUNT(*) AS jointly_confirmed_features
FROM   vendors v
JOIN   vendor_features vf USING (vendor_id)
WHERE  v.vendor_name <> 'August Health'
  AND  vf.availability_status = 'confirmed'
  AND  vf.feature_id IN (SELECT feature_id FROM focus)
GROUP  BY v.vendor_name
ORDER  BY jointly_confirmed_features DESC;


-- C4. Senior-living reported footprint (self-reported counts; NOT market share).
--     Kept separate from hospital share by design.
SELECT v.vendor_name,
       m.metric_name,
       m.metric_value,
       m.metric_unit,
       m.measurement_year,
       src.source_name
FROM   market_metrics m
JOIN   vendors v   USING (vendor_id)
JOIN   sources src USING (source_id)
WHERE  m.metric_name IN ('reported_customer_facilities', 'reported_customer_communities')
ORDER  BY m.metric_value DESC NULLS LAST;


-- C5. Evidence trail: sources backing August Health's confirmed features.
SELECT pf.feature_name,
       vf.availability_status,
       vf.verified_date,
       src.source_name,
       src.source_url
FROM   vendor_features vf
JOIN   vendors v          USING (vendor_id)
JOIN   product_features pf USING (feature_id)
LEFT   JOIN sources src    USING (source_id)
WHERE  v.vendor_name = 'August Health'
ORDER  BY vf.availability_status, pf.feature_name;
