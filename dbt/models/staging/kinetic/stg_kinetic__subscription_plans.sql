with source as (
    select * from {{ source('kinetic', 'subscription_plans') }}
)

select
    plan_id,
    tier as plan_tier,
    billing_interval,
    price as plan_price_usd,
    currency,
    is_active,
    created_at as plan_created_at
from source
