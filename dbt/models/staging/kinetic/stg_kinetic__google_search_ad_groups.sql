-- cpc_bid_micros is always empty: these campaigns use automated bidding
-- (TARGET_CPA / MAXIMIZE_CLICKS), so no manual bid is set. Being all-empty
-- made it load as text; it's cast back to a number here.

with source as (
    select * from {{ source('kinetic', 'google_search_ad_groups') }}
)

select
    ad_group_id,
    campaign_id,
    name as ad_group_name,
    status as ad_group_status,
    targeting_segment_id,
    cast(cpc_bid_micros as bigint) as cpc_bid_micros,
    created_at as ad_group_created_at
from source
