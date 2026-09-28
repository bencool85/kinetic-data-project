with source as (
    select * from {{ source('kinetic', 'orders') }}
)

select
    order_id,
    customer_id,
    guest_email,
    order_type,
    order_date,
    subtotal as subtotal_usd,
    subscriber_discount_applied,
    subscriber_discount_amount as subscriber_discount_usd,
    discount_code_id,
    discount_code_amount as discount_code_usd,
    total_amount as total_amount_usd,
    currency,
    created_at as order_created_at,
    (customer_id is null) as is_guest_order,
    (discount_code_id is not null or subscriber_discount_applied) as has_discount
from source
