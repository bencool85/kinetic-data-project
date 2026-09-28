with source as (
    select * from {{ source('kinetic', 'customers') }}
)

select
    customer_id,
    first_name,
    last_name,
    email,
    created_at as customer_created_at,
    signup_source,
    email_opt_in,
    push_opt_in,
    is_deleted
from source
