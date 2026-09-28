with source as (
    select * from {{ source('kinetic', 'products') }}
)

select
    product_id,
    name as product_name,
    product_type,
    category as product_category,
    base_price as base_price_usd,
    is_subscription_eligible,
    created_at as product_created_at,
    is_active
from source
