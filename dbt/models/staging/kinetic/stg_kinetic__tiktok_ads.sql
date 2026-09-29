with source as (
    select * from {{ source('kinetic', 'tiktok_ads') }}
)

select
    ad_id,
    adgroup_id,
    ad_name,
    ad_format,
    status as ad_status,
    create_time as ad_created_at
from source
