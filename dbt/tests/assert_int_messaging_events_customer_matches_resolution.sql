-- customer_id must be null exactly when customer_resolution is 'unresolved'.
-- Returns offending rows.
select event_id, customer_id, customer_resolution
from {{ ref('int_messaging_events') }}
where (customer_resolution = 'unresolved') <> (customer_id is null)
