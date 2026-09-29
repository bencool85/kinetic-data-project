-- One row per line item, per day, per ad exchange, per environment (web,
-- app, connected TV). DV360 buys across many exchanges at once, so each
-- line-item-day is split over several rows. line_item_day_slice_id is the
-- combined key. To get one number per line item per day, SUM across
-- exchange and environment.
-- Units: cost and CPM arrive in micros -- _usd versions added. ctr is a
-- fraction. Conversions are DV360's self-reported, not site-verified.

with source as (
    select * from {{ source('kinetic', 'dv360_performance_daily') }}
)

select
    cast(line_item_id as varchar) || '|' || strftime(date, '%Y-%m-%d') || '|' || exchange || '|' || environment
        as line_item_day_slice_id,
    line_item_id,
    insertion_order_id,
    date as report_date,
    exchange,
    environment,
    impressions,
    clicks,
    cost_micros,
    cost_micros / 1000000.0 as cost_usd,
    cpm_micros / 1000000.0 as cpm_usd,
    ctr as ctr_fraction,
    conversions,
    conversions_value as conversions_value_usd
from source
