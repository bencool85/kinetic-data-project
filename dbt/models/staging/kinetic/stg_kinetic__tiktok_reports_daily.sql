-- One row per ad per day. ad_day_id is the combined key.
-- Units: spend and CPM arrive in micros -- _usd versions added. ctr is a
-- fraction (0.016 = 1.6%). Conversions are TikTok's own attributed (and
-- fractional) counts, not site-verified orders.

with source as (
    select * from {{ source('kinetic', 'tiktok_reports_daily') }}
)

select
    cast(ad_id as varchar) || '|' || strftime(date, '%Y-%m-%d') as ad_day_id,
    ad_id,
    adgroup_id,
    campaign_id,
    date as report_date,
    impressions,
    clicks,
    video_views,
    spend_micro,
    spend_micro / 1000000.0 as spend_usd,
    cpm_micro / 1000000.0 as cpm_usd,
    ctr as ctr_fraction,
    conversions,
    conversions_value as conversions_value_usd
from source
