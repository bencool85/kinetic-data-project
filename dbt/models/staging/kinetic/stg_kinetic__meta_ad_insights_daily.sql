-- One row per ad per day. There is no single ID column, so ad_day_id is
-- built from ad_id + date and tested for uniqueness.
-- Units: spend/cpm/cpc are US dollars; ctr is a fraction (0.017 = 1.7%),
-- not a percentage -- renamed to ctr_fraction so it can't be misread.
-- cpc is null on days with zero clicks.

with source as (
    select * from {{ source('kinetic', 'meta_ad_insights_daily') }}
)

select
    cast(ad_id as varchar) || '|' || strftime(date, '%Y-%m-%d') as ad_day_id,
    ad_id,
    campaign_id,
    date as report_date,
    impressions,
    clicks,
    reach,
    frequency,
    spend as spend_usd,
    cpm as cpm_usd,
    cpc as cpc_usd,
    ctr as ctr_fraction
from source
