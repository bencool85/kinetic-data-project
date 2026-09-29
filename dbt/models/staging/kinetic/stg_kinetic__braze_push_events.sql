-- Braze's external_user_id is Kinetic's customer_id, renamed here to say so.
-- event_type keeps Braze's raw name; event_name is the short lowercase
-- version (send/open/click/bounce/unsubscribe).

with source as (
    select * from {{ source('kinetic', 'braze_push_events') }}
)

select
    event_id,
    send_id,
    campaign_id,
    external_user_id as customer_id,
    device_id,
    platform,
    event_type as braze_event_type,
    lower(split_part(event_type, '.', 4)) as event_name,
    occurred_at
from source
