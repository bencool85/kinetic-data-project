-- One row per ad per day per action type (purchase, add_to_cart, ...).
-- These are Meta's own self-reported conversions, not site-verified
-- orders -- there is no join key from a Meta ad to a specific Kinetic
-- order (see the CHANGELOG entry for the Dive v2 build).

with source as (
    select * from {{ source('kinetic', 'meta_ad_actions_daily') }}
)

select
    cast(ad_id as varchar) || '|' || strftime(date, '%Y-%m-%d') || '|' || action_type as ad_day_action_id,
    cast(ad_id as varchar) || '|' || strftime(date, '%Y-%m-%d') as ad_day_id,
    ad_id,
    campaign_id,
    date as report_date,
    action_type,
    value as action_count
from source
