-- In the raw table, customer_id is the Google Ads *account* number
-- (123-456-7890), NOT a Kinetic customer. Renamed to google_ads_account_id
-- so it can never be mistaken for, or joined to, customers.customer_id.
-- campaign_budget_micros is a daily budget in micros (millionths of a
-- dollar). end_date is always empty (no campaign has a scheduled end), which
-- made it load as text; it's cast back to a date here.

with source as (
    select * from {{ source('kinetic', 'google_search_campaigns') }}
)

select
    campaign_id,
    customer_id as google_ads_account_id,
    name as campaign_name,
    ad_objective,
    advertising_channel_type,
    bidding_strategy_type,
    status as campaign_status,
    campaign_budget_micros as daily_budget_micros,
    campaign_budget_micros / 1000000.0 as daily_budget_usd,
    start_date,
    cast(end_date as date) as end_date,
    created_at as campaign_created_at
from source
