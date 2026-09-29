-- One row per ad group per day.
-- Units (confirmed in generator/build_youtube_performance_daily.py): cost and
-- average cost-per-view arrive in micros -- _usd versions added.
-- video_view_rate is a fraction (0.284 = 28.4% of impressions became views).
-- These are Google's self-reported conversions, not site-verified orders.

with source as (
    select * from {{ source('kinetic', 'youtube_performance_daily') }}
)

select
    cast(ad_group_id as varchar) || '|' || strftime(date, '%Y-%m-%d') as ad_group_day_id,
    campaign_id,
    ad_group_id,
    date as report_date,
    impressions,
    video_views,
    video_view_rate as video_view_rate_fraction,
    clicks,
    cost_micros,
    cost_micros / 1000000.0 as cost_usd,
    average_cpv_micros / 1000000.0 as average_cpv_usd,
    conversions,
    conversions_value as conversions_value_usd
from source
