-- Budgets are in micros (Snap's "micro-currency": $1 = 1,000,000) and are
-- each campaign's CURRENT budget (fixed 2026-09-29, see CHANGELOG). Always-on
-- campaigns have a daily budget; holiday flights have a lifetime budget and
-- an end time instead. ad_account_id is Kinetic's Snap ad account, not a
-- customer -- renamed snap_ad_account_id.

with source as (
    select * from {{ source('kinetic', 'snap_campaigns') }}
)

select
    campaign_id,
    ad_account_id as snap_ad_account_id,
    name as campaign_name,
    ad_objective,
    objective,
    status as campaign_status,
    cast(daily_budget_micro as bigint) as daily_budget_micro,
    daily_budget_micro / 1000000.0 as daily_budget_usd,
    cast(lifetime_budget_micro as bigint) as lifetime_budget_micro,
    lifetime_budget_micro / 1000000.0 as lifetime_budget_usd,
    start_time,
    end_time,
    created_at as campaign_created_at,
    updated_at as campaign_updated_at
from source
