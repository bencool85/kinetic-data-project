-- Subscriber counts must add up: each month's active_subscribers_end equals
-- the previous month's plus new minus churned. Returns months where not.
with m as (
    select
        *,
        lag(active_subscribers_end) over (order by month_start) as prev_end
    from {{ ref('mart_subscriber_movement_monthly') }}
)
select year_month, prev_end, new_paying_subscribers, churned_subscribers, active_subscribers_end
from m
where prev_end is not null
  and active_subscribers_end <> prev_end + new_paying_subscribers - churned_subscribers
