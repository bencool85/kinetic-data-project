with source as (
    select * from {{ source('kinetic', 'identity_map') }}
)

select
    resolution_id,
    anonymous_id,
    customer_id,
    resolved_at,
    resolution_type
from source
