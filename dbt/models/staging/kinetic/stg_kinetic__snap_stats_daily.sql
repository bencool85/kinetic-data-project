-- One row per ad per day. ad_day_id is the combined key.
-- "swipes" are Snap's equivalent of clicks (a swipe-up on the ad) -- there is
-- no separate clicks column. Spend arrives in micros; spend_usd added.
-- Conversions are Snap's own attributed (and fractional) counts, not
-- site-verified orders.

with source as (
    select * from {{ source('kinetic', 'snap_stats_daily') }}
)

select
    ad_id || '|' || strftime(date, '%Y-%m-%d') as ad_day_id,
    ad_id,
    ad_squad_id,
    campaign_id,
    date as report_date,
    impressions,
    swipes,
    video_views,
    spend_micro,
    spend_micro / 1000000.0 as spend_usd,
    conversions,
    conversions_value as conversions_value_usd
from source
