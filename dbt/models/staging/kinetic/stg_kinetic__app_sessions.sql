with source as (
    select * from {{ source('kinetic', 'app_sessions') }}
)

select
    session_id,
    customer_id,
    device_id,
    platform,
    started_at,
    ended_at
from source
