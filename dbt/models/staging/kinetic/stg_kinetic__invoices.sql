with source as (
    select * from {{ source('kinetic', 'invoices') }}
)

select
    invoice_id,
    subscription_id,
    customer_id,
    plan_id,
    amount_due as amount_due_usd,
    currency,
    period_start,
    period_end,
    status as invoice_status,
    paid_at,
    created_at as invoice_created_at
from source
