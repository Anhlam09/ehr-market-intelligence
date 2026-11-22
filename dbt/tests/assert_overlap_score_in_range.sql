-- Singular test: overlap_score must be between 0 and 100.
-- A passing test returns zero rows.
select competitor, overlap_score
from {{ ref('competitor_overlap') }}
where overlap_score < 0 or overlap_score > 100
