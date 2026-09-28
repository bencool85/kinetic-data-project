with source as (
    select * from {{ source('kinetic', 'refunds') }}
)

select
    refund_id,
    order_id,
    payment_id,
    customer_id,
    amount as amount_usd,
    currency,
    is_partial,
    reason as refund_reason,
    status as refund_status,
    refunded_at,
    created_at as refund_created_at
from source
