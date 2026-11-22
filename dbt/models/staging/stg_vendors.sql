-- Clean view of vendors: trimmed names, typed year.
select
    vendor_id,
    trim(vendor_name)                        as vendor_name,
    website,
    headquarters,
    founded_year::int                        as founded_year,
    description
from {{ source('ehr_raw', 'vendors') }}
