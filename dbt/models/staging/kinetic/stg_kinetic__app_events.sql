-- workout_type / duration_minutes apply to workout and class events;
-- streak_days applies to streak_achieved events.

with source as (
    select * from {{ source('kinetic', 'app_events') }}
)

select
    event_id,
    session_id,
    customer_id,
    event_type,
    occurred_at,
    workout_type,
    duration_minutes,
    streak_days
from source
