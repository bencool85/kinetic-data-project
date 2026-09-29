with source as (
    select * from {{ source('kinetic', 'tiktok_adgroups') }}
)

select
    adgroup_id,
    campaign_id,
    adgroup_name,
    status as adgroup_status,
    targeting_segment_id,
    billing_event,
    placement_type,
    create_time as adgroup_created_at
from source
