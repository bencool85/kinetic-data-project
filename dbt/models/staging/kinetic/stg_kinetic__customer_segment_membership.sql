with source as (
    select * from {{ source('kinetic', 'customer_segment_membership') }}
)

select
    membership_id,
    customer_id,
    segment_id,
    entered_at,
    exited_at,
    (exited_at is null) as is_current_member,
    created_at as membership_created_at
from source
