with source as (
    select * from {{ source('kinetic', 'meta_ads') }}
)

select
    ad_id,
    campaign_id,
    name as ad_name,
    status as ad_status,
    targeting_segment_id,
    optimization_goal,
    billing_event,
    created_time as ad_created_at,
    updated_time as ad_updated_at
from source
