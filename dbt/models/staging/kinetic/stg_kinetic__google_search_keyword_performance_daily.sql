-- One row per keyword per day -- the most detailed Google Search table.
-- google_search_performance_daily is this same data rolled up to ad group;
-- never add the two together.
-- Units (confirmed in the generator code): cost and average CPC arrive in
-- micros (millionths of a dollar, Google Ads convention) -- cost_usd and
-- average_cpc_usd are the dollar versions to use downstream. ctr is a
-- fraction (0.058 = 5.8%). conversions can be fractional (Google's
-- attribution splits credit). conversions_value is already in dollars.
-- These are Google's self-reported conversions, not site-verified orders.

with source as (
    select * from {{ source('kinetic', 'google_search_keyword_performance_daily') }}
)

select
    keyword_id || '|' || strftime(date, '%Y-%m-%d') as keyword_day_id,
    keyword_id,
    campaign_id,
    ad_group_id,
    keyword_text,
    match_type,
    quality_score,
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
