with source as (
    select * from {{ source('kinetic', 'dv360_line_items') }}
)

select
    line_item_id,
    insertion_order_id,
    name as line_item_name,
    line_item_type,
    targeting_segment_id,
    status as line_item_status,
    created_at as line_item_created_at
from source
