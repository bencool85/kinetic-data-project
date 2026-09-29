-- One row per ad group per day. This table is the keyword table below
-- rolled up to ad-group level: same spend, less detail. Use one or the
-- other, never add them together (that would double-count spend).
-- Units (confirmed in the generator code): cost and average CPC arrive in
-- micros (millionths of a dollar, Google Ads convention) -- cost_usd and
-- average_cpc_usd are the dollar versions to use downstream. ctr is a
-- fraction (0.058 = 5.8%). conversions can be fractional (Google's
-- attribution splits credit). conversions_value is already in dollars.
-- These are Google's self-reported conversions, not site-verified orders.

with source as (
    select * from {{ source('kinetic', 'google_search_performance_daily') }}
)

select
    cast(ad_group_id as varchar) || '|' || strftime(date, '%Y-%m-%d') as ad_group_day_id,
    campaign_id,
    ad_group_id,
    date as report_date,
    impressions,
    clicks,
    cost_micros,
    cost_micros / 1000000.0 as cost_usd,
    average_cpc_micros / 1000000.0 as average_cpc_usd,
    ctr as ctr_fraction,
    conversions,
    conversions_value as conversions_value_usd
from source
