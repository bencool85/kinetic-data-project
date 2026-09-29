with source as (
    select * from {{ source('kinetic', 'segments') }}
)

select
    segment_id,
    segment_name,
    audience_grain,
    description as segment_description,
    source_system,
    ad_platform,
    platform_audience_id,
    is_active,
    created_at as segment_created_at
from source
