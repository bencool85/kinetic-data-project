with source as (
    select * from {{ source('kinetic', 'discount_codes') }}
)

select
    discount_code_id,
    code,
    discount_type,
    discount_value,
    applies_to,
    min_order_amount as min_order_amount_usd,
    valid_from,
    valid_until,
    is_active,
    created_at as discount_code_created_at
from source
