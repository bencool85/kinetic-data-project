-- An ad squad is Snap's name for what other platforms call an ad set or
-- ad group: the targeting/optimization level between campaign and ad.

with source as (
    select * from {{ source('kinetic', 'snap_ad_squads') }}
)

select
    ad_squad_id,
    campaign_id,
    name as ad_squad_name,
    status as ad_squad_status,
    targeting_segment_id,
    optimization_goal,
    created_at as ad_squad_created_at
from source
