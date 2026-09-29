with source as (
    select * from {{ source('kinetic', 'braze_email_campaigns') }}
)

select
    campaign_id,
    campaign_name,
    campaign_type,
    trigger_event,
    description as campaign_description,
    is_active,
    created_at as campaign_created_at
from source
