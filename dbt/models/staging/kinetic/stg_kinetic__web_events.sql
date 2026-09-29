-- product_id / order_id / search_query are only filled in for the event
-- types they apply to (e.g. order_id on purchase, search_query on search).

with source as (
    select * from {{ source('kinetic', 'web_events') }}
)

select
    event_id,
    session_id,
    anonymous_id,
    customer_id,
    event_type,
    occurred_at,
    page_path,
    product_id,
    order_id,
    search_query
from source
