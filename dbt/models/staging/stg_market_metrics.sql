-- Clean view of market metrics with vendor name attached.
select
    m.metric_id,
    m.vendor_id,
    v.vendor_name,
    m.segment_id,
    m.metric_name,
    m.metric_value::numeric                   as metric_value,
    m.metric_unit,
    m.measurement_year::int                   as measurement_year,
    m.source_id
from {{ source('ehr_raw', 'market_metrics') }} m
left join {{ source('ehr_raw', 'vendors') }} v
       on m.vendor_id = v.vendor_id
