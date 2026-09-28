with source as (
    select * from {{ source('kinetic', 'order_line_items') }}
)

select
    line_item_id,
    order_id,
    product_id,
    variant_id,
    quantity,
    unit_price as unit_price_usd,
    line_total as line_total_usd
from source
