-- Mart: how many (and which) healthcare segments each vendor serves.
with segs as (
    select * from {{ ref('stg_vendor_segments') }}
),
vendors as (
    select * from {{ ref('stg_vendors') }}
)
select
    v.vendor_id,
    v.vendor_name,
    count(s.segment_id)                                              as segments_served,
    count(*) filter (where s.market_role = 'primary')               as primary_segments,
    count(*) filter (where s.market_role = 'secondary')             as secondary_segments,
    string_agg(s.segment_name, ', ' order by s.segment_name)        as segments
from vendors v
left join segs s on v.vendor_id = s.vendor_id
group by v.vendor_id, v.vendor_name
order by segments_served desc, v.vendor_name
