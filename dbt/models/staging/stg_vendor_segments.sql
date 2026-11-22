-- Clean view of vendor<->segment relationships with normalized role text.
select
    vs.vendor_id,
    vs.segment_id,
    lower(trim(vs.market_role))              as market_role,
    ms.segment_name,
    vs.source_id
from {{ source('ehr_raw', 'vendor_segments') }} vs
left join {{ source('ehr_raw', 'market_segments') }} ms
       on vs.segment_id = ms.segment_id
