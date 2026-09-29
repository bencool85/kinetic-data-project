-- Budgets arrive in cents (Meta API convention, confirmed in
-- generator/build_meta_campaigns.py). Both are kept: the raw cents value for
-- traceability, and a dollar value that everything downstream should use.
-- Always-on campaigns have a daily budget; brand-lift flights have a
-- lifetime budget instead, so each column is null for the other kind.

with source as (
    select * from {{ source('kinetic', 'meta_campaigns') }}
)

select
    campaign_id,
    account_id,
    name as campaign_name,
    ad_objective,
    objective,
    status as campaign_status,
    daily_budget as daily_budget_cents,
    daily_budget / 100.0 as daily_budget_usd,
    lifetime_budget as lifetime_budget_cents,
    lifetime_budget / 100.0 as lifetime_budget_usd,
    start_time,
    stop_time,
    created_time as campaign_created_at,
    updated_time as campaign_updated_at
from source
