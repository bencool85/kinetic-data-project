-- TikTok stores one budget_micro column plus budget_mode (BUDGET_MODE_DAY
-- for always-on campaigns, BUDGET_MODE_TOTAL for holiday flights). Every
-- other platform has separate daily and lifetime budget columns, so both
-- are derived here (the raw columns are kept too) -- that way cross-platform
-- budget comparisons work the same everywhere. Amounts are in micros ($1 =
-- 1,000,000; the generator divides by 1,000,000) and are each campaign's
-- CURRENT budget (fixed 2026-09-29, see CHANGELOG). advertiser_id is
-- Kinetic's TikTok ad account, not a customer -- renamed tiktok_advertiser_id.

with source as (
    select * from {{ source('kinetic', 'tiktok_campaigns') }}
)

select
    campaign_id,
    advertiser_id as tiktok_advertiser_id,
    campaign_name,
    ad_objective,
    objective_type,
    status as campaign_status,
    budget_mode,
    budget_micro,
    case when budget_mode = 'BUDGET_MODE_DAY' then budget_micro / 1000000.0 end as daily_budget_usd,
    case when budget_mode = 'BUDGET_MODE_TOTAL' then budget_micro / 1000000.0 end as lifetime_budget_usd,
    start_time,
    end_time,
    create_time as campaign_created_at
from source
