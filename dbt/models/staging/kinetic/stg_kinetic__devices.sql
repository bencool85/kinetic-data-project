-- customer_id is null for anonymous devices that never resolved to a known
-- customer (~94% of rows) -- expected by design, not a data gap.

with source as (
    select * from {{ source('kinetic', 'devices') }}
)

select
    device_id,
    customer_id,
    anonymous_id,
    device_type,
    first_seen_at,
    last_seen_at,
    (customer_id is null) as is_anonymous_device
from source
