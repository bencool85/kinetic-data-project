with source as (
    select * from {{ source('kinetic', 'product_variants') }}
)

select
    variant_id,
    product_id,
    sku,
    option_value as variant_option,
    price_adjustment as price_adjustment_usd,
    is_active,
    created_at as variant_created_at
from source
