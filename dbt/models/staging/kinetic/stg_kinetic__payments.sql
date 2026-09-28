with source as (
    select * from {{ source('kinetic', 'payments') }}
)

select
    payment_id,
    order_id,
    customer_id,
    amount as amount_usd,
    currency,
    payment_method_type,
    card_brand,
    card_last4,
    status as payment_status,
    failure_code,
    processed_at,
    created_at as payment_created_at
from source
