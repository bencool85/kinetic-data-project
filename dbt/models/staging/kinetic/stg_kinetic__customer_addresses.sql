with source as (
    select * from {{ source('kinetic', 'customer_addresses') }}
)

select
    address_id,
    customer_id,
    address_type,
    street_address,
    unit,
    city,
    state,
    zip_code,
    country,
    created_at as address_created_at
from source
