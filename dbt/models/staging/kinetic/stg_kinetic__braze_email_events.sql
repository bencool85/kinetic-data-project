-- Braze's external_user_id is Kinetic's customer_id, renamed here to say so.
-- It is null for Order Confirmation emails sent to guest checkouts (people
-- with an email but no customer account) -- expected, not a gap.
-- event_type keeps Braze's raw name (e.g. users.messages.email.Open);
-- event_name is the short, lowercase version (send/open/click/bounce/
-- unsubscribe) that everything downstream should use.

with source as (
    select * from {{ source('kinetic', 'braze_email_events') }}
)

select
    event_id,
    send_id,
    campaign_id,
    external_user_id as customer_id,
    email_address,
    event_type as braze_event_type,
    lower(split_part(event_type, '.', 4)) as event_name,
    occurred_at
from source
