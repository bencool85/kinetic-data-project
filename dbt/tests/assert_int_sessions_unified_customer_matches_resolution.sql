-- customer_id is null exactly when the session is anonymous. Returns
-- sessions where the two disagree.
select session_id, customer_id, customer_resolution
from {{ ref('int_sessions_unified') }}
where (customer_id is null) <> (customer_resolution = 'anonymous')
