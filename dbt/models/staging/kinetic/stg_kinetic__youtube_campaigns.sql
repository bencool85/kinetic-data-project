-- YouTube ads run through Google Ads, so this table follows the same
-- conventions as google_search_campaigns:
--   * the raw customer_id is the Google Ads *account* number (123-456-7890,
--     the same account as Google Search), NOT a Kinetic customer -- renamed
--     google_ads_account_id.
--   * budgets are in micros (millionths of a dollar); _usd versions added.
-- Always-on campaigns have a daily budget; brand-lift flights have a
-- lifetime budget and an end date instead.

with source as (
    select * from {{ source('kinetic', 'youtube_campaigns') }}
)

select
    campaign_id,
    customer_id as google_ads_account_id,
    name as campaign_name,
    ad_objective,
    advertising_channel_type,
    video_ad_format,
    bidding_strategy_type,
    status as campaign_status,
    cast(campaign_budget_micros as bigint) as daily_budget_micros,
    campaign_budget_micros / 1000000.0 as daily_budget_usd,
    cast(lifetime_budget_micros as bigint) as lifetime_budget_micros,
    lifetime_budget_micros / 1000000.0 as lifetime_budget_usd,
    start_date,
    end_date,
    created_at as campaign_created_at
from source
