-- old_plan / new_plan hold plan_id values (e.g. plan_plus_monthly); renamed
-- here so the column name says what it actually contains.

with source as (
    select * from {{ source('kinetic', 'subscription_events') }}
)

select
    event_id,
    subscription_id,
    customer_id,
    event_type,
    event_at,
    old_plan as old_plan_id,
    new_plan as new_plan_id,
    resolved as is_resolved,
    reason as event_reason
from source
