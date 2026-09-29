with source as (
    select * from {{ source('kinetic', 'snap_ads') }}
)

select
    ad_id,
    ad_squad_id,
    name as ad_name,
    ad_type,
    status as ad_status,
    created_at as ad_created_at
from source
