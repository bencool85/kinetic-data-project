-- An insertion order (IO) is DV360's campaign-level budget container.
-- budget_micros is a MONTHLY budget in micros (confirmed in
-- generator/build_dv360_insertion_orders.py: 30x a daily figure) -- named
-- monthly_budget_* here so it isn't read as daily or lifetime.
-- KNOWN ISSUE (2026-09-29, see CHANGELOG): the stored budget is flat for the
-- whole 3 years while spend grows with the business, so later months spend
-- up to 2.4x this budget. Don't use it as a spend cap until that's resolved.
-- end_date is always empty (no scheduled end), which made it load as text;
-- cast back to a date here.

with source as (
    select * from {{ source('kinetic', 'dv360_insertion_orders') }}
)

select
    insertion_order_id,
    advertiser_id as dv360_advertiser_id,
    name as insertion_order_name,
    ad_objective,
    performance_goal_type,
    pacing_type,
    budget_type,
    budget_micros as monthly_budget_micros,
    budget_micros / 1000000.0 as monthly_budget_usd,
    status as insertion_order_status,
    start_date,
    cast(end_date as date) as end_date,
    created_at as insertion_order_created_at
from source
