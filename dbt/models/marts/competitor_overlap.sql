-- Mart: transparent weighted competitor-overlap score vs a focus vendor.
-- SQL re-implementation of src/analyze_competitors.py (kept in sync).
--   segment 40% + feature 35% + workflow 15% + integration 10%
-- Each dimension is a Jaccard similarity; feature dims use CONFIRMED features only.
-- 'unknown' = missing evidence, never treated as absence.
{% set focus = var('focus_vendor', 'August Health') %}

with
vf  as (select * from {{ ref('stg_vendor_features') }}),
vs  as (select * from {{ ref('stg_vendor_segments') }}),
v   as (select * from {{ ref('stg_vendors') }}),

focus_id as (select vendor_id from v where vendor_name = '{{ focus }}'),

-- ---- segment Jaccard inputs ----
focus_seg as (
    select segment_id from vs where vendor_id = (select vendor_id from focus_id)
),
focus_seg_n as (select count(*) as n from focus_seg),
seg_stats as (
    select
        vs.vendor_id,
        count(distinct vs.segment_id)                                              as comp_seg,
        count(distinct case when fs.segment_id is not null then vs.segment_id end) as inter_seg
    from vs
    left join focus_seg fs on vs.segment_id = fs.segment_id
    group by vs.vendor_id
),

-- ---- confirmed-feature Jaccard inputs ----
conf as (
    select vendor_id, feature_id, feature_name
    from vf where availability_status = 'confirmed'
),
focus_conf as (
    select feature_id, feature_name
    from conf where vendor_id = (select vendor_id from focus_id)
),
{% set workflow = "('Clinical charting','Medication management','Scheduling')" %}
{% set integ = "('Pharmacy integrations','API access','Data export','FHIR support')" %}
focus_feat as (
    select
        count(distinct feature_id)                                                            as f_feat,
        count(distinct case when feature_name in {{ workflow }} then feature_id end)          as f_wf,
        count(distinct case when feature_name in {{ integ }} then feature_id end)             as f_int
    from focus_conf
),
feat_stats as (
    select
        c.vendor_id,
        count(distinct c.feature_id)                                                          as comp_feat,
        count(distinct case when fc.feature_id is not null then c.feature_id end)             as inter_feat,
        count(distinct case when c.feature_name in {{ workflow }} then c.feature_id end)      as comp_wf,
        count(distinct case when c.feature_name in {{ workflow }} and fc.feature_id is not null
                            then c.feature_id end)                                            as inter_wf,
        count(distinct case when c.feature_name in {{ integ }} then c.feature_id end)         as comp_int,
        count(distinct case when c.feature_name in {{ integ }} and fc.feature_id is not null
                            then c.feature_id end)                                            as inter_int
    from conf c
    left join focus_conf fc on c.feature_id = fc.feature_id
    group by c.vendor_id
),

-- ---- evidence coverage per vendor ----
cov as (
    select
        vendor_id,
        count(*)                                                       as total_feat,
        count(*) filter (where availability_status <> 'unknown')       as known_feat
    from vf group by vendor_id
),
focus_cov as (
    select known_feat::numeric / nullif(total_feat, 0) as c
    from cov where vendor_id = (select vendor_id from focus_id)
),

scored as (
    select
        v.vendor_name as competitor,
        coalesce(
            ss.inter_seg::numeric
            / nullif((select n from focus_seg_n) + coalesce(ss.comp_seg,0) - coalesce(ss.inter_seg,0), 0),
            0) as segment_sim,
        coalesce(
            fs.inter_feat::numeric
            / nullif((select f_feat from focus_feat) + coalesce(fs.comp_feat,0) - coalesce(fs.inter_feat,0), 0),
            0) as feature_sim,
        coalesce(
            fs.inter_wf::numeric
            / nullif((select f_wf from focus_feat) + coalesce(fs.comp_wf,0) - coalesce(fs.inter_wf,0), 0),
            0) as workflow_sim,
        coalesce(
            fs.inter_int::numeric
            / nullif((select f_int from focus_feat) + coalesce(fs.comp_int,0) - coalesce(fs.inter_int,0), 0),
            0) as integration_sim,
        least((select c from focus_cov), co.known_feat::numeric / nullif(co.total_feat,0)) as evidence_coverage
    from v
    join cov co on v.vendor_id = co.vendor_id
    left join seg_stats ss on v.vendor_id = ss.vendor_id
    left join feat_stats fs on v.vendor_id = fs.vendor_id
    where v.vendor_name <> '{{ focus }}'
)

select
    '{{ focus }}'                          as focus_vendor,
    competitor,
    round(segment_sim, 3)                  as segment_sim,
    round(feature_sim, 3)                  as feature_sim,
    round(workflow_sim, 3)                 as workflow_sim,
    round(integration_sim, 3)             as integration_sim,
    round(100 * (0.40 * segment_sim + 0.35 * feature_sim
               + 0.15 * workflow_sim + 0.10 * integration_sim), 1) as overlap_score,
    round(evidence_coverage, 3)            as evidence_coverage,
    case
        when evidence_coverage < 0.30 then 'Insufficient evidence'
        when 100 * (0.40 * segment_sim + 0.35 * feature_sim
                  + 0.15 * workflow_sim + 0.10 * integration_sim) >= 70 then 'High overlap'
        when 100 * (0.40 * segment_sim + 0.35 * feature_sim
                  + 0.15 * workflow_sim + 0.10 * integration_sim) >= 40 then 'Moderate overlap'
        else 'Low overlap'
    end                                    as classification
from scored
order by overlap_score desc
