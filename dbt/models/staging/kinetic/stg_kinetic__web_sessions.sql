-- customer_id is null for sessions by visitors who hadn't signed in or
-- signed up yet (~79% of sessions) -- expected, not a gap. anonymous_id is
-- always present and is how pre-signup sessions get stitched to a customer
-- later via identity_map.

with source as (
    select * from {{ source('kinetic', 'web_sessions') }}
)

select
    session_id,
    anonymous_id,
    customer_id,
    started_at,
    ended_at,
    device_category,
    utm_source,
    utm_medium,
    utm_campaign,
    landing_page,
    referrer_domain,
    (customer_id is not null) as is_known_customer
from source
