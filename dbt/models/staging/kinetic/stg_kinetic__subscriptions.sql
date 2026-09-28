with source as (
    select * from {{ source('kinetic', 'subscriptions') }}
)

select
    subscription_id,
    customer_id,
    plan_id,
    billing_interval,
    status as subscription_status,
    trial_start,
    trial_end,
    start_date,
    current_period_start,
    current_period_end,
    canceled_at,
    cancel_reason,
    past_due_since,
    created_at as subscription_created_at
from source
