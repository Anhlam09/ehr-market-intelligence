-- Clean view of vendor<->feature availability with feature metadata attached.
select
    vf.vendor_id,
    vf.feature_id,
    pf.feature_name,
    pf.feature_category,
    lower(trim(vf.availability_status))      as availability_status,
    vf.source_id,
    vf.verified_date
from {{ source('ehr_raw', 'vendor_features') }} vf
left join {{ source('ehr_raw', 'product_features') }} pf
       on vf.feature_id = pf.feature_id
