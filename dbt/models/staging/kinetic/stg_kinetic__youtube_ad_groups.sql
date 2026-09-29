with source as (
    select * from {{ source('kinetic', 'youtube_ad_groups') }}
)

select
    ad_group_id,
    campaign_id,
    name as ad_group_name,
    status as ad_group_status,
    targeting_segment_id,
    created_at as ad_group_created_at
from source
